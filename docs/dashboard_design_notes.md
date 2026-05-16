# Dashboard Design Notes

## Design goal

The dashboard was redesigned to feel like a manufacturing operations command center instead of a simple analytics demo. The user journey now follows a shift-lead workflow:

1. Read the current operating posture.
2. Check whether the data stream is live, delayed, or replay/offline.
3. Review high-priority machine or process actions.
4. Inspect line performance and equipment health.
5. Validate data quality before trusting model output.
6. Review model registry and export a shift-handover report.

## Human-facing language

The dashboard avoids overclaiming. It uses language such as:

- "Shift handover action queue"
- "Recommended maintenance action"
- "Data freshness"
- "Replay / offline dataset"
- "Status is inferred from the latest SQLite timestamp"
- "Generated from failure, RUL, anomaly, and health-score signals"

This makes the project more credible because a real operator screen must explain what the system knows, what it infers, and what still needs human validation.

## Visual improvements

- Production-style hero header.
- Sidebar with site, area, database path, and run order.
- Status pills for ingestion and model posture.
- Compact cards for freshness, data window, risk posture, and DB state.
- Plotly white template with unified hover.
- Action queue table for triage.
- Markdown report upgraded into a shift-handover report.

## Real-system caveat

The dashboard now looks and reads closer to an operations tool, but it still uses simulated data. It should be presented as a production-oriented MVP, not as a deployed manufacturing system.
