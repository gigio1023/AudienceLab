# Agent Outputs

Each agent action is written as a JSON file under:

```
agent/outputs/{runId}/{agentId}/{sequence}_{action}.json
```

Each agent also appends every action to a JSONL stream:

```
agent/outputs/{runId}/{agentId}/actions.jsonl
```

The schema is defined in `agent/outputs/action-schema.json` and applies to both
the per-action JSON files and each JSONL line.

Artifacts (e.g., screenshots) are saved alongside action logs and referenced
in the `artifacts` array of the action file.
