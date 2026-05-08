from __future__ import annotations

import argparse
import os
from pathlib import Path

from common import ensure_data_dirs, request_json, require_env, sample_path, write_json


DEFAULT_OPENWEBNINJA_API_URL = "https://api.openwebninja.com/jsearch/search"
DEFAULT_RAPIDAPI_URL = "https://jsearch.p.rapidapi.com/search"
DEFAULT_RAPIDAPI_HOST = "jsearch.p.rapidapi.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a local-only JSearch/OpenWeb Ninja sample.")
    parser.add_argument("--query", required=True, help="Search query, for example: Data Analyst Dubai")
    parser.add_argument("--limit", type=int, default=10, help="Requested result count for a tiny sample.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument(
        "--provider",
        choices=["rapidapi", "openwebninja"],
        default=os.environ.get("JSEARCH_PROVIDER", "rapidapi"),
        help="Use RapidAPI headers by default because Week 0 testing is currently via RapidAPI.",
    )
    parser.add_argument("--api-url", default=os.environ.get("JSEARCH_API_URL"))
    parser.add_argument("--auth-header", default=os.environ.get("JSEARCH_AUTH_HEADER"))
    parser.add_argument("--rapidapi-host", default=os.environ.get("JSEARCH_RAPIDAPI_HOST", DEFAULT_RAPIDAPI_HOST))
    parser.add_argument("--dry-run", action="store_true", help="Print request plan without calling the API.")
    parser.add_argument("--output", help="Optional output path. Defaults to data/raw_samples/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    output_path = Path(args.output) if args.output else sample_path("jsearch", args.query)
    params = {"query": args.query, "page": args.page, "num_pages": 1, "limit": args.limit}
    api_url = args.api_url
    headers: dict[str, str]

    if args.provider == "rapidapi":
        api_url = api_url or DEFAULT_RAPIDAPI_URL
        headers = {
            "X-RapidAPI-Key": "<JSEARCH_API_KEY>",
            "X-RapidAPI-Host": args.rapidapi_host,
        }
    else:
        api_url = api_url or DEFAULT_OPENWEBNINJA_API_URL
        auth_header = args.auth_header or "X-API-Key"
        headers = {auth_header: "<JSEARCH_API_KEY>"}

    if args.dry_run:
        print(f"DRY RUN: GET {api_url}")
        print(f"Query params: {params}")
        print(f"Headers: {headers}")
        print(f"Would write: {output_path}")
        return

    api_key = require_env("JSEARCH_API_KEY")
    live_headers = dict(headers)
    if args.provider == "rapidapi":
        live_headers["X-RapidAPI-Key"] = api_key
    else:
        live_headers[next(iter(live_headers))] = api_key
    payload = request_json(
        "GET",
        api_url,
        headers=live_headers,
        params=params,
    )
    wrapped = {"_meta": {"source": "jsearch", "query": args.query}, **payload}
    write_json(output_path, wrapped)
    print(f"Wrote local raw sample: {output_path}")


if __name__ == "__main__":
    main()
