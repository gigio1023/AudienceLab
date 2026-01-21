# Shared Contracts and Outputs

This folder is the file-based integration point between the simulator, dashboard, and evaluators.

## Simulation Status Files

- **Path**: `shared/simulation/{simulationId}.json`
- **Schema**: `shared/simulation-schema.json`
- **Producer**: `agent/runner.py`
- **Consumer**: `dashboard/` (polling)

The dashboard polls these files for progress and final metrics.

## Evaluation Files

- **Expected input schema**: `shared/evaluation/expected-schema.json`
- **Result schema**: `shared/evaluation/result-schema.json`
- **Outputs**: `shared/evaluation/results/{evaluationId}.json`

See `shared/evaluation/README.md` for details.
Evaluation snapshots are also copied into `dashboard/public/evaluation/` for the UI.

## Notes

- Use ISO-8601 timestamps for `createdAt`/`updatedAt`
- Keep payloads compact; this is a polling-based interface
- Avoid adding PII to shared outputs
