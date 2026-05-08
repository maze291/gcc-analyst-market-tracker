from __future__ import annotations

import argparse
import base64
from pathlib import Path

from common import ensure_data_dirs, request_json, require_env, sample_path, write_json


COUNTRY_TO_LOCALE = {"AE": "en_AE", "SA": "en_SA"}
COUNTRY_TO_ENDPOINT = {
    "AE": "https://search.api.careerjet.net/v4/query",
    "SA": "https://search.api.careerjet.net/v4/query",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a local-only Careerjet sample.")
    parser.add_argument("--query", required=True, help="Keyword query, for example: Data Analyst")
    parser.add_argument("--location", required=True, help="Location, for example: Dubai or Riyadh")
    parser.add_argument("--country", choices=sorted(COUNTRY_TO_LOCALE), required=True)
    parser.add_argument("--limit", type=int, default=10, help="Requested result count for a tiny sample.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--user-ip", default="127.0.0.1", help="Required by Careerjet API docs.")
    parser.add_argument("--user-agent", default="gcc-analyst-market-tracker-feasibility/0.1")
    parser.add_argument("--referer", default="https://example-publisher-site.com/gcc-analyst-market-tracker")
    parser.add_argument("--dry-run", action="store_true", help="Print request plan without calling the API.")
    parser.add_argument("--output", help="Optional output path. Defaults to data/raw_samples/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
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
        print(f"DRY RUN: GET {COUNTRY_TO_ENDPOINT[args.country]}")
        print(f"Query params: {params}")
        print("Headers: Authorization: Basic <CAREERJET_API_KEY:>, Referer")
        print(f"Would write: {output_path}")
        return

    api_key = require_env("CAREERJET_API_KEY")
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    payload = request_json(
        "GET",
        COUNTRY_TO_ENDPOINT[args.country],
        headers={"Authorization": f"Basic {token}", "Referer": args.referer},
        params=params,
    )
    wrapped = {"_meta": {"source": "careerjet", "query": query_label, "country": args.country}, **payload}
    write_json(output_path, wrapped)
    print(f"Wrote local raw sample: {output_path}")


if __name__ == "__main__":
    main()
