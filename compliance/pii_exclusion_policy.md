# PII Exclusion Policy

## Drop Before Storage

- recruiter names
- recruiter emails
- phone numbers
- LinkedIn profile URLs
- hiring manager names
- application-form data
- candidate/applicant data

## Detection

Scripts flag obvious emails, phone numbers, and LinkedIn URLs. Manual review must also check for recruiter personal data in titles, snippets, descriptions, apply options, and metadata.

## Review Rule

If a provider frequently returns recruiter personal data that is hard to remove, it automatically fails as a v1 production source.
