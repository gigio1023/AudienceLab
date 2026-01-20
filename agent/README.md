# Agent Runner (Hero + Crowd)

Hybrid runner aligned with the hackathon strategy: the crowd simulates decisions
headlessly, while the hero validates with a real browser session.

## Setup

```bash
cd agent
cp .env.sample .env
# Set OPENAI_API_KEY (optional for --dry-run)
# Default models: gpt-5-mini for crowd, computer-use-preview for hero
# Optional: AGENT_LOG_LEVEL=DEBUG for verbose logs
uv sync
uv run playwright install chromium
```

Seed accounts and login method are documented in `agent/ACCOUNTS.md`.
If you set `SNS_EMAIL`, use one of the seed agent emails to override the default.

## Run (CLI)

```bash
uv run python cli.py run \
  --goal "Hybrid SNS simulation run" \
  --crowd-count 8
```

Optional flags:

- `--dry-run` skips OpenAI calls and still writes outputs.
- `--no-hero` disables the browser-based hero agent.
- `--persona-file agent/personas.json` to override personas.
- `--headed` runs the hero with a visible browser.
- `--no-screenshots` disables hero screenshot artifacts.
- `--post-context` overrides the crowd text context.

## Smoke Test (Quick Validation)

```bash
uv run python cli.py smoke-test --verbose
```

## Outputs

- Simulation status/result: `shared/simulation/{simulationId}.json`
- Per-action logs: `agent/outputs/{runId}/{agentId}/{sequence}_{action}.json`
- Per-agent stream: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- Schema for action logs: `agent/outputs/action-schema.json`

## Single Agent (Compatibility)

```bash
uv run python single_agent.py
```

Outputs a simulation state file under `shared/simulation/`.

## Evaluate Like/Comment Similarity

```bash
uv run python cli.py evaluate \
  --expected ../shared/evaluation/expected.example.json \
  --run-id <runId>
```

If no run info is provided, the evaluator uses the latest run under `agent/outputs/`.
