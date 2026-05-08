from __future__ import annotations

import csv
import datetime as dt
import email.utils
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RAW_SAMPLES_DIR = DATA_DIR / "raw_samples"
NORMALIZED_DIR = DATA_DIR / "normalized"
DERIVED_ONLY_DIR = DATA_DIR / "derived_only"

RESTRICTED_DOMAINS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "bayt.com",
    "naukrigulf.com",
    "gulftalent.com",
)

NORMALIZED_FIELDS = [
    "source_name",
    "source_url_domain_only",
    "date_seen",
    "job_title_raw",
    "job_title_normalized",
    "company_name",
    "country",
    "city",
    "seniority",
    "function",
    "skills_extracted",
    "salary_range_if_listed",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "employment_type",
    "work_arrangement",
    "industry",
    "posting_age",
    "posting_date",
    "description_available_flag",
    "restricted_source_flag",
    "duplicate_group_id",
    "pii_or_recruiter_data_flag",
    "source_record_id",
    "query_used",
]

SKILL_PATTERNS = {
    "SQL": r"\bsql\b",
    "Excel": r"\bexcel\b|\badvanced excel\b",
    "Power BI": r"\bpower\s*bi\b",
    "Tableau": r"\btableau\b",
    "Python": r"\bpython\b",
    "R Programming": r"\br programming\b|\brstudio\b",
    "SAS": r"\bsas\b",
    "SPSS": r"\bspss\b",
    "Looker": r"\blooker\b",
    "Qlik": r"\bqlik\b|\bqlikview\b|\bqlik sense\b",
    "Power Query": r"\bpower query\b",
    "DAX": r"\bdax\b",
    "ETL": r"\betl\b",
    "Snowflake": r"\bsnowflake\b",
    "Databricks": r"\bdatabricks\b",
    "AWS": r"\baws\b|amazon web services",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "BigQuery": r"\bbigquery\b|big query",
    "Redshift": r"\bredshift\b",
    "Alteryx": r"\balteryx\b",
    "SAP": r"\bsap\b",
    "Salesforce": r"\bsalesforce\b",
    "CRM": r"\bcrm\b",
    "Jira": r"\bjira\b",
    "Agile": r"\bagile\b|scrum",
    "Statistics": r"\bstatistics\b|\bstatistical\b",
    "Machine Learning": r"\bmachine learning\b|\bml\b",
    "Forecasting": r"\bforecasting\b|\bforecast\b",
    "Financial Modeling": r"\bfinancial model(?:ing)?\b",
    "Data Visualization": r"\bdata visualization\b|\bvisualisation\b|\bdashboard(?:s)?\b",
    "Data Warehousing": r"\bdata warehouse\b|\bdata warehousing\b",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
LINKEDIN_RE = re.compile(r"linkedin\.com/(?:in|pub|company)/", re.IGNORECASE)


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def today_iso() -> str:
    return dt.date.today().isoformat()


def ensure_data_dirs() -> None:
    for directory in (RAW_SAMPLES_DIR, NORMALIZED_DIR, DERIVED_ONLY_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "sample"


def sample_path(source_name: str, query: str, extension: str = "json") -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return RAW_SAMPLES_DIR / f"{source_name}_{slugify(query)}_{timestamp}.{extension}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    request_url = url
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        request_url = f"{url}?{query}"

    body = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        request_url,
        data=body,
        headers=request_headers,
        method=method.upper(),
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    return json.loads(text)


def domain_from_url(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"https://{text}"
    parsed = urllib.parse.urlparse(text)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def is_restricted_domain(domain: str) -> bool:
    cleaned = domain_from_url(domain) or str(domain).lower()
    return any(cleaned == blocked or cleaned.endswith(f".{blocked}") for blocked in RESTRICTED_DOMAINS)


def restricted_source_flag(*values: Any) -> bool:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            if restricted_source_flag(*value):
                return True
            continue
        text = str(value).lower()
        domain = domain_from_url(text)
        if domain and is_restricted_domain(domain):
            return True
        if any(blocked in text for blocked in RESTRICTED_DOMAINS):
            return True
    return False


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def has_pii_or_recruiter_data(*values: Any) -> bool:
    text = flatten_text(values)
    return bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or LINKEDIN_RE.search(text))


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_title(title: Any) -> str:
    text = clean_text(title).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title()


def role_category(title: Any) -> str:
    text = clean_text(title).lower()
    rules = [
        ("Data Analyst", r"\bdata analyst\b"),
        ("Business Analyst", r"\bbusiness analyst\b"),
        ("BI Analyst", r"\bbi analyst\b|\bbusiness intelligence analyst\b"),
        ("Product Analyst", r"\bproduct analyst\b"),
        ("Financial Analyst", r"\bfinancial analyst\b|\bfinance analyst\b"),
        ("Operations Analyst", r"\boperations analyst\b|\boperational analyst\b"),
        ("Reporting Analyst", r"\breporting analyst\b"),
        ("Analyst-adjacent Data Scientist", r"\bdata scientist\b"),
    ]
    for label, pattern in rules:
        if re.search(pattern, text):
            return label
    if "analyst" in text:
        return "Other Analyst"
    return ""


def seniority(title: Any) -> str:
    text = clean_text(title).lower()
    if re.search(r"\bintern(ship)?\b|graduate|trainee", text):
        return "Intern/Graduate"
    if re.search(r"\bjunior\b|\bentry\b|associate", text):
        return "Junior"
    if re.search(r"\bsenior\b|\bsr\.?\b", text):
        return "Senior"
    if re.search(r"\blead\b|principal|staff", text):
        return "Lead/Principal"
    if re.search(r"\bmanager\b|head of|director", text):
        return "Manager+"
    return ""


def infer_country(*values: Any) -> str:
    text = flatten_text(values).lower()
    if any(token in text for token in ("united arab emirates", "uae", "dubai", "abu dhabi", "sharjah")):
        return "United Arab Emirates"
    if any(token in text for token in ("saudi arabia", "riyadh", "jeddah", "dammam", "ksa")):
        return "Saudi Arabia"
    return ""


def infer_city(*values: Any) -> str:
    text = flatten_text(values).lower()
    for city in ("Dubai", "Abu Dhabi", "Riyadh", "Jeddah", "Dammam", "Sharjah"):
        if city.lower() in text:
            return city
    return ""


def normalize_employment_type(*values: Any) -> str:
    text = flatten_text(values).lower()
    if "full" in text and "time" in text:
        return "Full-time"
    if "part" in text and "time" in text:
        return "Part-time"
    if "contract" in text:
        return "Contract"
    if "temporary" in text or "temp" in text:
        return "Temporary"
    if "intern" in text:
        return "Internship"
    return ""


def normalize_work_arrangement(*values: Any) -> str:
    text = flatten_text(values).lower()
    if "hybrid" in text:
        return "Hybrid"
    if "remote" in text or "work from home" in text or "wfh" in text:
        return "Remote"
    if "onsite" in text or "on-site" in text or "office" in text:
        return "Onsite"
    return ""


def extract_skills(text: Any) -> list[str]:
    haystack = flatten_text(text)
    found: list[str] = []
    for label, pattern in SKILL_PATTERNS.items():
        if re.search(pattern, haystack, re.IGNORECASE):
            found.append(label)
    return found


def parse_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        try:
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date().isoformat()
        except (ValueError, OSError, OverflowError):
            return ""
    text = clean_text(value)
    if not text:
        return ""
    normalized = text.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        return parsed.date().isoformat()
    except (TypeError, ValueError):
        return ""


def posting_age_days(posting_date: str) -> str:
    if not posting_date:
        return ""
    try:
        posted = dt.date.fromisoformat(posting_date)
    except ValueError:
        return ""
    return str((dt.date.today() - posted).days)


def posting_date_bucket(posting_date: str) -> str:
    if not posting_date:
        return ""
    try:
        posted = dt.date.fromisoformat(posting_date)
    except ValueError:
        return ""
    return posted.strftime("%Y-%m")


def salary_range(minimum: Any, maximum: Any, currency: Any = "", period: Any = "") -> str:
    min_text = clean_text(minimum)
    max_text = clean_text(maximum)
    if not min_text and not max_text:
        return ""
    if min_text and max_text:
        base = f"{min_text}-{max_text}"
    else:
        base = min_text or max_text
    extras = " ".join(part for part in (clean_text(currency), clean_text(period)) if part)
    return f"{base} {extras}".strip()


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "jobs", "results", "postings", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _jsearch_record(record: dict[str, Any], query_used: str) -> dict[str, str]:
    title = record.get("job_title")
    description = record.get("job_description")
    publisher = record.get("job_publisher")
    apply_link = record.get("job_apply_link") or record.get("job_google_link")
    apply_options = record.get("apply_options") or record.get("job_apply_options") or []
    domain = domain_from_url(apply_link) or domain_from_url(publisher)
    posting_date = parse_date(
        record.get("job_posted_at_datetime_utc")
        or record.get("job_posted_at_timestamp")
        or record.get("job_posted_at")
    )
    salary_min = record.get("job_min_salary") or record.get("job_salary_min")
    salary_max = record.get("job_max_salary") or record.get("job_salary_max")
    currency = record.get("job_salary_currency")
    period = record.get("job_salary_period")
    # PII/contact risk is checked against temporary raw fields before they are discarded.
    text_for_flags = [description, record.get("job_highlights"), apply_options, record.get("employer_linkedin")]
    country = record.get("job_country") or infer_country(record.get("job_location"), title)
    city = record.get("job_city") or infer_city(record.get("job_location"), title)
    return {
        "source_name": "JSearch / OpenWeb Ninja",
        "source_url_domain_only": domain,
        "date_seen": today_iso(),
        "job_title_raw": clean_text(title),
        "job_title_normalized": normalize_title(title),
        "company_name": clean_text(record.get("employer_name")),
        "country": clean_text(country),
        "city": clean_text(city),
        "seniority": seniority(title),
        "function": role_category(title),
        "skills_extracted": "; ".join(extract_skills([description, record.get("job_highlights")])),
        "salary_range_if_listed": salary_range(salary_min, salary_max, currency, period),
        "salary_min": clean_text(salary_min),
        "salary_max": clean_text(salary_max),
        "salary_currency": clean_text(currency),
        "salary_period": clean_text(period),
        "employment_type": normalize_employment_type(record.get("job_employment_type"), description),
        "work_arrangement": "Remote" if record.get("job_is_remote") else normalize_work_arrangement(description),
        "industry": clean_text(record.get("employer_company_type") or record.get("job_naics_name")),
        "posting_age": posting_age_days(posting_date),
        "posting_date": posting_date,
        "description_available_flag": "yes" if clean_text(description) else "no",
        "restricted_source_flag": "yes" if restricted_source_flag(domain, publisher, apply_options) else "no",
        "duplicate_group_id": "",
        "pii_or_recruiter_data_flag": "yes" if has_pii_or_recruiter_data(text_for_flags) else "no",
        "source_record_id": clean_text(record.get("job_id")),
        "query_used": query_used,
    }


def _careerjet_record(record: dict[str, Any], query_used: str) -> dict[str, str]:
    title = record.get("title")
    description = record.get("description")
    location = record.get("locations") or record.get("location")
    domain = domain_from_url(record.get("site") or record.get("url"))
    posting_date = parse_date(record.get("date"))
    salary = record.get("salary")
    return {
        "source_name": "Careerjet",
        "source_url_domain_only": domain,
        "date_seen": today_iso(),
        "job_title_raw": clean_text(title),
        "job_title_normalized": normalize_title(title),
        "company_name": clean_text(record.get("company")),
        "country": infer_country(location, title, query_used),
        "city": infer_city(location, title, query_used),
        "seniority": seniority(title),
        "function": role_category(title),
        "skills_extracted": "; ".join(extract_skills(description)),
        "salary_range_if_listed": clean_text(salary),
        "salary_min": clean_text(record.get("salary_min")),
        "salary_max": clean_text(record.get("salary_max")),
        "salary_currency": clean_text(record.get("salary_currency_code") or record.get("salary_currency")),
        "salary_period": clean_text(record.get("salary_type")),
        "employment_type": normalize_employment_type(description),
        "work_arrangement": normalize_work_arrangement(description),
        "industry": "",
        "posting_age": posting_age_days(posting_date),
        "posting_date": posting_date,
        "description_available_flag": "yes" if clean_text(description) else "no",
        "restricted_source_flag": "yes" if restricted_source_flag(domain, record.get("site"), record.get("url")) else "no",
        "duplicate_group_id": "",
        "pii_or_recruiter_data_flag": "yes" if has_pii_or_recruiter_data(description, record.get("url")) else "no",
        "source_record_id": clean_text(record.get("jobkey") or record.get("id")),
        "query_used": query_used,
    }


def _jooble_record(record: dict[str, Any], query_used: str) -> dict[str, str]:
    title = record.get("title")
    description = record.get("snippet") or record.get("description")
    location = record.get("location")
    source = record.get("source")
    domain = domain_from_url(source) or domain_from_url(record.get("link"))
    posting_date = parse_date(record.get("updated") or record.get("date"))
    salary = record.get("salary")
    return {
        "source_name": "Jooble",
        "source_url_domain_only": domain,
        "date_seen": today_iso(),
        "job_title_raw": clean_text(title),
        "job_title_normalized": normalize_title(title),
        "company_name": clean_text(record.get("company")),
        "country": infer_country(location, title, query_used),
        "city": infer_city(location, title, query_used),
        "seniority": seniority(title),
        "function": role_category(title),
        "skills_extracted": "; ".join(extract_skills(description)),
        "salary_range_if_listed": clean_text(salary),
        "salary_min": "",
        "salary_max": "",
        "salary_currency": "",
        "salary_period": "",
        "employment_type": normalize_employment_type(record.get("type"), description),
        "work_arrangement": normalize_work_arrangement(description),
        "industry": "",
        "posting_age": posting_age_days(posting_date),
        "posting_date": posting_date,
        "description_available_flag": "yes" if clean_text(description) else "no",
        "restricted_source_flag": "yes" if restricted_source_flag(domain, source, record.get("link")) else "no",
        "duplicate_group_id": "",
        "pii_or_recruiter_data_flag": "yes" if has_pii_or_recruiter_data(description, record.get("link")) else "no",
        "source_record_id": clean_text(record.get("id")),
        "query_used": query_used,
    }


def _adzuna_record(record: dict[str, Any], query_used: str) -> dict[str, str]:
    title = record.get("title")
    description = record.get("description")
    location = record.get("location") or {}
    area = location.get("area") if isinstance(location, dict) else location
    domain = domain_from_url(record.get("redirect_url"))
    posting_date = parse_date(record.get("created"))
    salary_min = record.get("salary_min")
    salary_max = record.get("salary_max")
    return {
        "source_name": "Adzuna",
        "source_url_domain_only": domain,
        "date_seen": today_iso(),
        "job_title_raw": clean_text(title),
        "job_title_normalized": normalize_title(title),
        "company_name": clean_text((record.get("company") or {}).get("display_name") if isinstance(record.get("company"), dict) else record.get("company")),
        "country": infer_country(area, title, query_used),
        "city": infer_city(area, title, query_used),
        "seniority": seniority(title),
        "function": role_category(title),
        "skills_extracted": "; ".join(extract_skills(description)),
        "salary_range_if_listed": salary_range(salary_min, salary_max),
        "salary_min": clean_text(salary_min),
        "salary_max": clean_text(salary_max),
        "salary_currency": "",
        "salary_period": "",
        "employment_type": normalize_employment_type(record.get("contract_type"), description),
        "work_arrangement": normalize_work_arrangement(description),
        "industry": clean_text((record.get("category") or {}).get("label") if isinstance(record.get("category"), dict) else record.get("category")),
        "posting_age": posting_age_days(posting_date),
        "posting_date": posting_date,
        "description_available_flag": "yes" if clean_text(description) else "no",
        "restricted_source_flag": "yes" if restricted_source_flag(domain, record.get("redirect_url")) else "no",
        "duplicate_group_id": "",
        "pii_or_recruiter_data_flag": "yes" if has_pii_or_recruiter_data(description, record.get("redirect_url")) else "no",
        "source_record_id": clean_text(record.get("id")),
        "query_used": query_used,
    }


def normalize_record(record: dict[str, Any], source: str, query_used: str = "") -> dict[str, str]:
    source_key = source.lower().replace("-", "_").replace(" ", "_")
    if source_key in {"jsearch", "openwebninja", "jsearch_openwebninja"}:
        row = _jsearch_record(record, query_used)
    elif source_key == "careerjet":
        row = _careerjet_record(record, query_used)
    elif source_key == "jooble":
        row = _jooble_record(record, query_used)
    elif source_key == "adzuna":
        row = _adzuna_record(record, query_used)
    else:
        raise ValueError(f"Unsupported source: {source}")
    return {field: clean_text(row.get(field, "")) for field in NORMALIZED_FIELDS}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fieldnames or NORMALIZED_FIELDS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def duplicate_key(row: dict[str, str]) -> str:
    parts = [
        normalize_title(row.get("job_title_normalized") or row.get("job_title_raw")),
        clean_text(row.get("company_name")).lower(),
        clean_text(row.get("city")).lower(),
        clean_text(row.get("country")).lower(),
        posting_date_bucket(row.get("posting_date", "")),
    ]
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest() if any(parts) else ""
