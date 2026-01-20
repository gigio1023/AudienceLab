---
name: agent-simulation
description: Implement or run the Python Playwright single-agent simulator in `agent/`, including env setup with `uv`, Pixelfed login, and writing results to `shared/simulation/`. Use when modifying the agent loop, selectors, or simulation output.
---

# Agent Simulation

## Quick start

```bash
cd agent
cp .env.example .env
uv sync
uv run playwright install chromium
uv run python single_agent.py
```

## Output contract

- Write updates to `shared/simulation/{simulationId}.json`.
- Keep payloads aligned with `shared/simulation-schema.json`.
- Use atomic writes (temp file + replace) to avoid partial reads.

## Safe edit checklist

- Keep all dependency changes in `pyproject.toml` and install with `uv`.
- Preserve HTTPS handling for self-signed Pixelfed (`ignore_https_errors=True`).
- Respect env vars: `SNS_URL`, `SNS_EMAIL`, `SNS_PASSWORD`, `OPENAI_MODEL`.
- If a new action is added, log it in `agentLogs` and update metrics accordingly.

## Troubleshooting

- **Login loops**: confirm seed users exist in Pixelfed and credentials match `.env`.
- **SSL errors**: ensure `args=["--ignore-certificate-errors"]` is present.
- **No API key**: `OPENAI_API_KEY` empty will skip VLM and log a fallback reason.
- **Selector misses**: update `perform_action` selectors to match Pixelfed UI labels.
