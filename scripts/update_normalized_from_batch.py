from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from common import (
    NORMALIZED_DIR,
    NORMALIZED_FIELDS,
    duplicate_key,
    extract_items,
    normalize_record,
    read_csv_rows,
    read_json,
    write_csv,
)


SOURCE_OUTPUTS = {
    "jsearch": {
        "all": NORMALIZED_DIR / "jsearch_normalized_all.csv",
        "deduped": NORMALIZED_DIR / "jsearch_deduped.csv",
    },
    "careerjet": {
        "all": NORMALIZED_DIR / "careerjet_normalized_all.csv",
        "deduped": NORMALIZED_DIR / "careerjet_deduped.csv",
    },
    "jooble": {
        "all": NORMALIZED_DIR / "jooble_normalized_all.csv",
        "deduped": NORMALIZED_DIR / "jooble_deduped.csv",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize successful raw samples from a batch manifest, append unseen records, and refresh duplicate groups."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCE_OUTPUTS), default=sorted(SOURCE_OUTPUTS))
    parser.add_argument("--refresh-existing", action="store_true", help="Re-normalize and replace rows whose source record IDs already exist.")
    return parser.parse_args()


def row_identity(row: dict[str, str]) -> str:
    source = row.get("source_name", "")
    record_id = row.get("source_record_id", "").strip()
    if record_id:
        return f"{source}|id|{record_id}"
    key = duplicate_key(row)
    query = row.get("query_used", "").strip().lower()
    return f"{source}|fallback|{key}|{query}"


def assign_duplicate_groups(rows: list[dict[str, str]]) -> list[dict[str, str]]:
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
    return rows


def normalize_manifest_rows(manifest_rows: list[dict[str, str]], source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest_row in manifest_rows:
        if manifest_row.get("source") != source:
            continue
        if manifest_row.get("status") not in {"ok", "skipped_existing"}:
            continue
        path_text = manifest_row.get("output_path", "")
        if not path_text:
            continue
        path = Path(path_text)
        if not path.exists():
            continue
        payload = read_json(path)
        query_used = str((payload.get("_meta") or {}).get("query") or manifest_row.get("query_label") or "")
        for item in extract_items(payload):
            rows.append(normalize_record(item, source, query_used=query_used))
    return rows


def main() -> None:
    args = parse_args()
    manifest_rows = read_csv_rows(Path(args.manifest))

    for source in args.sources:
        paths = SOURCE_OUTPUTS[source]
        existing = read_csv_rows(paths["all"]) if paths["all"].exists() else []
        identity_to_index = {row_identity(row): index for index, row in enumerate(existing)}
        seen = set(identity_to_index)
        incoming = normalize_manifest_rows(manifest_rows, source)

        added: list[dict[str, str]] = []
        refreshed = 0
        skipped = 0
        for row in incoming:
            identity = row_identity(row)
            if identity in seen:
                if args.refresh_existing:
                    existing[identity_to_index[identity]] = row
                    refreshed += 1
                else:
                    skipped += 1
                continue
            identity_to_index[identity] = len(existing) + len(added)
            seen.add(identity)
            added.append(row)

        all_rows = existing + added
        write_csv(paths["all"], all_rows, NORMALIZED_FIELDS)
        deduped = assign_duplicate_groups([dict(row) for row in all_rows])
        write_csv(paths["deduped"], deduped, NORMALIZED_FIELDS)
        duplicate_groups = len({row["duplicate_group_id"] for row in deduped if row.get("duplicate_group_id")})

        print(
            f"{source}: {len(existing)} existing + {len(added)} added "
            f"({refreshed} refreshed, {skipped} repeated source records skipped) -> {len(all_rows)} rows; "
            f"{duplicate_groups} duplicate groups"
        )
        print(f"Wrote {paths['all']}")
        print(f"Wrote {paths['deduped']}")


if __name__ == "__main__":
    main()
