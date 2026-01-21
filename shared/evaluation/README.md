# Evaluation Contracts

This folder defines the schema for comparing simulated engagement against expected baselines.

## Files

- `expected-schema.json`: target engagement values (overall + per persona)
- `result-schema.json`: computed metrics and similarity scores
- `expected.example.json`: minimal example input
- `results/{evaluationId}.json`: generated evaluation outputs

## Typical Flow

1. Create an **expected** file that describes desired engagement levels.
2. Run an evaluator to compute actual metrics from JSONL logs.
3. Emit a **result** file that conforms to `result-schema.json`.

The current `eval-agent/` module emits files in this format and also copies a latest snapshot into the dashboard public folder.
