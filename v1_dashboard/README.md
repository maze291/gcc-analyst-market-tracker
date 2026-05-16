# V1 Private Dashboard

This is the local/private v1 dashboard surface for the GCC Analyst Market Tracker.

It reads aggregate-only data from:

```text
data/derived_only/dashboard/dashboard_data.json
```

The V2 preview section also reads local history CSVs from:

```text
data/derived_only/history/
```

Generate that file first:

```powershell
python scripts\build_dashboard_aggregates.py
python scripts\build_unique_jobs.py
python scripts\write_trend_snapshot.py
```

Then serve the repo root locally:

```powershell
python -m http.server 8080
```

Open:

```text
http://localhost:8080/v1_dashboard/
```

## Release Note

This dashboard is a private prototype that uses API-sourced aggregate data. Do not deploy it with raw job-level data, full job listings, descriptions, recruiter contact details, or application links.
