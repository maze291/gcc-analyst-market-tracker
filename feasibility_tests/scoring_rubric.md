# Scoring Rubric

Score each API out of 100 after it passes the compliance gate.

## Compliance Gate

An API cannot be a production source unless terms or written permission clearly allow:

- aggregate public statistics
- derived-field storage
- short-term caching
- non-commercial public dashboard or reporting use

If this is unclear, cap the decision at `feasibility_only` or `validation_only`, regardless of weighted score.

## Weighted Score

| Category | Weight | What to measure |
| --- | ---: | --- |
| UAE/Saudi coverage | 25 | Can it return at least 50 relevant UAE/Saudi analyst postings during testing? |
| Role relevance | 15 | Percent of results that are actually analyst-related. |
| Field completeness | 15 | Title, company, city, country, date, employment type, salary, source domain. |
| Description usefulness | 10 | Description/snippet quality for temporary skill extraction. |
| Compliance fit | 20 | Terms or permission allow aggregate-only analytics and minimized storage. |
| Restricted-source risk | 10 | Percent of listings sourced from LinkedIn, Indeed, Glassdoor, Bayt, Naukrigulf, GulfTalent, or other high-risk sources. |
| Operational fit | 5 | Free tier, rate limits, reliability, easy setup. |

## Decision Thresholds

| Score | Decision |
| ---: | --- |
| 80-100 | Good enough for v1 primary or strong secondary source, if compliance gate passes. |
| 65-79 | Usable as secondary validation source, if compliance gate passes. |
| 50-64 | Use only for limited aggregate checks. |
| Below 50 | Avoid for v1. |

## Automatic Fail Conditions

An API fails as a production source if any are true:

- It cannot return meaningful UAE or Saudi results.
- Terms do not clearly permit aggregate public statistics, derived-field storage, short-term caching, and non-commercial reporting.
- Terms clearly prohibit aggregate vacancy counts or ongoing research use.
- It requires storing or displaying full postings publicly.
- It frequently returns recruiter personal data that is hard to remove.
- It mostly returns restricted-platform links and provides no safer intermediary/metadata approach.
- It does not provide enough useful fields for monthly aggregate statistics.
