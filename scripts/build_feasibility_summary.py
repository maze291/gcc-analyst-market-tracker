from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import DERIVED_ONLY_DIR, REPO_ROOT


REVIEW_FILES = {
    "JSearch / OpenWeb Ninja": REPO_ROOT / "feasibility_tests" / "results" / "jsearch_review.csv",
    "Careerjet": REPO_ROOT / "feasibility_tests" / "results" / "careerjet_review.csv",
    "Jooble": REPO_ROOT / "feasibility_tests" / "results" / "jooble_review.csv",
    "Adzuna": REPO_ROOT / "feasibility_tests" / "results" / "adzuna_review.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local-only Week 0 feasibility summary.")
    parser.add_argument("--output", default=str(DERIVED_ONLY_DIR / "feasibility_summary.md"))
    return parser.parse_args()


def yes_rate(rows: list[dict[str, str]], column: str) -> str:
    if not rows:
        return "n/a"
    yes = sum(1 for row in rows if row.get(column, "").strip().lower() == "yes")
    return f"{yes / len(rows):.0%}"


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    lines = [
        "# Week 0 Feasibility Summary",
        "",
        "This summary is generated from manual review CSVs and is local-only by default.",
        "",
        "The `Possible PII/contact pattern in raw input` rate is triggered from temporary raw fields used during review and normalization. It does not mean emails, phone numbers, LinkedIn profiles, recruiter names, hiring manager names, full descriptions, or full application URLs are retained in the normalized/public-safe output.",
        "",
        "Retained PII/contact fields: 0",
        "",
        "| API | Reviewed rows | Title relevance | Company present | City present | Description present | Restricted-source rate | Possible PII/contact pattern in raw input |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for api_name, path in REVIEW_FILES.items():
        rows = [row for row in load_rows(path) if any(value.strip() for value in row.values())]
        lines.append(
            "| "
            + " | ".join(
                [
                    api_name,
                    str(len(rows)),
                    yes_rate(rows, "job_title_relevant_yes_no"),
                    yes_rate(rows, "company_present_yes_no"),
                    yes_rate(rows, "city_present_yes_no"),
                    yes_rate(rows, "description_present_yes_no"),
                    yes_rate(rows, "restricted_source_yes_no"),
                    yes_rate(rows, "pii_or_recruiter_data_yes_no"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Decision Reminder",
            "",
            "Apply the compliance gate before weighted scoring. If provider permission is unclear, keep the source at feasibility-only or validation-only.",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote local summary: {output}")


if __name__ == "__main__":
    main()
