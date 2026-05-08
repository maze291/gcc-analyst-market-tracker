from __future__ import annotations

import argparse
import base64
import os
import urllib.error
from pathlib import Path

from common import ensure_data_dirs, load_dotenv, request_json, require_env, sample_path, write_json


COUNTRY_TO_LOCALE = {"AE": "en_AE", "SA": "en_SA"}
DEFAULT_ENDPOINT = "https://search.api.careerjet.net/v4/query"


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Fetch a local-only Careerjet sample.")
    parser.add_argument("--query", required=True, help="Keyword query, for example: Data Analyst")
    parser.add_argument("--location", required=True, help="Location, for example: Dubai or Riyadh")
    parser.add_argument("--country", choices=sorted(COUNTRY_TO_LOCALE), required=True)
    parser.add_argument("--limit", type=int, default=10, help="Requested result count for a tiny sample.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--api-url", default=os.environ.get("CAREERJET_API_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--user-ip", default=os.environ.get("CAREERJET_USER_IP", ""), help="Required by Careerjet API docs. Use the public IP declared in Careerjet.")
    parser.add_argument("--user-agent", default=os.environ.get("CAREERJET_USER_AGENT", "gcc-analyst-market-tracker-feasibility/0.1"))
    parser.add_argument("--referer", default=os.environ.get("CAREERJET_REFERER", "https://maze291.github.io"))
    parser.add_argument("--dry-run", action="store_true", help="Print request plan without calling the API.")
    parser.add_argument("--output", help="Optional output path. Defaults to data/raw_samples/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    if not args.user_ip:
        raise SystemExit("Missing --user-ip or CAREERJET_USER_IP. Use the public IP address you declared in Careerjet.")
    query_label = f"{args.query} {args.location}".strip()
    output_path = Path(args.output) if args.output else sample_path("careerjet", query_label)
    params = {
        "locale_code": COUNTRY_TO_LOCALE[args.country],
        "keywords": args.query,
        "location": args.location,
        "page": args.page,
        "page_size": args.limit,
        "user_ip": args.user_ip,
        "user_agent": args.user_agent,
    }

    if args.dry_run:
        print(f"DRY RUN: GET {args.api_url}")
        print(f"Query params: {params}")
        print("Headers: Authorization: Basic <CAREERJET_API_KEY:>, Referer")
        print(f"Would write: {output_path}")
        return

    api_key = require_env("CAREERJET_API_KEY")
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    try:
        payload = request_json(
            "GET",
            args.api_url,
            headers={"Authorization": f"Basic {token}", "Referer": args.referer},
            params=params,
        )
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Careerjet request failed before receiving an API response. "
            "If this says getaddrinfo/DNS, your machine could not resolve the Careerjet API host. "
            "Check DNS/VPN/firewall, verify the endpoint in Careerjet's API documentation, or retry with "
            "--api-url / CAREERJET_API_URL if Careerjet shows a different endpoint. "
            f"Original error: {exc}"
        ) from exc
    jobs = payload.get("jobs")
    if isinstance(jobs, list) and len(jobs) > args.limit:
        payload = dict(payload)
        payload["_original_jobs_count"] = len(jobs)
        payload["jobs"] = jobs[: args.limit]
    wrapped = {"_meta": {"source": "careerjet", "query": query_label, "country": args.country}, **payload}
    write_json(output_path, wrapped)
    print(f"Wrote local raw sample: {output_path}")
    if isinstance(jobs, list) and len(jobs) > args.limit:
        print(f"Careerjet returned {len(jobs)} jobs; saved first {args.limit} for this controlled sample.")


if __name__ == "__main__":
    main()
