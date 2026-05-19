# Streamlit Community Cloud Portfolio Deployment

This deployment profile is for a free public portfolio demo. It is not an
always-on factory deployment and does not process real factory data.

## What To Deploy

Use this Streamlit entrypoint:

```text
streamlit_app.py
```

The entrypoint configures:

- `SMOP_PORTFOLIO_MODE=1`
- `SMOP_AUTO_SEED_DEMO=1`
- `SMOP_DB_PATH=data/portfolio_demo.db`

On first boot, the app creates a small synthetic SQLite database if the
dashboard tables are empty. The generated data is synthetic DEMO data only.

## Streamlit Cloud Steps

1. Push the repository to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app from the GitHub repository.
4. Set the main file path to:

```text
streamlit_app.py
```

5. Use the repository root as the app directory.
6. Deploy.

## Expected Free-Tier Behavior

- The public URL stays available.
- The app may sleep when it has no traffic.
- First load after sleep can be slower because the app boots and checks or
  regenerates the portfolio demo database.
- Local SQLite writes are demo state, not durable production storage.

## Portfolio Positioning

Use this wording when sharing the URL:

> Smart Manufacturing AI Operations Platform portfolio demo. It uses synthetic
> manufacturing data to demonstrate ingestion, data quality checks, ML workflow,
> operational risk triage, and a Streamlit command-center dashboard. It is not a
> real factory deployment and does not use proprietary or named-manufacturer
> data.

## Local Smoke Test

Run the same entrypoint locally:

```bash
SMOP_DB_PATH=data/portfolio_demo.db SMOP_AUTO_SEED_DEMO=1 streamlit run streamlit_app.py
```

If you want to reset the generated portfolio database:

```bash
rm -f data/portfolio_demo.db
SMOP_DB_PATH=data/portfolio_demo.db SMOP_AUTO_SEED_DEMO=1 streamlit run streamlit_app.py
```
