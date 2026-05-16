from __future__ import annotations

import argparse
import base64
import os
import time
import urllib.error
from pathlib import Path
from typing import Any

from common import (
    RAW_SAMPLES_DIR,
    ensure_data_dirs,
    load_dotenv,
    request_json,
    require_env,
    slugify,
    write_csv,
    write_json,
)


JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
CAREERJET_API_URL = "https://search.api.careerjet.net/v4/query"

CAREERJET_LOCALE = {
    "AE": "en_AE",
    "SA": "en_SA",
}

DEFAULT_ROLES = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Financial Analyst",
    "Reporting Analyst",
    "Product Analyst",
    "Operations Analyst",
    "Data Scientist",
]

DEFAULT_CITIES = {
    "Dubai": "AE",
    "Abu Dhabi": "AE",
    "Riyadh": "SA",
    "Jeddah": "SA",
    "Dammam": "SA",
}

CITY_COUNTRIES = {
    **DEFAULT_CITIES,
    "Sharjah": "AE",
    "Khobar": "SA",
    "Doha": "QA",
    "Kuwait City": "KW",
    "Manama": "BH",
    "Muscat": "OM",
}

MANIFEST_FIELDS = [
    "batch_tag",
    "source",
    "role",
    "city",
    "country",
    "query_label",
    "limit",
    "status",
    "row_count",
    "output_path",
    "error",
]


def parse_csv_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run a controlled analyst-market sampling batch across configured APIs."
    )
    parser.add_argument("--batch-tag", default=time.strftime("%Y%m%d_expansion"))
    parser.add_argument("--roles", help="Comma-separated role list. Defaults to the controlled expansion roles.")
    parser.add_argument(
        "--cities",
        help=(
            "Comma-separated city list. Defaults to the core weekly cities. "
            "Supported discovery cities include Sharjah, Khobar, Doha, Kuwait City, Manama, and Muscat."
        ),
    )
    parser.add_argument("--sources", nargs="+", choices=["jsearch", "careerjet"], default=["jsearch", "careerjet"])
    parser.add_argument("--jsearch-limit", type=int, default=10)
    parser.add_argument("--careerjet-limit", type=int, default=5)
    parser.add_argument("--delay-seconds", type=float, default=0.6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest", help="Optional manifest output path.")
    parser.add_argument("--careerjet-user-ip", default=os.environ.get("CAREERJET_USER_IP", ""))
    parser.add_argument(
        "--careerjet-referer",
        default=os.environ.get("CAREERJET_REFERER", "https://maze291.github.io"),
    )
    parser.add_argument(
        "--careerjet-user-agent",
        default=os.environ.get("CAREERJET_USER_AGENT", "gcc-analyst-market-tracker-feasibility/0.1"),
    )
    parser.add_argument("--jsearch-provider", choices=["rapidapi"], default="rapidapi")
    return parser.parse_args()


def output_path(source: str, role: str, city: str, batch_tag: str) -> Path:
    query_label = f"{role} {city}"
    return RAW_SAMPLES_DIR / f"{source}_{slugify(query_label)}_{slugify(batch_tag)}.json"


def planned_requests(args: argparse.Namespace) -> list[dict[str, str]]:
    roles = parse_csv_list(args.roles, DEFAULT_ROLES)
    requested_cities = parse_csv_list(args.cities, list(DEFAULT_CITIES))
    unknown_cities = [city for city in requested_cities if city not in CITY_COUNTRIES]
    if unknown_cities:
        raise SystemExit(f"Unknown cities for this batch: {', '.join(unknown_cities)}")

    requests: list[dict[str, str]] = []
    for role in roles:
        for city in requested_cities:
            country = CITY_COUNTRIES[city]
            query_label = f"{role} {city}"
            for source in args.sources:
                if source == "careerjet" and country not in CAREERJET_LOCALE:
                    raise SystemExit(
                        f"Careerjet locale is not configured for {city} ({country}). "
                        "Use --sources jsearch for Gulf discovery cities outside AE/SA."
                    )
                requests.append(
                    {
                        "source": source,
                        "role": role,
                        "city": city,
                        "country": country,
                        "query_label": query_label,
                    }
                )
    return requests


def fetch_jsearch(role: str, city: str, output: Path, limit: int) -> int:
    api_key = require_env("JSEARCH_API_KEY")
    params = {"query": f"{role} {city}", "page": 1, "num_pages": 1, "limit": limit}
    payload = request_json(
        "GET",
        JSEARCH_API_URL,
        headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": JSEARCH_RAPIDAPI_HOST},
        params=params,
    )
    rows = payload.get("data")
    row_count = len(rows) if isinstance(rows, list) else 0
    wrapped = {"_meta": {"source": "jsearch", "query": f"{role} {city}"}, **payload}
    write_json(output, wrapped)
    return row_count


def fetch_careerjet(
    role: str,
    city: str,
    country: str,
    output: Path,
    limit: int,
    user_ip: str,
    user_agent: str,
    referer: str,
) -> int:
    if not user_ip:
        raise SystemExit("Missing CAREERJET_USER_IP. Set it in .env before running Careerjet batches.")

    api_key = require_env("CAREERJET_API_KEY")
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    params = {
        "locale_code": CAREERJET_LOCALE[country],
        "keywords": role,
        "location": city,
        "page": 1,
        "page_size": limit,
        "user_ip": user_ip,
        "user_agent": user_agent,
    }
    payload = request_json(
        "GET",
        CAREERJET_API_URL,
        headers={"Authorization": f"Basic {token}", "Referer": referer},
        params=params,
    )
    jobs = payload.get("jobs")
    if isinstance(jobs, list) and len(jobs) > limit:
        payload = dict(payload)
        payload["_original_jobs_count"] = len(jobs)
        payload["jobs"] = jobs[:limit]
    row_count = len(payload.get("jobs")) if isinstance(payload.get("jobs"), list) else 0
    wrapped = {"_meta": {"source": "careerjet", "query": f"{role} {city}", "country": country}, **payload}
    write_json(output, wrapped)
    return row_count


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    manifest_path = Path(args.manifest) if args.manifest else RAW_SAMPLES_DIR / "batches" / f"{slugify(args.batch_tag)}.csv"
    requests = planned_requests(args)

    if args.dry_run:
        print(f"DRY RUN: {len(requests)} requests planned for batch {args.batch_tag}")
        for request in requests:
            limit = args.jsearch_limit if request["source"] == "jsearch" else args.careerjet_limit
            print(
                f"{request['source']}: {request['query_label']} "
                f"({request['country']}), limit={limit}, output={output_path(request['source'], request['role'], request['city'], args.batch_tag)}"
            )
        print(f"Would write manifest: {manifest_path}")
        return

    records: list[dict[str, Any]] = []
    for index, request in enumerate(requests, start=1):
        source = request["source"]
        role = request["role"]
        city = request["city"]
        country = request["country"]
        limit = args.jsearch_limit if source == "jsearch" else args.careerjet_limit
        path = output_path(source, role, city, args.batch_tag)
        status = "ok"
        row_count = 0
        error = ""

        if path.exists() and not args.overwrite:
            status = "skipped_existing"
            try:
                # Keep the manifest useful when re-running normalization from an existing batch.
                from common import extract_items, read_json

                row_count = len(extract_items(read_json(path)))
            except Exception:
                row_count = 0
        else:
            try:
                if source == "jsearch":
                    row_count = fetch_jsearch(role, city, path, limit)
                else:
                    row_count = fetch_careerjet(
                        role,
                        city,
                        country,
                        path,
                        limit,
                        args.careerjet_user_ip,
                        args.careerjet_user_agent,
                        args.careerjet_referer,
                    )
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                status = "error"
                error = str(exc)

        records.append(
            {
                "batch_tag": args.batch_tag,
                "source": source,
                "role": role,
                "city": city,
                "country": country,
                "query_label": request["query_label"],
                "limit": str(limit),
                "status": status,
                "row_count": str(row_count),
                "output_path": str(path),
                "error": error,
            }
        )
        print(f"[{index}/{len(requests)}] {source} {request['query_label']}: {status} ({row_count})")

        if index < len(requests) and args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    write_csv(manifest_path, records, MANIFEST_FIELDS)
    ok_rows = sum(int(row["row_count"] or 0) for row in records if row["status"] in {"ok", "skipped_existing"})
    errors = sum(1 for row in records if row["status"] == "error")
    print(f"Wrote batch manifest: {manifest_path}")
    print(f"Fetched or reused {ok_rows} raw rows across {len(records)} requests; errors: {errors}")


if __name__ == "__main__":
    main()
