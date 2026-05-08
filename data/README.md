# Data Directory

This directory is intentionally local-first.

## Folders

- `raw_samples/`: local-only raw API samples. Do not commit payloads.
- `normalized/`: local-only normalized metadata CSVs generated from raw samples.
- `derived_only/`: local-only aggregate outputs and summaries.

Only `.gitkeep` files are tracked in data subfolders.

## Rule

Raw descriptions, full postings, full application URLs, and recruiter/contact data must not be committed.
