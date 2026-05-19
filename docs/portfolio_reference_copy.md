# Smart Manufacturing AI Operations Platform - Portfolio Reference Copy

Use this as copy-ready portfolio content. The live Streamlit Community Cloud app
is deployed at `https://smart-manu-portfolio-prsworkswgg.streamlit.app/`.

For a shorter paste-ready Markdown/HTML block, use
`docs/portfolio_paste_pack.md`.

## Project Card

**Title:** Smart Manufacturing AI Operations Platform

**Short description:** End-to-end industrial AI portfolio demo for smart
manufacturing operations, predictive maintenance, data quality monitoring, and
decision support.

**Role:** Full-stack Industrial AI / Machine Learning Engineering project

**Status:** Public portfolio demo using synthetic manufacturing data

**Live demo:** `https://smart-manu-portfolio-prsworkswgg.streamlit.app/`

**Source code:** `https://github.com/prsworkswgg/smart_manu/tree/codex/streamlit-portfolio-polish`

**Main app file:** `streamlit_app.py`

**Tech stack:** C# .NET, FastAPI, Python, SQLite, scikit-learn, Streamlit,
Plotly, pytest, GitHub, Streamlit Community Cloud

## One-Line Summary

Built an end-to-end Smart Manufacturing AI Operations Platform that connects
data acquisition, API ingestion, data quality checks, ML workflow, operational
risk triage, and a Streamlit command-center dashboard using synthetic factory
data.

## Portfolio Case Study

Many machine learning portfolio projects stop at a notebook. This project was
built to demonstrate a more complete industrial AI workflow: data acquisition,
backend ingestion, storage, validation, model training, inference, operations
dashboarding, and deployment packaging.

The system simulates a precision-electronics manufacturing environment with
production lines, stations, machines, process signals, quality indicators, and
maintenance risk signals. A C# data acquisition service generates sensor and
production events and posts them to a FastAPI backend. The backend stores data
in SQLite, runs data quality checks, prepares features, trains predictive
maintenance and anomaly detection models, and exposes inference endpoints.

The Streamlit dashboard acts as an operations command center. It reduces the
main page to four primary KPIs, an action queue, and a line risk map. Detail is
moved into drill-down pages for operations overview, data collection, line
monitoring, machine investigation, anomaly investigation, data quality, model
training, and reports. Charts are time-windowed, downsampled, threshold-aware,
and filterable by line, station, and machine.

The dashboard also includes a trust layer for every metric. Each metric is
tagged as `Live`, `Replay`, `Derived`, `Model unavailable`, or `Not checked` so
the viewer can tell whether a number comes from live-like demo data, replayed
historical records, derived calculations, an unavailable model, or an unchecked
source. This makes the interface more honest and closer to a real operations
tool than a decorative analytics page.

## What This Demonstrates

- End-to-end industrial AI architecture from data acquisition to dashboard.
- C# collector pattern with HTTP publishing, buffering, and retry behavior.
- FastAPI ingestion and inference endpoints.
- SQLite-backed local demo data layer.
- Python data quality checks for missing values, duplicate timestamps, gaps,
  stuck sensors, impossible values, and synthetic data quality issues.
- ML workflow for failure classification, remaining useful life estimation,
  and anomaly detection.
- Streamlit command center designed around operator decisions, not just charts.
- Trust badges that make metric provenance explicit.
- Time-windowed, threshold-aware charting with line, station, and machine
  selection.
- i18n audit support to keep Thai and English dashboard pages separate.
- Visual regression screenshots for desktop and mobile dashboard states.

## Dashboard Highlights

**Command center:** Four operational KPIs, current risk posture, action queue,
and line risk overview.

**Action queue:** Prioritized operational tasks such as data quality escalation,
machine investigation, anomaly review, and model readiness checks.

**Risk map:** Line-level risk cards that show where attention should go first,
instead of leaving the user to interpret a wall of charts.

**Drill-down pages:** Dedicated views for line monitoring, machine
investigation, anomaly investigation, data quality, model training, and reports.

**Trust layer:** Each metric is labeled with provenance: `Live`, `Replay`,
`Derived`, `Model unavailable`, or `Not checked`.

## Screenshots To Use

Use screenshots captured from the actual Streamlit dashboard, not mockups.

- `assets/screenshots/desktop/01_command_center.png`
  - Caption: Operations command center with KPI trust badges, action queue, and
    line risk overview.
- `assets/screenshots/desktop/04_line_monitoring.png`
  - Caption: Line monitoring view with time-windowed, threshold-aware charts and
    line/station/machine filtering.
- `assets/screenshots/mobile/01_command_center.png`
  - Caption: Mobile command center layout with compact operational cards and
    trust badges.
- `assets/screenshots/mobile/04_line_monitoring.png`
  - Caption: Mobile line monitoring view optimized for scanability.

## Resume Bullets

- Built an end-to-end Smart Manufacturing AI Operations Platform using C# .NET,
  FastAPI, SQLite, Python ML, and Streamlit.
- Designed a Streamlit operations command center with KPI trust badges, action
  queue, line risk map, drill-down workflow pages, and mobile-responsive
  dashboard layouts.
- Implemented synthetic manufacturing data generation, data quality checks,
  feature preparation, ML model workflow, and dashboard-ready SQLite reporting.
- Added i18n audit tooling and visual regression screenshots for desktop and
  mobile portfolio validation.
- Packaged the project for Streamlit Community Cloud using a dedicated
  `streamlit_app.py` entrypoint and automatic synthetic demo data seeding.

## LinkedIn / Portfolio Post

I built a Smart Manufacturing AI Operations Platform as a portfolio demo for
Industrial AI and Machine Learning Engineering.

The project connects a C# .NET data acquisition service, FastAPI ingestion,
SQLite storage, Python data quality checks, ML workflow, inference endpoints,
and a Streamlit operations dashboard. The dashboard is designed as a decision
surface rather than a static chart page: it includes four primary KPIs, metric
trust badges, an action queue, a line risk map, and drill-down pages for
investigation.

The app uses synthetic manufacturing data only. It does not claim real factory
deployment or real manufacturer data. The goal is to demonstrate practical
architecture, honest data boundaries, operational UX thinking, and runnable
engineering evidence.

## Interview Pitch

I built this project to show the full industrial AI workflow beyond a notebook.
A C# collector sends synthetic machine and production events to a FastAPI
backend. The backend stores data in SQLite, runs data quality checks, prepares
features, trains demo ML models, and serves prediction outputs. A Streamlit
dashboard reads the real demo database and presents the results as an
operations command center with KPI trust badges, action queue, risk map, and
drill-down pages.

The strongest design choice is that the dashboard separates decision-making
from raw detail. The landing page focuses on what an operator or shift lead
should do next, while detailed charts and tables are moved into investigation
pages. Every metric also carries a trust badge so the viewer can tell whether
the value is live-like, replayed, derived, model-dependent, or not checked.

This is a synthetic-data demo, not a validated production control system. A
real deployment would require real OT/IT integration, historian or message
broker integration, cybersecurity review, plant validation, model monitoring,
and process-owner sign-off.

## Honest Boundary

Correct claim:

> This is a manufacturer-aligned demo data operations system for smart
> manufacturing AI workflows.

Do not claim:

- Real manufacturer production data.
- Real factory deployment.
- Factory-certified predictive maintenance model.
- Validated maintenance recommendations.
- Closed-loop process control.

## Suggested Portfolio Layout

1. Hero image: desktop command center screenshot.
2. Short summary and role.
3. Problem: smart manufacturing teams need trustworthy operational visibility.
4. Solution: end-to-end data acquisition, ML workflow, and command-center
   dashboard.
5. Architecture: C# collector -> FastAPI -> SQLite -> ML workflow -> Streamlit.
6. UX decisions: four KPIs, action queue, risk map, drill-down pages, trust
   badges.
7. Engineering evidence: tests, i18n audit, visual regression screenshots,
   Streamlit Cloud entrypoint.
8. Limitations: synthetic data only, not a real factory deployment.
9. Links: live Streamlit app and GitHub repository.
