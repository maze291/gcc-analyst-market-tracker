# JSearch / OpenWeb Ninja Source Rule

## Week 0 Role

Primary feasibility-test source.

## Production Status

Feasibility testing only until written permission confirms aggregate public statistics, derived-field storage, short-term caching, and public reporting are allowed.

## Use Constraints

- Do not display raw listings publicly.
- Do not display full descriptions.
- Do not store full application links.
- Do not store employer LinkedIn profile links.
- Extract skills temporarily, then discard source text.
- Flag publishers and apply domains that match restricted sources.
- Confirm the exact endpoint, RapidAPI host, and auth header from the provider account dashboard before live testing; the local fetcher supports `--api-url`, `--rapidapi-host`, and `--auth-header` overrides.

## Known Risk

The API is relevant for job-market analytics, but OpenWeb Ninja terms restrict systematic retrieval, aggregation, database creation, copying, and public display without written permission.
