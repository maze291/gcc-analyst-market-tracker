from __future__ import annotations

import argparse
import time
import urllib.error
from pathlib import Path
from typing import Any

from common import RAW_SAMPLES_DIR, ensure_data_dirs, request_json, require_env, slugify, write_csv, write_json


JOOBLE_API_URL = "https://jooble.org/api/{api_key}"

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

DEFAULT_COUNTRIES = ["United Arab Emirates", "Saudi Arabia"]

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
    parser = argparse.ArgumentParser(description="Run a small country-level Jooble validation batch.")
    parser.add_argument("--batch-tag", default=time.strftime("%Y%m%d_jooble_validation"))
    parser.add_argument("--roles", help="Comma-separated role list.")
    parser.add_argument("--countries", help="Comma-separated country list.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=0.6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest", help="Optional manifest output path.")
    return parser.parse_args()


def output_path(role: str, country: str, batch_tag: str) -> Path:
    query_label = f"{role} {country}"
    return RAW_SAMPLES_DIR / f"jooble_{slugify(query_label)}_{slugify(batch_tag)}.json"


def fetch_jooble(role: str, country: str, output: Path, limit: int) -> int:
    api_key = require_env("JOOBLE_API_KEY")
    payload = {
        "keywords": role,
        "location": country,
        "page": 1,
        "ResultOnPage": limit,
        "companysearch": "false",
    }
    response = request_json("POST", JOOBLE_API_URL.format(api_key=api_key), json_body=payload)
    jobs = response.get("jobs")
    row_count = len(jobs) if isinstance(jobs, list) else 0
    wrapped = {"_meta": {"source": "jooble", "query": f"{role} {country}"}, **response}
    write_json(output, wrapped)
    return row_count


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    roles = parse_csv_list(args.roles, DEFAULT_ROLES)
    countries = parse_csv_list(args.countries, DEFAULT_COUNTRIES)
    manifest_path = Path(args.manifest) if args.manifest else RAW_SAMPLES_DIR / "batches" / f"{slugify(args.batch_tag)}.csv"

    requests = [(role, country) for role in roles for country in countries]
    if args.dry_run:
        print(f"DRY RUN: {len(requests)} Jooble validation requests planned for batch {args.batch_tag}")
        for role, country in requests:
            print(f"jooble: {role} {country}, limit={args.limit}, output={output_path(role, country, args.batch_tag)}")
        print(f"Would write manifest: {manifest_path}")
        return

    records: list[dict[str, Any]] = []
    for index, (role, country) in enumerate(requests, start=1):
        path = output_path(role, country, args.batch_tag)
        status = "ok"
        row_count = 0
        error = ""

        if path.exists() and not args.overwrite:
            status = "skipped_existing"
            try:
                from common import extract_items, read_json

                row_count = len(extract_items(read_json(path)))
            except Exception:
                row_count = 0
        else:
            try:
                row_count = fetch_jooble(role, country, path, args.limit)
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                status = "error"
                error = str(exc)

        records.append(
            {
                "batch_tag": args.batch_tag,
                "source": "jooble",
                "role": role,
                "city": "",
                "country": country,
                "query_label": f"{role} {country}",
                "limit": str(args.limit),
                "status": status,
                "row_count": str(row_count),
                "output_path": str(path),
                "error": error,
            }
        )
        print(f"[{index}/{len(requests)}] jooble {role} {country}: {status} ({row_count})")
        if index < len(requests) and args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    write_csv(manifest_path, records, MANIFEST_FIELDS)
    ok_rows = sum(int(row["row_count"] or 0) for row in records if row["status"] in {"ok", "skipped_existing"})
    errors = sum(1 for row in records if row["status"] == "error")
    print(f"Wrote batch manifest: {manifest_path}")
    print(f"Fetched or reused {ok_rows} Jooble rows across {len(records)} requests; errors: {errors}")


if __name__ == "__main__":
    main()
