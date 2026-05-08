from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import DERIVED_ONLY_DIR, NORMALIZED_DIR, REPO_ROOT, duplicate_key, read_csv_rows, write_csv


DASHBOARD_DIR = DERIVED_ONLY_DIR / "dashboard"


@dataclass(frozen=True)
class SourceInputs:
    key: str
    label: str
    normalized_path: Path
    review_path: Path


SOURCES = [
    SourceInputs(
        key="jsearch",
        label="JSearch / OpenWeb Ninja",
        normalized_path=NORMALIZED_DIR / "jsearch_deduped.csv",
        review_path=REPO_ROOT / "feasibility_tests" / "results" / "jsearch_review.csv",
    ),
    SourceInputs(
        key="careerjet",
        label="Careerjet",
        normalized_path=NORMALIZED_DIR / "careerjet_deduped.csv",
        review_path=REPO_ROOT / "feasibility_tests" / "results" / "careerjet_review.csv",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build aggregate-only v1 dashboard data from normalized samples and manual reviews."
    )
    parser.add_argument("--output-dir", default=str(DASHBOARD_DIR))
    return parser.parse_args()


def yes(value: Any) -> bool:
    return str(value or "").strip().lower() == "yes"


def clean(value: Any) -> str:
    return str(value or "").strip()


def pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


def country_name(value: str) -> str:
    text = clean(value)
    if text.upper() == "AE":
        return "United Arab Emirates"
    if text.upper() == "SA":
        return "Saudi Arabia"
    return text


def split_skills(value: str) -> list[str]:
    return [skill.strip() for skill in clean(value).split(";") if skill.strip()]


def month_bucket(row: dict[str, str]) -> str:
    date = clean(row.get("posting_date"))
    if len(date) >= 7:
        return date[:7]
    return "Unknown"


def reviewed_records(source: SourceInputs) -> list[dict[str, str]]:
    normalized = read_csv_rows(source.normalized_path)
    review = read_csv_rows(source.review_path)
    if len(normalized) != len(review):
        raise SystemExit(
            f"{source.label}: normalized/review row mismatch "
            f"({len(normalized)} normalized vs {len(review)} review)."
        )

    rows: list[dict[str, str]] = []
    for index, (norm, rev) in enumerate(zip(normalized, review), start=1):
        country = country_name(clean(norm.get("country")) or clean(rev.get("country_target")))
        city = clean(norm.get("city")) or clean(rev.get("city_target"))
        role = clean(rev.get("analyst_role_category")) or clean(norm.get("function")) or "Uncategorized"
        record = {
            "source_key": source.key,
            "source_name": source.label,
            "row_number": str(index),
            "country": country,
            "city": city or "Unknown",
            "role_category": role,
            "reviewer_decision": clean(rev.get("reviewer_decision")),
            "title_relevance": clean(rev.get("job_title_relevant_yes_no")),
            "company_present": "yes" if yes(rev.get("company_present_yes_no")) else "no",
            "city_present": "yes" if yes(rev.get("city_present_yes_no")) else "no",
            "posting_date_present": "yes" if yes(rev.get("posting_date_present_yes_no")) else "no",
            "salary_present": "yes" if yes(rev.get("salary_present_yes_no")) else "no",
            "description_present": "yes" if yes(rev.get("description_present_yes_no")) else "no",
            "skills_extractable": "yes" if yes(rev.get("skills_extractable_yes_no")) else "no",
            "restricted_source": "yes" if yes(rev.get("restricted_source_yes_no")) else "no",
            "possible_pii_raw_pattern": "yes" if yes(rev.get("pii_or_recruiter_data_yes_no")) else "no",
            "duplicate_flag": "yes" if yes(rev.get("duplicate_yes_no")) else "no",
            "posting_month": month_bucket(norm),
            "skills": "; ".join(split_skills(norm.get("skills_extracted", ""))),
            "dedupe_key": duplicate_key(norm) or f"{source.key}:{index}",
        }
        rows.append(record)
    return rows


def count_by(records: list[dict[str, str]], *fields: str) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, ...]] = Counter()
    for row in records:
        key = tuple(row.get(field, "Unknown") or "Unknown" for field in fields)
        counter[key] += 1
    result = []
    for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        out = {field: value for field, value in zip(fields, key)}
        out["count"] = count
        result.append(out)
    return result


def status_counts(records: list[dict[str, str]]) -> dict[str, int]:
    return dict(Counter(row["reviewer_decision"] or "unknown" for row in records))


def source_quality(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in records:
        grouped[row["source_name"]].append(row)

    rows = []
    for source_name, source_rows in sorted(grouped.items()):
        reviewed = len(source_rows)
        included = sum(1 for row in source_rows if row["reviewer_decision"] == "include")
        review_later = sum(1 for row in source_rows if row["reviewer_decision"] == "review_later")
        rows.append(
            {
                "source_name": source_name,
                "reviewed_rows": reviewed,
                "included_rows": included,
                "review_later_rows": review_later,
                "title_relevance_rate": pct(sum(1 for row in source_rows if row["title_relevance"] == "yes"), reviewed),
                "company_presence_rate": pct(sum(1 for row in source_rows if row["company_present"] == "yes"), reviewed),
                "city_presence_rate": pct(sum(1 for row in source_rows if row["city_present"] == "yes"), reviewed),
                "posting_date_presence_rate": pct(
                    sum(1 for row in source_rows if row["posting_date_present"] == "yes"), reviewed
                ),
                "salary_coverage_rate": pct(sum(1 for row in source_rows if row["salary_present"] == "yes"), reviewed),
                "skills_extractable_rate": pct(sum(1 for row in source_rows if row["skills_extractable"] == "yes"), reviewed),
                "restricted_source_rate": pct(sum(1 for row in source_rows if row["restricted_source"] == "yes"), reviewed),
                "possible_pii_raw_pattern_rate": pct(
                    sum(1 for row in source_rows if row["possible_pii_raw_pattern"] == "yes"), reviewed
                ),
                "duplicate_flag_rate": pct(sum(1 for row in source_rows if row["duplicate_flag"] == "yes"), reviewed),
            }
        )
    return rows


def skill_counts(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    source_counter: dict[str, Counter[str]] = defaultdict(Counter)
    for row in records:
        for skill in split_skills(row.get("skills")):
            counter[skill] += 1
            source_counter[skill][row["source_name"]] += 1

    result = []
    for skill, count in counter.most_common():
        out: dict[str, Any] = {"skill": skill, "count": count}
        for source_name, source_count in source_counter[skill].items():
            out[source_name] = source_count
        result.append(out)
    return result


def salary_coverage(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for item in count_by(records, "source_name", "country"):
        source_rows = [
            row
            for row in records
            if row["source_name"] == item["source_name"] and row["country"] == item["country"]
        ]
        rows.append(
            {
                "source_name": item["source_name"],
                "country": item["country"],
                "included_rows": len(source_rows),
                "salary_present_rows": sum(1 for row in source_rows if row["salary_present"] == "yes"),
                "salary_coverage_rate": pct(sum(1 for row in source_rows if row["salary_present"] == "yes"), len(source_rows)),
            }
        )
    return rows


def fields_for(rows: list[dict[str, Any]], preferred: list[str]) -> list[str]:
    fields = list(preferred)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, str]] = []
    for source in SOURCES:
        if not source.normalized_path.exists():
            raise SystemExit(f"Missing normalized input: {source.normalized_path}")
        if not source.review_path.exists():
            raise SystemExit(f"Missing review input: {source.review_path}")
        all_records.extend(reviewed_records(source))

    included = [row for row in all_records if row["reviewer_decision"] == "include"]
    review_later = [row for row in all_records if row["reviewer_decision"] == "review_later"]
    unique_included_keys = {row["dedupe_key"] for row in included}
    restricted_rows = [row for row in all_records if row["restricted_source"] == "yes"]
    pii_rows = [row for row in all_records if row["possible_pii_raw_pattern"] == "yes"]
    salary_rows = [row for row in included if row["salary_present"] == "yes"]

    aggregates = {
        "metadata": {
            "title": "GCC Analyst Market Tracker v1",
            "status": "Private prototype",
            "data_scope": "Aggregate-only dashboard data generated from Week 0 reviewed samples.",
            "public_release_status": "Blocked pending provider permission for aggregate public reporting.",
            "retained_pii_contact_fields": 0,
            "sources": [source.label for source in SOURCES],
        },
        "kpis": {
            "reviewed_rows": len(all_records),
            "included_rows": len(included),
            "deduped_included_estimate": len(unique_included_keys),
            "review_later_rows": len(review_later),
            "sources_tested": len(SOURCES),
            "countries": len({row["country"] for row in all_records if row["country"] and row["country"] != "Unknown"}),
            "cities": len({row["city"] for row in all_records if row["city"] and row["city"] != "Unknown"}),
            "salary_coverage_rate": pct(len(salary_rows), len(included)),
            "restricted_source_rate_all_reviewed": pct(len(restricted_rows), len(all_records)),
            "possible_pii_raw_pattern_rate_all_reviewed": pct(len(pii_rows), len(all_records)),
        },
        "source_quality": source_quality(all_records),
        "postings_by_city": count_by(included, "country", "city"),
        "role_mix": count_by(included, "role_category"),
        "role_mix_by_source": count_by(included, "source_name", "role_category"),
        "postings_by_source": count_by(included, "source_name"),
        "posting_months": count_by(included, "posting_month"),
        "skill_counts": skill_counts(included),
        "salary_coverage": salary_coverage(included),
        "review_status": status_counts(all_records),
        "risk_counts": {
            "restricted_source_rows": len(restricted_rows),
            "possible_pii_raw_pattern_rows": len(pii_rows),
            "retained_pii_contact_fields": 0,
        },
        "data_handling": [
            "Dashboard files are aggregate-only.",
            "No full job postings, descriptions, application URLs, recruiter names, emails, phone numbers, or profile links are included.",
            "Possible PII/contact pattern metrics refer to temporary raw input flags, not retained fields.",
            "Public launch remains blocked until provider permission is clarified.",
        ],
    }

    write_json(output_dir / "dashboard_data.json", aggregates)
    write_csv(output_dir / "postings_by_city.csv", aggregates["postings_by_city"], ["country", "city", "count"])
    write_csv(output_dir / "role_mix.csv", aggregates["role_mix"], ["role_category", "count"])
    write_csv(output_dir / "role_mix_by_source.csv", aggregates["role_mix_by_source"], ["source_name", "role_category", "count"])
    write_csv(output_dir / "postings_by_source.csv", aggregates["postings_by_source"], ["source_name", "count"])
    write_csv(
        output_dir / "skill_counts.csv",
        aggregates["skill_counts"],
        fields_for(aggregates["skill_counts"], ["skill", "count"]),
    )
    write_csv(
        output_dir / "source_quality.csv",
        aggregates["source_quality"],
        [
            "source_name",
            "reviewed_rows",
            "included_rows",
            "review_later_rows",
            "title_relevance_rate",
            "company_presence_rate",
            "city_presence_rate",
            "posting_date_presence_rate",
            "salary_coverage_rate",
            "skills_extractable_rate",
            "restricted_source_rate",
            "possible_pii_raw_pattern_rate",
            "duplicate_flag_rate",
        ],
    )
    write_csv(
        output_dir / "salary_coverage.csv",
        aggregates["salary_coverage"],
        ["source_name", "country", "included_rows", "salary_present_rows", "salary_coverage_rate"],
    )

    print(f"Wrote aggregate dashboard data to: {output_dir}")
    print(f"Reviewed rows: {len(all_records)}")
    print(f"Included rows: {len(included)}")
    print(f"Deduped included estimate: {len(unique_included_keys)}")
    print("Retained PII/contact fields: 0")


if __name__ == "__main__":
    main()
