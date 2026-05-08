from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import extract_items, extract_skills, flatten_text, has_pii_or_recruiter_data, read_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract skill labels from temporary local text or raw JSON.")
    parser.add_argument("--text", help="Text to inspect. Do not paste sensitive contact data.")
    parser.add_argument("--input", help="Optional local raw JSON file to inspect without writing output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.text and not args.input:
        raise SystemExit("Provide --text or --input.")

    if args.text:
        text = args.text
    else:
        payload = read_json(Path(args.input))
        text = flatten_text(extract_items(payload) or payload)

    result = {
        "skills": extract_skills(text),
        "pii_or_recruiter_data_flag": has_pii_or_recruiter_data(text),
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
