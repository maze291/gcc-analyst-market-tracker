# Data Retention Policy

## Feasibility Samples

Raw API samples are local-only and temporary. They may be used during Week 0 to test parsing, field completeness, skill extraction, restricted-source detection, duplicate detection, and PII exclusion.

Raw samples must not be committed.

## Production Storage

Production storage is limited to normalized metadata and derived aggregate fields:

- source name
- source domain only
- date seen
- normalized job title
- company name where present
- country and city
- seniority
- function / analyst role category
- extracted skills as derived values
- salary range where listed
- employment type
- work arrangement
- industry where available
- posting date or posting age
- description availability flag
- restricted-source flag
- duplicate group id
- PII/contact-data flags

## Prohibited Storage

- full descriptions
- full raw postings
- full application URLs
- recruiter names
- recruiter emails
- phone numbers
- hiring manager names
- LinkedIn profile links
- application-form data
