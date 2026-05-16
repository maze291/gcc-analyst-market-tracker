from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import DERIVED_ONLY_DIR, NORMALIZED_DIR, REPO_ROOT, clean_text, duplicate_key, read_csv_rows, write_csv


HISTORY_DIR = DERIVED_ONLY_DIR / "history"
DEFAULT_OUTPUT = HISTORY_DIR / "unique_jobs.csv"

UNIQUE_JOB_FIELDS = [
    "unique_job_id",
    "dedupe_key",
    "job_title_raw",
    "job_title_normalized",
    "company_name",
    "country",
    "city",
    "role_category",
    "seniority",
    "skills_extracted",
    "skill_count",
    "salary_present",
    "salary_range_if_listed",
    "employment_type",
    "work_arrangement",
    "industry",
    "posting_date",
    "posting_month",
    "freshness_bucket",
    "first_seen",
    "last_seen",
    "seen_count",
    "source_count",
    "sources",
    "source_keys",
    "source_observation_counts",
    "source_record_ids",
    "source_domains",
    "queries_seen",
    "restricted_source_flag",
    "possible_pii_raw_pattern_flag",
    "validation_level",
    "confidence_score",
    "confidence_notes",
]


@dataclass(frozen=True)
class SourceInput:
    key: str
    label: str
    normalized_path: Path
    review_path: Path
    include_in_main_counts: bool = True


def review_path(name: str) -> Path:
    auto_path = REPO_ROOT / "feasibility_tests" / "results" / f"{name}_review_auto.csv"
    if auto_path.exists():
        return auto_path
    return REPO_ROOT / "feasibility_tests" / "results" / f"{name}_review.csv"


SOURCES = [
    SourceInput(
        key="jsearch",
        label="JSearch / OpenWeb Ninja",
        normalized_path=NORMALIZED_DIR / "jsearch_deduped.csv",
        review_path=review_path("jsearch"),
    ),
    SourceInput(
        key="careerjet",
        label="Careerjet",
        normalized_path=NORMALIZED_DIR / "careerjet_deduped.csv",
        review_path=review_path("careerjet"),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the V2 unique-jobs layer from reviewed normalized rows.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--snapshot-date", default=dt.date.today().isoformat())
    parser.add_argument("--cities", help="Optional comma-separated city filter for comparable scoped outputs.")
    parser.add_argument("--countries", help="Optional comma-separated country filter for comparable scoped outputs.")
    return parser.parse_args()


def clean_country(value: str) -> str:
    text = clean_text(value)
    if text.upper() == "AE":
        return "United Arab Emirates"
    if text.upper() == "SA":
        return "Saudi Arabia"
    if text.upper() == "QA":
        return "Qatar"
    if text.upper() == "KW":
        return "Kuwait"
    if text.upper() == "BH":
        return "Bahrain"
    if text.upper() == "OM":
        return "Oman"
    return text


def parse_csv_filter(value: str | None, *, country: bool = False) -> set[str]:
    if not value:
        return set()
    items = [part.strip() for part in value.split(",") if part.strip()]
    if country:
        return {clean_country(item) for item in items}
    return set(items)


def split_values(value: str) -> list[str]:
    return [part.strip() for part in clean_text(value).split(";") if part.strip()]


def parse_date(value: str) -> dt.date | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def max_date(values: list[str]) -> str:
    dates = [date for value in values if (date := parse_date(value))]
    return max(dates).isoformat() if dates else ""


def min_date(values: list[str]) -> str:
    dates = [date for value in values if (date := parse_date(value))]
    return min(dates).isoformat() if dates else ""


def posting_month(value: str) -> str:
    text = clean_text(value)
    return text[:7] if len(text) >= 7 else "Unknown"


def freshness_bucket(posting_date: str, snapshot_date: str) -> str:
    posted = parse_date(posting_date)
    snapshot = parse_date(snapshot_date)
    if not posted or not snapshot:
        return "unknown"
    age = (snapshot - posted).days
    if age < 0:
        return "future_dated"
    if age <= 30:
        return "fresh_0_30_days"
    if age <= 90:
        return "recent_31_90_days"
    return "old_90_plus_days"


def stable_unique_id(group_key: str) -> str:
    digest = hashlib.sha1(group_key.encode("utf-8")).hexdigest()[:12]
    return f"uj_{digest}"


def yes(value: Any) -> bool:
    return clean_text(value).lower() == "yes"


def review_decision(review: dict[str, str]) -> str:
    return clean_text(review.get("reviewer_decision")).lower()


def reviewed_rows(source: SourceInput) -> list[dict[str, str]]:
    normalized = read_csv_rows(source.normalized_path)
    review = read_csv_rows(source.review_path)
    if len(normalized) != len(review):
        raise SystemExit(
            f"{source.label}: normalized/review row mismatch "
            f"({len(normalized)} normalized vs {len(review)} review)."
        )

    rows: list[dict[str, str]] = []
    for norm, rev in zip(normalized, review):
        if review_decision(rev) != "include":
            continue
        row = dict(norm)
        row["_source_key"] = source.key
        row["_source_label"] = source.label
        row["_role_category"] = clean_text(rev.get("analyst_role_category")) or clean_text(norm.get("function"))
        row["_country"] = clean_country(clean_text(norm.get("country")) or clean_text(rev.get("country_target")))
        row["_city"] = clean_text(norm.get("city")) or clean_text(rev.get("city_target"))
        row["_dedupe_key"] = duplicate_key(norm) or f"{source.key}:{clean_text(norm.get('source_record_id'))}"
        rows.append(row)
    return rows


def representative_score(row: dict[str, str]) -> tuple[int, int, int, int, int]:
    return (
        0 if row.get("restricted_source_flag") == "yes" else 1,
        0 if row.get("pii_or_recruiter_data_flag") == "yes" else 1,
        1 if clean_text(row.get("company_name")) else 0,
        1 if clean_text(row.get("posting_date")) else 0,
        1 if clean_text(row.get("skills_extracted")) else 0,
    )


def choose_representative(rows: list[dict[str, str]]) -> dict[str, str]:
    return sorted(rows, key=representative_score, reverse=True)[0]


def confidence(group_rows: list[dict[str, str]], rep: dict[str, str]) -> tuple[int, str]:
    source_count = len({row["_source_key"] for row in group_rows})
    seen_count = len(group_rows)
    score = 40
    notes: list[str] = ["Included by auto-review."]

    if clean_text(rep.get("company_name")):
        score += 15
    else:
        notes.append("Missing company.")
    if clean_text(rep.get("_city")):
        score += 10
    else:
        notes.append("Missing city.")
    if clean_text(rep.get("posting_date")):
        score += 10
    else:
        notes.append("Missing posting date.")
    if clean_text(rep.get("skills_extracted")):
        score += 10
    else:
        notes.append("No extracted skills.")
    if source_count > 1:
        score += 10
        notes.append("Seen across multiple sources.")
    if seen_count > 1:
        score += 5
        notes.append("Seen multiple times.")
    if any(row.get("restricted_source_flag") == "yes" for row in group_rows):
        score -= 15
        notes.append("Restricted-source signal present.")
    if any(row.get("pii_or_recruiter_data_flag") == "yes" for row in group_rows):
        score -= 5
        notes.append("Raw input had possible contact pattern.")

    return max(0, min(100, score)), " ".join(notes)


def validation_level(group_rows: list[dict[str, str]]) -> str:
    source_count = len({row["_source_key"] for row in group_rows})
    if source_count > 1:
        return "multi_source"
    if len(group_rows) > 1:
        return "repeat_seen_single_source"
    return "single_source"


def build_unique_jobs(
    snapshot_date: str,
    *,
    cities: set[str] | None = None,
    countries: set[str] | None = None,
) -> list[dict[str, str]]:
    source_rows: list[dict[str, str]] = []
    for source in SOURCES:
        if not source.normalized_path.exists():
            raise SystemExit(f"Missing normalized input: {source.normalized_path}")
        if not source.review_path.exists():
            raise SystemExit(f"Missing review input: {source.review_path}")
        source_rows.extend(reviewed_rows(source))

    if cities:
        source_rows = [row for row in source_rows if row.get("_city") in cities]
    if countries:
        source_rows = [row for row in source_rows if row.get("_country") in countries]

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        grouped[row["_dedupe_key"]].append(row)

    unique_jobs: list[dict[str, str]] = []
    for group_key, rows in sorted(grouped.items(), key=lambda item: item[0]):
        rep = choose_representative(rows)
        source_counts = Counter(row["_source_key"] for row in rows)
        sources = sorted({row["_source_label"] for row in rows})
        source_keys = sorted(source_counts)
        skills = sorted({skill for row in rows for skill in split_values(row.get("skills_extracted", ""))})
        posting_date = max_date([row.get("posting_date", "") for row in rows])
        first_seen = min_date([row.get("date_seen", "") for row in rows])
        last_seen = max_date([row.get("date_seen", "") for row in rows])
        score, notes = confidence(rows, rep)
        salary_present = any(
            clean_text(row.get("salary_range_if_listed"))
            or clean_text(row.get("salary_min"))
            or clean_text(row.get("salary_max"))
            for row in rows
        )
        unique_jobs.append(
            {
                "unique_job_id": stable_unique_id(group_key),
                "dedupe_key": group_key,
                "job_title_raw": clean_text(rep.get("job_title_raw")),
                "job_title_normalized": clean_text(rep.get("job_title_normalized")),
                "company_name": clean_text(rep.get("company_name")),
                "country": clean_text(rep.get("_country")),
                "city": clean_text(rep.get("_city")),
                "role_category": clean_text(rep.get("_role_category")) or "Other Analyst",
                "seniority": clean_text(rep.get("seniority")),
                "skills_extracted": "; ".join(skills),
                "skill_count": str(len(skills)),
                "salary_present": "yes" if salary_present else "no",
                "salary_range_if_listed": clean_text(rep.get("salary_range_if_listed")),
                "employment_type": clean_text(rep.get("employment_type")),
                "work_arrangement": clean_text(rep.get("work_arrangement")),
                "industry": clean_text(rep.get("industry")),
                "posting_date": posting_date,
                "posting_month": posting_month(posting_date),
                "freshness_bucket": freshness_bucket(posting_date, snapshot_date),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "seen_count": str(len(rows)),
                "source_count": str(len(source_keys)),
                "sources": "; ".join(sources),
                "source_keys": "; ".join(source_keys),
                "source_observation_counts": "; ".join(f"{key}:{source_counts[key]}" for key in source_keys),
                "source_record_ids": "; ".join(
                    sorted({f"{row['_source_key']}:{clean_text(row.get('source_record_id'))}" for row in rows if clean_text(row.get("source_record_id"))})
                ),
                "source_domains": "; ".join(sorted({clean_text(row.get("source_url_domain_only")) for row in rows if clean_text(row.get("source_url_domain_only"))})),
                "queries_seen": "; ".join(sorted({clean_text(row.get("query_used")) for row in rows if clean_text(row.get("query_used"))})),
                "restricted_source_flag": "yes" if any(row.get("restricted_source_flag") == "yes" for row in rows) else "no",
                "possible_pii_raw_pattern_flag": "yes" if any(row.get("pii_or_recruiter_data_flag") == "yes" for row in rows) else "no",
                "validation_level": validation_level(rows),
                "confidence_score": str(score),
                "confidence_notes": notes,
            }
        )
    return unique_jobs


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    rows = build_unique_jobs(
        args.snapshot_date,
        cities=parse_csv_filter(args.cities),
        countries=parse_csv_filter(args.countries, country=True),
    )
    write_csv(output, rows, UNIQUE_JOB_FIELDS)
    print(f"Wrote {len(rows)} unique jobs: {output}")


if __name__ == "__main__":
    main()
