# Agent Runner (Single Cycle MVP)

## Setup

```bash
cd agent
cp .env.example .env
uv sync
uv run playwright install chromium
```

## Run

```bash
uv run python single_agent.py
```

Outputs a simulation state file under `shared/simulation/`.
