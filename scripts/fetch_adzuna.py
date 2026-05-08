from __future__ import annotations

import argparse
from pathlib import Path

from common import ensure_data_dirs, request_json, require_env, sample_path, write_json


COUNTRY_TO_ADZUNA_CODE = {"AE": "ae", "SA": "sa"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guarded Adzuna fetcher. Adzuna is documentation-only unless written permission is obtained."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--country", choices=sorted(COUNTRY_TO_ADZUNA_CODE), required=True)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--i-have-written-permission", action="store_true")
    parser.add_argument("--output", help="Optional output path. Defaults to data/raw_samples/.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.i_have_written_permission:
        raise SystemExit(
            "Adzuna is blocked for v1 unless written permission is obtained. "
            "Re-run with --i-have-written-permission only after recording permission."
        )

    ensure_data_dirs()
    app_id = require_env("ADZUNA_APP_ID")
    app_key = require_env("ADZUNA_APP_KEY")
    country = COUNTRY_TO_ADZUNA_CODE[args.country]
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{args.page}"
    query_label = f"{args.query} {args.location}".strip()
    params = {"app_id": app_id, "app_key": app_key, "what": args.query, "where": args.location}
    output_path = Path(args.output) if args.output else sample_path("adzuna", query_label)

    if args.dry_run:
        print(f"DRY RUN: GET {url}")
        print("Query params include app_id/app_key from environment plus what/where.")
        print(f"Would write: {output_path}")
        return

    payload = request_json("GET", url, params=params)
    wrapped = {"_meta": {"source": "adzuna", "query": query_label, "country": args.country}, **payload}
    write_json(output_path, wrapped)
    print(f"Wrote local raw sample: {output_path}")


if __name__ == "__main__":
    main()
