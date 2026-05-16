from __future__ import annotations

import argparse
import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from common import DERIVED_ONLY_DIR, REPO_ROOT, clean_text, read_csv_rows, write_csv


HISTORY_DIR = DERIVED_ONLY_DIR / "history"
UNIQUE_JOBS_PATH = HISTORY_DIR / "unique_jobs.csv"
SKILL_TAXONOMY_PATH = REPO_ROOT / "config" / "skill_taxonomy.csv"

SUMMARY_FIELDS = [
    "snapshot_date",
    "total_unique_jobs",
    "countries",
    "cities",
    "role_categories",
    "skill_count",
    "source_observations",
    "avg_confidence_score",
    "fresh_jobs",
    "recent_jobs",
    "old_jobs",
    "unknown_freshness_jobs",
    "multi_source_jobs",
    "repeat_seen_single_source_jobs",
    "single_source_jobs",
    "restricted_source_jobs",
    "possible_pii_raw_pattern_jobs",
    "salary_jobs",
]

DIMENSION_FIELDS = ["snapshot_date", "dimension", "value", "country", "count", "avg_confidence_score", "fresh_jobs"]
CITY_FIELDS = ["snapshot_date", "country", "city", "count", "avg_confidence_score", "fresh_jobs"]
ROLE_FIELDS = ["snapshot_date", "role_category", "count", "avg_confidence_score", "fresh_jobs"]
SKILL_FIELDS = ["snapshot_date", "skill", "skill_group", "count", "avg_confidence_score", "fresh_jobs"]
SOURCE_FIELDS = ["snapshot_date", "source_key", "source_name", "unique_job_count", "observation_count"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append/replace V2 trend snapshot rows from unique_jobs.csv.")
    parser.add_argument("--input", default=str(UNIQUE_JOBS_PATH))
    parser.add_argument("--output-dir", default=str(HISTORY_DIR))
    parser.add_argument("--snapshot-date", default=dt.date.today().isoformat())
    return parser.parse_args()


def split_values(value: str) -> list[str]:
    return [part.strip() for part in clean_text(value).split(";") if part.strip()]


def int_value(value: str) -> int:
    try:
        return int(clean_text(value))
    except ValueError:
        return 0


def avg_confidence(rows: list[dict[str, str]]) -> str:
    values = [int_value(row.get("confidence_score", "")) for row in rows if clean_text(row.get("confidence_score"))]
    return f"{mean(values):.1f}" if values else "0.0"


def fresh_count(rows: list[dict[str, str]]) -> int:
    return sum(1 for row in rows if row.get("freshness_bucket") in {"fresh_0_30_days", "future_dated"})


def load_skill_taxonomy() -> dict[str, str]:
    if not SKILL_TAXONOMY_PATH.exists():
        return {}
    return {row["skill"]: row["skill_group"] for row in read_csv_rows(SKILL_TAXONOMY_PATH)}


def replace_snapshot(path: Path, fieldnames: list[str], rows: list[dict[str, str]], snapshot_date: str) -> None:
    existing = read_csv_rows(path) if path.exists() else []
    kept = [row for row in existing if row.get("snapshot_date") != snapshot_date]
    write_csv(path, kept + rows, fieldnames)


def summary_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    freshness = Counter(row.get("freshness_bucket") or "unknown" for row in rows)
    validation = Counter(row.get("validation_level") or "single_source" for row in rows)
    skills = {skill for row in rows for skill in split_values(row.get("skills_extracted", ""))}
    return [
        {
            "snapshot_date": snapshot_date,
            "total_unique_jobs": str(len(rows)),
            "countries": str(len({row.get("country") for row in rows if clean_text(row.get("country"))})),
            "cities": str(len({row.get("city") for row in rows if clean_text(row.get("city"))})),
            "role_categories": str(len({row.get("role_category") for row in rows if clean_text(row.get("role_category"))})),
            "skill_count": str(len(skills)),
            "source_observations": str(sum(int_value(row.get("seen_count", "0")) for row in rows)),
            "avg_confidence_score": avg_confidence(rows),
            "fresh_jobs": str(freshness["fresh_0_30_days"] + freshness["future_dated"]),
            "recent_jobs": str(freshness["recent_31_90_days"]),
            "old_jobs": str(freshness["old_90_plus_days"]),
            "unknown_freshness_jobs": str(freshness["unknown"]),
            "multi_source_jobs": str(validation["multi_source"]),
            "repeat_seen_single_source_jobs": str(validation["repeat_seen_single_source"]),
            "single_source_jobs": str(validation["single_source"]),
            "restricted_source_jobs": str(sum(1 for row in rows if row.get("restricted_source_flag") == "yes")),
            "possible_pii_raw_pattern_jobs": str(sum(1 for row in rows if row.get("possible_pii_raw_pattern_flag") == "yes")),
            "salary_jobs": str(sum(1 for row in rows if row.get("salary_present") == "yes")),
        }
    ]


def dimension_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    dimensions = [
        ("city", "city"),
        ("role", "role_category"),
        ("freshness", "freshness_bucket"),
        ("validation", "validation_level"),
    ]
    for dimension, field in dimensions:
        grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            value = clean_text(row.get(field)) or "Unknown"
            country = clean_text(row.get("country")) if dimension == "city" else ""
            grouped[(value, country)].append(row)
        for (value, country), group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
            output.append(
                {
                    "snapshot_date": snapshot_date,
                    "dimension": dimension,
                    "value": value,
                    "country": country,
                    "count": str(len(group)),
                    "avg_confidence_score": avg_confidence(group),
                    "fresh_jobs": str(fresh_count(group)),
                }
            )
    return output


def city_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        country = clean_text(row.get("country")) or "Unknown"
        city = clean_text(row.get("city")) or "Unknown"
        grouped[(country, city)].append(row)
    return [
        {
            "snapshot_date": snapshot_date,
            "country": country,
            "city": city,
            "count": str(len(group)),
            "avg_confidence_score": avg_confidence(group),
            "fresh_jobs": str(fresh_count(group)),
        }
        for (country, city), group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def role_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        role = clean_text(row.get("role_category")) or "Unknown"
        grouped[role].append(row)
    return [
        {
            "snapshot_date": snapshot_date,
            "role_category": role,
            "count": str(len(group)),
            "avg_confidence_score": avg_confidence(group),
            "fresh_jobs": str(fresh_count(group)),
        }
        for role, group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def skill_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    taxonomy = load_skill_taxonomy()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for skill in split_values(row.get("skills_extracted", "")):
            grouped[skill].append(row)
    return [
        {
            "snapshot_date": snapshot_date,
            "skill": skill,
            "skill_group": taxonomy.get(skill, "Other"),
            "count": str(len(group)),
            "avg_confidence_score": avg_confidence(group),
            "fresh_jobs": str(fresh_count(group)),
        }
        for skill, group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def source_rows(rows: list[dict[str, str]], snapshot_date: str) -> list[dict[str, str]]:
    source_names: dict[str, str] = {
        "jsearch": "JSearch / OpenWeb Ninja",
        "careerjet": "Careerjet",
        "jooble": "Jooble",
    }
    unique_counts: Counter[str] = Counter()
    observation_counts: Counter[str] = Counter()
    for row in rows:
        for source_key in split_values(row.get("source_keys", "")):
            unique_counts[source_key] += 1
        for part in split_values(row.get("source_observation_counts", "")):
            if ":" not in part:
                continue
            source_key, count = part.split(":", 1)
            observation_counts[source_key] += int_value(count)
    return [
        {
            "snapshot_date": snapshot_date,
            "source_key": key,
            "source_name": source_names.get(key, key),
            "unique_job_count": str(unique_counts[key]),
            "observation_count": str(observation_counts[key]),
        }
        for key in sorted(unique_counts)
    ]


def main() -> None:
    args = parse_args()
    rows = read_csv_rows(Path(args.input))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    replace_snapshot(output_dir / "trend_daily_summary.csv", SUMMARY_FIELDS, summary_rows(rows, args.snapshot_date), args.snapshot_date)
    replace_snapshot(output_dir / "trend_city.csv", CITY_FIELDS, city_rows(rows, args.snapshot_date), args.snapshot_date)
    replace_snapshot(output_dir / "trend_role.csv", ROLE_FIELDS, role_rows(rows, args.snapshot_date), args.snapshot_date)
    replace_snapshot(output_dir / "trend_dimensions.csv", DIMENSION_FIELDS, dimension_rows(rows, args.snapshot_date), args.snapshot_date)
    replace_snapshot(output_dir / "trend_skill.csv", SKILL_FIELDS, skill_rows(rows, args.snapshot_date), args.snapshot_date)
    replace_snapshot(output_dir / "trend_source.csv", SOURCE_FIELDS, source_rows(rows, args.snapshot_date), args.snapshot_date)
    print(f"Wrote trend snapshots for {args.snapshot_date} to: {output_dir}")


if __name__ == "__main__":
    main()
