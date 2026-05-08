# API Terms Register

Review date: 2026-05-08

| Provider | Terms / docs URL | Current use in Week 0 | Production risk | Notes |
| --- | --- | --- | --- | --- |
| JSearch / OpenWeb Ninja | https://www.openwebninja.com/api/jsearch and https://www.openwebninja.com/terms | Primary feasibility-test source | High until written permission | Product copy supports analytics use, but terms restrict aggregation/database/public display without written permission. |
| Careerjet | https://www.careerjet.ae/partners/api and https://www.careerjet.com.sa/partners/api | Active feasibility-test source | Medium until clarified | Publisher API supports job result integration and UAE/Saudi locales; aggregate analytics/storage permission still needs provider confirmation. |
| Jooble | https://jooble.org/api/about and https://jooble.org/info/terms | Validation source | Medium-high until clarified | API supports displaying job results, but storage, copying, republication, and derived analytics require clarification. |
| Adzuna | https://developer.adzuna.com/docs/terms_of_service | Documentation-only | High | Terms explicitly restrict ongoing aggregation without written consent. Avoid v1 unless permission is granted. |

## Gate Status Definitions

- `production_candidate`: written terms comfort exists and data quality passes.
- `feasibility_only`: data can be tested locally, but public production use is not cleared.
- `validation_only`: useful for cross-checking counts/coverage, not a foundation for public reporting.
- `avoid`: terms, coverage, or operational risk make the source unsuitable for v1.
