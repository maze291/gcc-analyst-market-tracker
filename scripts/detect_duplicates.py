from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from common import NORMALIZED_FIELDS, duplicate_key, read_csv_rows, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assign duplicate groups across APIs using normalized title/company/location/date.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv_rows(Path(args.input))
    keys = [duplicate_key(row) for row in rows]
    counts = Counter(key for key in keys if key)
    group_ids: dict[str, str] = {}
    next_id = 1

    for row, key in zip(rows, keys):
        if key and counts[key] > 1:
            if key not in group_ids:
                group_ids[key] = f"dup_{next_id:04d}"
                next_id += 1
            row["duplicate_group_id"] = group_ids[key]
        else:
            row["duplicate_group_id"] = ""

    write_csv(Path(args.output), rows, NORMALIZED_FIELDS)
    print(f"Wrote {len(rows)} rows with {len(group_ids)} duplicate groups: {args.output}")


if __name__ == "__main__":
    main()
