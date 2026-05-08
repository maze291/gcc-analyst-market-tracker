from __future__ import annotations

import argparse
from pathlib import Path

from common import NORMALIZED_FIELDS, extract_items, normalize_record, read_json, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize local raw job samples into aggregate-safe CSV fields.")
    parser.add_argument("--source", required=True, choices=["jsearch", "careerjet", "jooble", "adzuna"])
    parser.add_argument("--input", nargs="+", required=True, help="One or more local raw JSON files.")
    parser.add_argument("--output", required=True, help="Output CSV path under data/normalized/.")
    parser.add_argument("--query-used", default="", help="Optional override for query_used.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = []
    for input_path in args.input:
        payload = read_json(Path(input_path))
        query_used = args.query_used
        if isinstance(payload, dict) and not query_used:
            query_used = str((payload.get("_meta") or {}).get("query") or "")
        for item in extract_items(payload):
            rows.append(normalize_record(item, args.source, query_used=query_used))

    write_csv(Path(args.output), rows, NORMALIZED_FIELDS)
    print(f"Wrote {len(rows)} normalized rows: {args.output}")
    print("No full descriptions or full application URLs are written by this script.")


if __name__ == "__main__":
    main()
