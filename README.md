# GCC Analyst Market Tracker Feasibility

Week 0 feasibility sprint workspace for testing whether API-only job-market data can support an aggregate analyst labor-market dashboard for the United Arab Emirates and Saudi Arabia.

This repository is for research and risk planning only. It is not legal advice.

## Operating Principle

Compliance gates production use before data quality scoring. An API can score well on coverage and field richness and still remain limited to feasibility testing if its terms do not clearly allow:

- aggregate public statistics
- derived-field storage
- short-term caching
- non-commercial public dashboard or reporting use

## Week 0 Path

1. Scaffold compliance docs, data policies, source rules, sample queries, and review templates.
2. Test API authentication locally for JSearch/OpenWeb Ninja, Careerjet, and Jooble.
3. Pull small raw samples locally only, then normalize into aggregate-safe fields.
4. Manually review 50-100 postings per active API.
5. Score each API and write a decision log.

Adzuna is documentation-only for v1 unless written permission and UAE/Saudi coverage are confirmed.

## Data Handling Rules

Do not commit API keys, raw job descriptions, recruiter contact info, application links, or raw full postings.

Allowed persisted fields are aggregate-safe normalized metadata and derived fields. Full descriptions may be used temporarily for local skill extraction, then must be discarded.

## Quick Start

```powershell
Copy-Item .env.example .env
```

Fill in local API keys in `.env`; never commit that file.

For RapidAPI JSearch, use the regenerated RapidAPI key as `JSEARCH_API_KEY` and keep `JSEARCH_RAPIDAPI_HOST=jsearch.p.rapidapi.com`, unless the RapidAPI endpoint page shows a different host.

For Careerjet, set `CAREERJET_API_KEY` and `CAREERJET_USER_IP` to the public IP address declared in Careerjet's API settings. Do not use `127.0.0.1`.
If Careerjet shows a different endpoint in your account, set `CAREERJET_API_URL` or pass `--api-url`.

Run a tiny smoke test after accounts are created:

```powershell
python scripts\fetch_careerjet.py --query "Data Analyst" --location "Dubai" --country AE --limit 5 --dry-run
python scripts\fetch_jooble.py --query "Data Analyst" --location "Dubai" --limit 5 --dry-run
python scripts\fetch_jsearch.py --provider rapidapi --query "Data Analyst Dubai" --limit 5 --dry-run
```

If your JSearch/OpenWeb Ninja account dashboard provides a different endpoint, host, or auth header, pass `--api-url`, `--rapidapi-host`, or `--auth-header` to `scripts\fetch_jsearch.py`. The default is intentionally overrideable because provider account docs can vary.

Remove `--dry-run` only when you are ready to create local raw sample files under `data/raw_samples/`.

Normalize a raw sample:

```powershell
python scripts\normalize_jobs.py --source jsearch --input data\raw_samples\jsearch_sample.json --output data\normalized\jsearch_normalized.csv
```

Add duplicate groups across active APIs:

```powershell
python scripts\detect_duplicates.py --input data\normalized\combined.csv --output data\normalized\combined_deduped.csv
```

## Important Files

- `WEEK_0_CHECKLIST.md`: day-by-day sprint tasks
- `DECISION_LOG.md`: final decision template
- `compliance/api_terms_register.md`: source terms and risk register
- `compliance/provider_permission_questions.md`: questions to send providers before production use
- `feasibility_tests/scoring_rubric.md`: scoring and automatic fail rules
- `dashboard_mvp_spec/allowed_public_outputs.md`: public dashboard limits

## Public Project Page

The GitHub Pages-ready project site lives in `docs/`.

Recommended setup:

1. Push this repository to GitHub.
2. In repository settings, enable GitHub Pages.
3. Set the source to the `docs/` folder on the main branch.
4. Use the resulting GitHub Pages URL for early provider registration.
5. Add a custom domain later before serious public launch.
