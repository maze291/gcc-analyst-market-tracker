# V1 Private Dashboard

This is the local/private v1 dashboard surface for the GCC Analyst Market Tracker.

It reads aggregate-only data from:

```text
data/derived_only/dashboard/dashboard_data.json
```

Generate that file first:

```powershell
python scripts\build_dashboard_aggregates.py
```

Then serve the repo root locally:

```powershell
python -m http.server 8080
```

Open:

```text
http://localhost:8080/v1_dashboard/
```

## Public Release Rule

This dashboard is a private prototype until provider permission is clarified. It must not be deployed publicly with live aggregate data before the compliance gate is resolved.
