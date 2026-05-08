from __future__ import annotations

import argparse
from pathlib import Path

from common import NORMALIZED_FIELDS, is_restricted_domain, read_csv_rows, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flag restricted source domains in a normalized CSV.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", help="Optional CSV output path. If omitted, prints a summary only.")
    parser.add_argument("--domain-column", default="source_url_domain_only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv_rows(Path(args.input))
    restricted_count = 0
    for row in rows:
        flag = is_restricted_domain(row.get(args.domain_column, ""))
        row["restricted_source_flag"] = "yes" if flag else "no"
        restricted_count += int(flag)

    print(f"Rows scanned: {len(rows)}")
    print(f"Restricted rows: {restricted_count}")

    if args.output:
        write_csv(Path(args.output), rows, NORMALIZED_FIELDS)
        print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
