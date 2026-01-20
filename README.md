# AudienceLab

> A local-first, persona-driven swarm simulator for influencer campaign planning. It mirrors real engagement patterns on a local SNS, logs outcomes to shared contracts, and renders results in a live dashboard.

## Why it exists

Influencer campaigns are expensive to validate. Teams need a fast, repeatable way to compare shortlisted creators using realistic engagement signals **before** spending budget. AudienceLab provides a closed-loop simulation that turns real Instagram-derived context into structured, comparable metrics.

## What it does

- Builds persona-driven agents from real or templated audience signals
- Simulates likes, comments, and follows on a local SNS
- Produces normalized engagement metrics and per-agent action logs
- Streams outputs to a dashboard for review and comparison

## Closed-Loop Flow (Data → Persona → Simulation → Metrics)

1. **Instagram data (Tier 1+)** informs influencer and audience context
2. **Persona builder** produces audience personas (Tier 2+ if comments exist)
3. **Swarm simulation** runs persona agents on a local SNS
4. **Metrics** are aggregated and normalized
5. **Dashboard** ranks candidates and explains why

## Swarm Model

All agents share the same behavior model. The only difference between agents is whether they run **headed** (visible browser) or **headless** (no UI). This keeps the swarm consistent while allowing visual debugging when needed.

## Architecture

```
Persona seeds (sns-vibe/seeds/personas.json)
        |
        v
Agent CLI (agent/cli.py)
  - Swarm agents (Playwright + OpenAI; headed or headless)
        |
        v
Local SNS (sns-vibe: SvelteKit + SQLite)
        |
        v
Outputs
  - shared/simulation/{simulationId}.json
  - agent/outputs/{runId}/{agentId}/actions.jsonl
  - (dashboard feed) search-dashboard/public/simulation/*.jsonl
        |
        v
Search Dashboard (React + Vite)
  - polls /simulation/{id}.json + /simulation/index.json
        |
        v
Evaluation (eval-agent)
  - reads JSONL logs + sns-vibe seed posts
  - LLM judge (gpt-5-mini) for comment quality
```

## Repo Structure

- `agent/` — persona-based browser agents (Playwright + OpenAI)
- `sns-vibe/` — local SNS sandbox (SvelteKit + SQLite)
- `search-dashboard/` — simulation + reporting UI (React + Vite)
- `shared/` — simulation contract and outputs
- `eval-agent/` — offline evaluation on JSONL logs
- `docs/` — deep dives, strategy, troubleshooting

## Demo Ports

Local demo (default dev ports):
- SNS: http://localhost:51737
- Dashboard: http://localhost:51730

Ports are configured in each `package.json`, so you do not need to pass explicit port flags when starting the dev servers.

## Quick Start

```bash
# 1) Configure agent env
cp agent/.env.sample agent/.env
# Set:
# OPENAI_API_KEY=...
# SNS_URL=http://localhost:8383
# (Optional for sns-vibe login) SNS_USERNAME=agent1

# 2) Start SNS (Terminal 1)
cd sns-vibe
npm install
bash scripts/reset-db.sh
npm run dev

# 3) Start Dashboard (Terminal 2)
cd ../search-dashboard
npm install
npm run dev

# 4) Run Simulation (Terminal 3)
cd ../agent
uv sync
uv run python cli.py run --crowd-count 8 --max-concurrency 4

# 5) (Optional) Deploy logs to dashboard feed
python ../scripts/deploy_dashboard_data.py

# 6) Run Evaluation
cd ../eval-agent
uv sync
uv run python evaluate.py
```

## Output Contracts

- **Simulation state**: `shared/simulation/{simulationId}.json`
- **Per-agent action logs**: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- **Dashboard feed**: `search-dashboard/public/simulation/*.jsonl`

See `shared/simulation-schema.json` for the contract.

## Evaluation Summary

Evaluation is implemented in `eval-agent/` and operates on action logs from `search-dashboard/public/simulation/*.jsonl`:

- **Quantitative metrics**
  - Engagement Rate = successful (like/comment/follow) / total steps
  - Marketing Engagement Rate = successful (like/comment) on marketing-tagged seed posts / total steps
  - Action distribution by type and success
- **Qualitative metrics (LLM judge)**
  - Uses `gpt-5-mini` to score comments on relevance, tone, and consistency
  - Produces average quality scores and a human-readable verdict

Output is summarized in `eval-agent/evaluation_report.md`.

## Cost Notes (GPT-5 mini)

Each step calls the model with:
- A system prompt (persona + rules)
- A user prompt containing current page content

Rule-of-thumb estimate per step:
- Input: ~1.2k-1.8k tokens
- Output: ~60-120 tokens

Example (default 9 agents x 35 steps = 315 steps):
- ~`$0.13 - $0.22` total (typical range)

## Troubleshooting Quick Hits

- **SNS not reachable**: confirm `SNS_URL`, then restart `sns-vibe`.
- **Playwright missing**: `uv run playwright install chromium`.
- **Slow runs**: reduce `--crowd-count` or `--max-concurrency`.

## Roadmap (Short)

- Stream `shared/simulation/{id}.json` directly into the dashboard
- Multi-run comparison and exportable reports
- WebSocket progress updates

## License

Hackathon project. Local-first demo focus.
