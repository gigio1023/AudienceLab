# Shared Simulation Files

Simulation runners write status updates to `shared/simulation/{simulationId}.json`.
The JSON must conform to `shared/simulation-schema.json` so the dashboard can poll it.

Evaluation outputs are written to `shared/evaluation/results/{evaluationId}.json`.
Schemas live under `shared/evaluation/`.
