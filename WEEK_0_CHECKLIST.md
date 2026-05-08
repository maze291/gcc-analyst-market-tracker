# Week 0 Checklist

## Day 1 - Compliance Setup

- [ ] Confirm repository is initialized and `.gitignore` blocks local secrets and raw samples.
- [ ] Review `compliance/api_terms_register.md`.
- [ ] Review source rules for JSearch/OpenWeb Ninja, Careerjet, Jooble, and Adzuna.
- [ ] Confirm restricted-source domains in `compliance/restricted_sources.md`.
- [ ] Confirm data retention, public display, and PII exclusion policies.
- [ ] Prepare written-permission questions in `compliance/provider_permission_questions.md`.

## Day 2 - API Access And Smoke Tests

- [ ] Create API accounts for JSearch/OpenWeb Ninja, Careerjet, and Jooble.
- [ ] Store keys locally in `.env`; do not commit `.env`.
- [ ] Run tiny dry-run checks for the three active APIs.
- [ ] Confirm Careerjet UAE and Saudi locale handling with `en_AE` and `en_SA`.
- [ ] Confirm Careerjet request includes `user_ip`, `user_agent`, and `Referer`.

## Day 3 - Small Sample Pulls

Start with the first-pass query set in `feasibility_tests/sample_queries.md`.

- [ ] Pull local-only samples for JSearch.
- [ ] Pull local-only samples for Careerjet.
- [ ] Pull local-only samples for Jooble.
- [ ] Normalize each sample into aggregate-safe CSV fields.
- [ ] Extract skills from temporary text and discard full descriptions.
- [ ] Flag restricted-source domains.
- [ ] Deduplicate across APIs without using `source_name` in the duplicate key.

## Day 4 - Manual Review

- [ ] Review 50-100 postings per active API where coverage allows.
- [ ] Record one row per posting using `feasibility_tests/manual_review_template.csv`.
- [ ] Check analyst title relevance, country/city quality, company presence, salary/date coverage, description usefulness, restricted-source risk, duplicate risk, and PII/contact-data risk.

## Day 5 - Score And Decide

- [ ] Apply compliance gate before weighted score.
- [ ] Complete `feasibility_tests/results/decision_matrix.csv`.
- [ ] Write `DECISION_LOG.md`.
- [ ] Choose one outcome:
  - JSearch passes data quality and written terms comfort: production candidate.
  - JSearch passes data quality but terms remain unclear: feasibility/testing only.
  - Careerjet passes enough quality and terms are clearer: possible primary or secondary candidate.
  - Jooble passes enough quality: validation only unless terms are clarified.
  - No API passes: pivot to open-data/manual aggregate research.
