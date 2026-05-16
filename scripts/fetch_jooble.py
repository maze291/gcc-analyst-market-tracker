from __future__ import annotations

import argparse
from pathlib import Path

from common import ensure_data_dirs, request_json, require_env, sample_path, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a local-only Jooble sample.")
    parser.add_argument("--query", required=True, help="Keyword query, for example: Data Analyst")
    parser.add_argument("--location", required=True, help="Location, for example: Dubai or Riyadh")
    parser.add_argument("--limit", type=int, default=10, help="Used for review planning; Jooble may page by provider defaults.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Print request plan without calling the API.")
    parser.add_argument("--output", help="Optional output path. Defaults to data/raw_samples/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    query_label = f"{args.query} {args.location}".strip()
    output_path = Path(args.output) if args.output else sample_path("jooble", query_label)
    payload = {
        "keywords": args.query,
        "location": args.location,
        "page": args.page,
        "ResultOnPage": args.limit,
        "companysearch": "false",
    }

    if args.dry_run:
        print("DRY RUN: POST https://jooble.org/api/<JOOBLE_API_KEY>")
        print(f"JSON body: {payload}")
        print(f"Requested review limit: {args.limit}")
        print(f"Would write: {output_path}")
        return

    api_key = require_env("JOOBLE_API_KEY")
    response = request_json("POST", f"https://jooble.org/api/{api_key}", json_body=payload)
    wrapped = {"_meta": {"source": "jooble", "query": query_label}, **response}
    write_json(output_path, wrapped)
    print(f"Wrote local raw sample: {output_path}")


if __name__ == "__main__":
    main()
