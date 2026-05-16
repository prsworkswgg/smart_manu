# Final Release Checklist

| Check | Status | Notes |
|---|---|---|
| dotnet run sends data to API | NEEDS LOCAL RUN | Requires .NET SDK and running FastAPI |
| FastAPI receives data and writes SQLite | READY TO TEST | `/ingest/*` endpoints implemented |
| SQLite contains real rows | READY TO TEST | Check `/data-acquisition/status` |
| Python `train_all.py` runs | READY TO TEST | Requires enough simulated data |
| model artifacts created | READY TO TEST | Creates files under `models/` |
| metrics JSON created | READY TO TEST | Creates metrics under `models/` |
| prediction endpoints work | READY TO TEST | Requires trained models |
| dashboard opens | READY TO TEST | `streamlit run dashboard/app.py` |
| dashboard shows real data | READY TO TEST | Reads SQLite, no hardcoded demo values |
| report export works | READY TO TEST | Dashboard exports CSV/Markdown |
| README has run steps | PASS | Run steps included |
| docs have limitations | PASS | `docs/limitations.md` included |
| no real Seagate data claim | PASS | Disclaimers included |
| resume bullets align to JD | PASS | `docs/portfolio_package.md` |
| interview pitch clear | PASS | `docs/portfolio_package.md` |

## Missing items

- Dashboard screenshots
- Demo video or GIF
- Actual metric values from the user's local run
- Integration test suite
- CI workflow

## Must-fix before applying

1. Run the full system locally from clean clone.
2. Capture screenshots of all 8 dashboard pages.
3. Save model metrics from one complete demo run.
4. Add screenshots to README.
5. Practice answers about simulated data and RUL limitations.

## Nice-to-have

- Docker Compose
- PostgreSQL option
- OPC UA or MQTT adapter
- API authentication
- unit tests and integration tests
- architecture diagram image

## Final score

Current repository readiness score: **8.6 / 10**

With screenshots, local run proof, and a short demo video: **9.2 / 10**

## Recommended next action

Run the full demo locally and capture evidence:

```bash
bash scripts/run_api.sh
cd acquisition-csharp/SensorCollector && dotnet run
python backend-python/src/data/preprocessing.py
python backend-python/src/models/train_all.py
bash scripts/run_dashboard.sh
```
