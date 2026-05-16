from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import (
    NORMALIZED_DIR,
    RAW_SAMPLES_DIR,
    REPO_ROOT,
    clean_text,
    duplicate_key,
    extract_items,
    flatten_text,
    read_csv_rows,
    read_json,
    write_csv,
)


REVIEW_FIELDS = [
    "api_name",
    "sample_id",
    "query_used",
    "country_target",
    "city_target",
    "job_title_raw",
    "job_title_relevant_yes_no",
    "analyst_role_category",
    "company_present_yes_no",
    "country_present_yes_no",
    "city_present_yes_no",
    "salary_present_yes_no",
    "posting_date_present_yes_no",
    "description_present_yes_no",
    "description_full_or_snippet",
    "skills_extractable_yes_no",
    "employment_type_present_yes_no",
    "work_arrangement_present_yes_no",
    "source_domain",
    "restricted_source_yes_no",
    "duplicate_yes_no",
    "pii_or_recruiter_data_yes_no",
    "notes",
    "reviewer_decision",
]

SOURCE_FILES = {
    "jsearch": {
        "input": NORMALIZED_DIR / "jsearch_deduped.csv",
        "output": REPO_ROOT / "feasibility_tests" / "results" / "jsearch_review_auto.csv",
        "api_name": "JSearch / OpenWeb Ninja",
        "priority": 2,
    },
    "careerjet": {
        "input": NORMALIZED_DIR / "careerjet_deduped.csv",
        "output": REPO_ROOT / "feasibility_tests" / "results" / "careerjet_review_auto.csv",
        "api_name": "Careerjet",
        "priority": 1,
    },
    "jooble": {
        "input": NORMALIZED_DIR / "jooble_deduped.csv",
        "output": REPO_ROOT / "feasibility_tests" / "results" / "jooble_review_auto.csv",
        "api_name": "Jooble",
        "priority": 3,
    },
}

INCLUDE_PATTERNS = [
    ("Data Analyst", r"\bdata analyst\b|\banalytics analyst\b|\bdata\b.{0,40}\banalyst\b"),
    ("Business Analyst", r"\bbusiness analyst\b|\bbusiness systems analyst\b|\bbusiness excellence analyst\b"),
    ("BI Analyst", r"\bbi analyst\b|\bbusiness intelligence analyst\b|\bpower bi analyst\b|\bbusiness intelligence\b|\bbi\b.{0,30}\banalyst\b"),
    ("Financial Analyst", r"\bfinancial analyst\b|\bfinancial planning analyst\b|\bfinance analyst\b|\bfp&a analyst\b|\bcfo\b.{0,30}\banalyst\b|\bbudget(?:ing)?\b.{0,30}\banalyst\b|\btax analyst\b|\btreasury\b.{0,30}\banalyst\b|\breconciliation analyst\b"),
    ("Reporting Analyst", r"\breporting analyst\b|\bmis analyst\b"),
    ("Product Analyst", r"\bproduct analyst\b"),
    ("Operations Analyst", r"\boperations analyst\b|\boperational analyst\b|\bprocurement\b.{0,40}\banalyst\b|\bsupply chain\b.{0,40}\banalyst\b|\bmanufacturing analyst\b|\basset management analyst\b"),
    ("Data Scientist/Analyst-adjacent", r"\bdata scientist\b"),
    ("Research Analyst", r"\bresearch analyst\b|\bmarket analyst\b"),
    ("Commercial Analyst", r"\bcommercial analyst\b|\bpricing analyst\b|\brevenue analyst\b|\bcustomer success analyst\b"),
    ("Risk Analyst", r"\brisk analyst\b|\binvestment analyst\b|\bstrategy analyst\b|\bperformance analyst\b|\bcredit analyst\b|\bcompliance analyst\b|\bfinancial crime\b.{0,30}\banalyst\b|\bcyber security analyst\b|\bcybersecurity analyst\b"),
    ("HR Analyst", r"\bhr analyst\b|\bpeople analyst\b|\bhuman resources analyst\b"),
]

EXCLUDE_TITLE_RE = re.compile(
    r"\b("
    r"engineer|developer|architect|administrator|admin|support|technician|accountant|"
    r"teacher|trainer|professor|lecturer|recruiter|talent acquisition|sales executive|"
    r"business development|customer service|call center|secretary|assistant|coordinator|"
    r"designer|driver|nurse|doctor|lawyer|chef|waiter|storekeeper"
    r")\b",
    re.IGNORECASE,
)

ANALYTIC_CONTEXT_RE = re.compile(
    r"\b(analysis|analytics|dashboard|reporting|insight|forecast|sql|python|power bi|tableau|statistics|model(?:ing)?|data)\b",
    re.IGNORECASE,
)

TARGET_CITIES = {
    "Dubai",
    "Abu Dhabi",
    "Sharjah",
    "Riyadh",
    "Jeddah",
    "Dammam",
    "Khobar",
    "Doha",
    "Kuwait City",
    "Manama",
    "Muscat",
}
TARGET_COUNTRIES = {
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Kuwait",
    "Bahrain",
    "Oman",
    "AE",
    "SA",
    "QA",
    "KW",
    "BH",
    "OM",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create include/exclude review CSVs from normalized rows using title, metadata, and local raw snippets."
    )
    parser.add_argument("--sources", nargs="+", choices=sorted(SOURCE_FILES), default=sorted(SOURCE_FILES))
    return parser.parse_args()


def source_key_from_name(value: str) -> str:
    lowered = value.lower()
    if "careerjet" in lowered:
        return "careerjet"
    if "jooble" in lowered:
        return "jooble"
    return "jsearch"


def raw_record_id(source: str, record: dict[str, Any]) -> str:
    if source == "careerjet":
        return clean_text(record.get("jobkey") or record.get("id"))
    if source == "jooble":
        return clean_text(record.get("id"))
    return clean_text(record.get("job_id"))


def raw_record_text(source: str, record: dict[str, Any]) -> str:
    if source == "careerjet":
        return flatten_text(
            [
                record.get("title"),
                record.get("company"),
                record.get("locations") or record.get("location"),
                record.get("description"),
            ]
        )
    if source == "jooble":
        return flatten_text(
            [
                record.get("title"),
                record.get("company"),
                record.get("location"),
                record.get("snippet"),
                record.get("source"),
            ]
        )
    return flatten_text(
        [
            record.get("job_title"),
            record.get("employer_name"),
            record.get("job_location"),
            record.get("job_description"),
            record.get("job_highlights"),
        ]
    )


def build_raw_context_index() -> dict[tuple[str, str], str]:
    context: dict[tuple[str, str], str] = {}
    for path in RAW_SAMPLES_DIR.glob("*.json"):
        if path.name.startswith("jsearch_"):
            source = "jsearch"
        elif path.name.startswith("careerjet_"):
            source = "careerjet"
        elif path.name.startswith("jooble_"):
            source = "jooble"
        else:
            continue
        try:
            payload = read_json(path)
        except Exception:
            continue
        for record in extract_items(payload):
            record_id = raw_record_id(source, record)
            if record_id:
                context[(source, record_id)] = raw_record_text(source, record)
    return context


def yes_no(value: str) -> str:
    return "yes" if clean_text(value) else "no"


def infer_review_role(row: dict[str, str], context: str) -> tuple[str, str, str]:
    title = clean_text(row.get("job_title_raw"))
    title_text = title.lower()
    context_text = f"{title} {row.get('skills_extracted', '')} {context}".lower()

    for label, pattern in INCLUDE_PATTERNS:
        if re.search(pattern, title_text, re.IGNORECASE):
            if label == "Data Scientist/Analyst-adjacent":
                return (
                    label,
                    "include",
                    "Data scientist role included as analyst-adjacent because the batch intentionally samples data roles.",
                )
            return label, "include", f"Title directly matches {label.lower()} scope."

    if "analyst" in title_text:
        if EXCLUDE_TITLE_RE.search(title_text) and not ANALYTIC_CONTEXT_RE.search(context_text):
            return "", "exclude", "Title contains analyst wording but context points away from analysis work."
        return "Other Analyst", "include", "Title is analyst-scoped and no stronger exclusion signal is present."

    if EXCLUDE_TITLE_RE.search(title_text):
        return "", "exclude", "Role title is outside analyst scope."

    if "data scientist" in context_text:
        return (
            "Data Scientist/Analyst-adjacent",
            "include",
            "Data scientist context is close enough to the analyst-market expansion scope.",
        )

    return "", "exclude", "No clear analyst, BI, reporting, financial, product, operations, or data-science role signal."


def location_exclusion_note(row: dict[str, str], *, allow_cityless: bool = False) -> str:
    city = clean_text(row.get("city"))
    country = clean_text(row.get("country"))
    if city not in TARGET_CITIES and not (allow_cityless and not city):
        return f"Location is outside this batch's target cities: {city or 'unknown city'}."
    if country and country not in TARGET_COUNTRIES:
        return f"Location country is outside this batch's target countries: {country}."
    return ""


def base_review_row(row: dict[str, str], role: str, decision: str, note: str) -> dict[str, str]:
    source_key = source_key_from_name(row.get("source_name", ""))
    return {
        "api_name": SOURCE_FILES[source_key]["api_name"],
        "sample_id": clean_text(row.get("source_record_id")) or f"{source_key}_unkeyed",
        "query_used": clean_text(row.get("query_used")),
        "country_target": clean_text(row.get("country")),
        "city_target": clean_text(row.get("city")),
        "job_title_raw": clean_text(row.get("job_title_raw")),
        "job_title_relevant_yes_no": "yes" if decision == "include" else "no",
        "analyst_role_category": role,
        "company_present_yes_no": yes_no(row.get("company_name", "")),
        "country_present_yes_no": yes_no(row.get("country", "")),
        "city_present_yes_no": yes_no(row.get("city", "")),
        "salary_present_yes_no": yes_no(row.get("salary_range_if_listed", "") or row.get("salary_min", "") or row.get("salary_max", "")),
        "posting_date_present_yes_no": yes_no(row.get("posting_date", "")),
        "description_present_yes_no": "yes" if row.get("description_available_flag") == "yes" else "no",
        "description_full_or_snippet": "snippet_or_excerpt" if row.get("description_available_flag") == "yes" else "not_available",
        "skills_extractable_yes_no": yes_no(row.get("skills_extracted", "")),
        "employment_type_present_yes_no": yes_no(row.get("employment_type", "")),
        "work_arrangement_present_yes_no": yes_no(row.get("work_arrangement", "")),
        "source_domain": clean_text(row.get("source_url_domain_only")),
        "restricted_source_yes_no": "yes" if row.get("restricted_source_flag") == "yes" else "no",
        "duplicate_yes_no": "yes" if row.get("duplicate_group_id") else "no",
        "pii_or_recruiter_data_yes_no": "yes" if row.get("pii_or_recruiter_data_flag") == "yes" else "no",
        "notes": note,
        "reviewer_decision": decision,
    }


def duplicate_preference(item: dict[str, Any]) -> tuple[int, int, int, int]:
    row = item["row"]
    source_key = item["source_key"]
    restricted = 1 if row.get("restricted_source_flag") == "yes" else 0
    pii = 1 if row.get("pii_or_recruiter_data_flag") == "yes" else 0
    source_priority = SOURCE_FILES[source_key]["priority"]
    return restricted, pii, source_priority, item["index"]


def main() -> None:
    args = parse_args()
    context = build_raw_context_index()
    reviewed_by_source: dict[str, list[dict[str, str]]] = {source: [] for source in args.sources}
    candidate_items: list[dict[str, Any]] = []

    for source in args.sources:
        rows = read_csv_rows(SOURCE_FILES[source]["input"])
        for index, row in enumerate(rows):
            record_id = clean_text(row.get("source_record_id"))
            raw_context = context.get((source, record_id), "")
            role, decision, note = infer_review_role(row, raw_context)
            location_note = location_exclusion_note(row, allow_cityless=source == "jooble")
            if decision == "include" and location_note:
                role = ""
                decision = "exclude"
                note = location_note
            review = base_review_row(row, role, decision, note)
            reviewed_by_source[source].append(review)
            if decision == "include":
                candidate_items.append(
                    {
                        "source": source,
                        "source_key": source,
                        "index": index,
                        "row": row,
                        "review": review,
                        "dedupe_key": duplicate_key(row),
                    }
                )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidate_items:
        key = item["dedupe_key"]
        if key:
            groups[key].append(item)

    excluded_duplicates = 0
    for group_items in groups.values():
        if len(group_items) < 2:
            continue
        keeper = sorted(group_items, key=duplicate_preference)[0]
        for item in group_items:
            item["review"]["duplicate_yes_no"] = "yes"
            if item is keeper:
                item["review"]["notes"] = f"{item['review']['notes']} Kept as duplicate-group representative."
            else:
                item["review"]["reviewer_decision"] = "exclude"
                item["review"]["job_title_relevant_yes_no"] = "no"
                item["review"]["notes"] = "Duplicate of another included posting; excluded from aggregate counts."
                excluded_duplicates += 1

    for source, reviews in reviewed_by_source.items():
        output = SOURCE_FILES[source]["output"]
        write_csv(output, reviews, REVIEW_FIELDS)
        included = sum(1 for row in reviews if row["reviewer_decision"] == "include")
        excluded = sum(1 for row in reviews if row["reviewer_decision"] == "exclude")
        print(f"{source}: wrote {len(reviews)} reviews to {output} ({included} include, {excluded} exclude)")
    print(f"Excluded duplicate rows after choosing representatives: {excluded_duplicates}")


if __name__ == "__main__":
    main()
