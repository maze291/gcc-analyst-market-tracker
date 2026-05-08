# Compliance README

This folder records feasibility controls for API-only labor-market research. It is not legal advice.

## Production Gate

No API becomes a production source until its terms or written permission clearly allow:

- aggregate public statistics
- derived-field storage
- short-term caching
- non-commercial public dashboard or reporting use

If terms are unclear, the provider remains limited to feasibility testing.

## Storage Controls

- Keep raw samples local only.
- Do not commit raw full postings, full descriptions, application URLs, or recruiter contact data.
- Store normalized metadata and derived aggregate fields only.
- Drop recruiter names, emails, phone numbers, LinkedIn profiles, hiring manager names, and application-form data.

## Public Display Controls

Public MVP outputs must be aggregate statistics only. Do not publish raw listings, descriptions, direct application links, or restricted-source links.
