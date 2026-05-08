# Decision Log

Review date: 2026-05-08

## Executive Decision

Status: Pending Week 0 review

Selected primary API: TBD

Selected fallback API: TBD

APIs delayed or rejected: TBD

## Compliance Gate

Production source selection is blocked unless terms or written permission clearly allow:

- aggregate public statistics
- derived-field storage
- short-term caching
- non-commercial public dashboard or reporting use

## Candidate Outcomes

| API | Data quality outcome | Terms outcome | Decision |
| --- | --- | --- | --- |
| JSearch / OpenWeb Ninja | TBD | Written permission required before production | Feasibility testing only until clarified |
| Careerjet | TBD | Publisher API, production analytics still requires clarification | Feasibility testing and possible candidate |
| Jooble | TBD | Display-oriented API, storage/analytics unclear | Validation only until clarified |
| Adzuna | Not active for v1 | Ongoing aggregation requires written consent | Avoid unless permission granted |

## Week 0 Work Completed So Far

### JSearch / OpenWeb Ninja — RapidAPI Setup

Completed:
- Created RapidAPI access for JSearch.
- Added API key locally in `.env`.
- Confirmed dry run does not expose the real API key.
- Confirmed script uses:
  - endpoint: `https://jsearch.p.rapidapi.com/search`
  - header: `X-RapidAPI-Key`
  - header: `X-RapidAPI-Host: jsearch.p.rapidapi.com`
- Successfully ran a real tiny sample query:
  - `Data Analyst Dubai`

Status:
- API authentication: PASS
- Fetch script: PASS
- Raw local sample write: PASS

## JSearch Initial Feasibility Results — 2026-05-08

Input:
- 8 test queries
- 10 results per query
- 80 normalized records total

Queries tested:
- Data Analyst Dubai
- Business Analyst Dubai
- BI Analyst Dubai
- Financial Analyst Dubai
- Data Analyst Riyadh
- Business Analyst Riyadh
- BI Analyst Riyadh
- Financial Analyst Riyadh

Coverage:
- AE, Dubai: 39 records
- SA, Riyadh: 39 records
- Missing country/city: 2 records

Restricted-source analysis:
- Restricted-source records: 27 / 80 = 33.75%
- Non-restricted-source records: 53 / 80 = 66.25%

Top observed source domains:
- bebee.com: 12
- ae.indeed.com: 11
- gulftalent.com: 8
- sa.jooble.org: 7
- careerwebsite.com: 4
- naukrigulf.com: 3
- sa.linkedin.com: 2
- glassdoor.com: 2

Salary coverage:
- Salary fields present: 0 / 80 = 0%
- Decision: salary bands/ranges should not be a v1 dashboard promise.
- Allowed v1 metric: salary transparency / salary coverage rate.

Description availability:
- Description available flag: 80 / 80 = 100%
- Decision: descriptions are usable for temporary skill extraction.
- Production rule: do not retain full descriptions; store only derived skills and description availability flag.

Initial interpretation:
- Technical feasibility: PASS for UAE/Dubai and Saudi/Riyadh sample coverage.
- Skill extraction feasibility: PASS.
- Salary analysis feasibility: FAIL for v1 salary-band analysis.
- Compliance posture: CONDITIONAL because 33.75% of records point to restricted/high-risk domains.
- Public output rule: aggregate statistics only; no listing-level display.

## JSearch Duplicate Check — 2026-05-08

Input file:
- `data/normalized/jsearch_normalized_all.csv`

Output file:
- `data/normalized/jsearch_deduped.csv`

Results:
- Raw normalized rows: 80
- Duplicate groups detected: 2
- Duplicate-flagged rows: 4 / 80 = 5.0%
- Estimated unique postings after deduplication: 78

Duplicate examples:

1. `Senior Finance Analyst, MedTech/Vision`
   - Company: Johnson & Johnson Services, Inc.
   - Location: Riyadh, Saudi Arabia
   - Source domain: careers.jnj.com
   - Appeared under:
     - Financial Analyst Riyadh
     - Business Analyst Riyadh

2. `Master Data Management Business Analyst`
   - Company: Eram Talent
   - Location: Riyadh, Saudi Arabia
   - Source domain: gulftalent.com
   - Appeared under:
     - Business Analyst Riyadh
     - Data Analyst Riyadh

Interpretation:
- Duplication is present but manageable in the initial JSearch sample.
- Most observed duplication comes from the same posting matching multiple analyst-query categories.
- Dashboard metrics should use deduplicated posting counts, not raw API result counts.
- Cross-query and cross-source deduplication should remain part of the v1 pipeline.

Decision:
- JSearch remains technically promising for aggregate analytics.
- JSearch is not yet approved as a production public-dashboard source until provider terms or written permission clarify aggregate public reporting and derived-field storage.

## JSearch Manual Relevance Review — 2026-05-08

Input file:
- `feasibility_tests/results/jsearch_review.csv`

Reviewed records:
- Total reviewed: 80
- Keep: 67 / 80 = 83.8%
- Borderline: 13 / 80 = 16.3%
- Exclude: 0 / 80 = 0.0%
- Useful rate, counting keep + borderline: 80 / 80 = 100.0%

Role breakdown:
- Financial Analyst: 23
- Business Analyst: 20
- BI Analyst: 16
- Data Analyst: 15
- Data Engineer: 3
- Data Scientist / Analyst-adjacent: 2
- Product Analyst: 1

Interpretation:
- Role relevance score: 15 / 15
- JSearch returned highly relevant analyst-market results for the initial UAE/Saudi test set.
- The sample is skewed toward Financial Analyst and Business Analyst roles, but still includes enough BI/Data Analyst results for v1 feasibility.
- JSearch appears technically strong for UAE/Saudi analyst-market tracking.

Decision:
- JSearch total feasibility score: 80 / 100.
- JSearch qualifies as a strong Week 0 feasibility source.
- JSearch is not production-approved yet because provider terms/written permission must still clarify aggregate public reporting, short-term caching, and derived-field storage.
- Continue testing Careerjet next before selecting a production candidate.

## JSearch PII/Contact Flag Review — 2026-05-08

Current result:
- `pii_or_recruiter_data_flag = yes`: 30 / 80 records
- `pii_or_recruiter_data_flag = no`: 50 / 80 records

Investigation:
- The flag is generated from temporary raw JSearch fields, not retained public-safe fields.
- JSearch PII/contact detection checks temporary fields such as job description, job highlights, apply options, and employer LinkedIn fields.
- The flag is triggered by email-like, phone-like, or LinkedIn-style patterns.
- Codex confirmed the normalized CSV does not retain dedicated fields for recruiter names, emails, phone numbers, LinkedIn profiles, hiring manager names, full descriptions, or full application URLs.
- Codex also checked the normalized CSV for retained patterns and found no email patterns, no LinkedIn profile patterns, and only date-related false positives for phone-like patterns.

Interpretation:
- The correct metric is “possible PII/contact pattern in raw input,” not “PII retained in normalized output.”
- 30 / 80 raw records may contain contact-like or LinkedIn-style patterns in temporary raw input.
- Retained PII/contact fields in normalized output: 0.
- Production ingestion must keep raw data local-only/temporary, extract derived skills, and avoid retaining raw descriptions or full application URLs.

Decision:
- Keep the 30 `yes` flags as evidence of raw-input risk.
- Do not overwrite them.
- Summary wording was updated to distinguish raw-input risk from retained PII.


## MVP Data Fields

- country
- city
- role category
- seniority
- company presence flag
- salary min/max/currency/period where listed
- employment type
- work arrangement
- posting date or age
- source domain only
- restricted-source flag
- duplicate group id
- aggregate skill counts

## Public Display Limits

Allowed: aggregate statistics and charts only.

Blocked: full postings, full descriptions, recruiter contact data, full application links, restricted-platform links, searchable job databases, and raw API exports.

## Unresolved Questions

- Which provider grants written permission for aggregate public statistics?
- Which provider grants written permission for derived-field storage and short-term caching?
- Which country has stronger tested coverage for Week 1 MVP launch?
- Is a separate commercial or publisher agreement required before public launch?
