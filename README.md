# AudienceLab

> A local-first, persona-driven multi-agent SNS simulator that generates engagement signals and streams results to a live dashboard.

## Demo

Local demo:
- SNS: http://localhost:51737
- Dashboard: http://localhost:51730

Ports are configured in each `package.json`, so you do not need to pass explicit port flags when starting the dev servers.

## Problem Definition

Influencer campaigns are expensive to validate, and teams lack a fast, repeatable way to compare shortlisted creators with realistic engagement signals before spending real budget.

## Solution

AudienceLab runs a local SNS and drives a swarm of persona-based agents using Playwright + OpenAI to simulate likes, comments, and follows. The swarm is behaviorally identical; the only difference is whether a given agent runs headed or headless. Results are logged to shared JSON contracts and can be monitored live via the dashboard.

## Evaluation

Evaluation is implemented in `eval-agent/` and operates on agent action logs from `search-dashboard/public/simulation/*.jsonl`:

- Quantitative metrics
  - Engagement Rate = successful (like/comment/follow) / total steps
  - Marketing Engagement Rate = successful (like/comment) on marketing-tagged seed posts / total steps
  - Action distribution by type and success
- Qualitative metrics (LLM judge)
  - Uses `gpt-5-mini` to score comments on:
    - Relevance (1-5)
    - Tone (1-5)
    - Consistency (1-5)
  - Produces average quality scores and a human-readable verdict
- Verdict thresholds
  - Engagement Level: High (>= 50%), Medium (20-49%), Low (< 20%)
  - Comment Quality: Excellent (>= 4.5), Good (4.0-4.4), Fair (3.0-3.9), Poor (< 3.0)

Output is summarized in `eval-agent/evaluation_report.md`.

## Requirements Checklist

- [x] OpenAI API usage
- [x] Multi-agent implementation
- [x] Runnable demo

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

## Tech Stack

- Python, Playwright, OpenAI API (agent runner)
- SvelteKit, SQLite, Tailwind (sns-vibe)
- React, Vite (search-dashboard)
- Python, Pandas, OpenAI API (eval-agent)

## Install & Run

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

## Cost Estimate (GPT-5 mini)

Agent actions consume tokens when decisions are made. In the local Playwright loop (`agent/local_agent.py`), each step calls the model with:

- A system prompt (persona + rules)
- A user prompt containing current page content (up to ~4000 chars)

Rule-of-thumb estimate per step:
- Input: ~1.2k-1.8k tokens
- Output: ~60-120 tokens

Pricing (given):
- Input: $0.250 / 1M tokens
- Output: $2.000 / 1M tokens

Per-step cost (approx):
```
Input 1.5k  -> $0.000375
Output 100  -> $0.000200
Total       -> $0.000575 per step
```

Example (default 9 agents x 35 steps = 315 steps):
```
~$0.13 - $0.22 total (typical range)
```

Notes:
- The `budget` value in `agent/cli.py` is recorded in the simulation config but does not currently enforce stopping.
- Non-`--mcp` runs in `agent/cli.py` make fewer model calls (one decision per agent), so cost is lower.

## Roadmap (Optional)

- Directly stream `shared/simulation/{id}.json` into the dashboard without manual copy
- Expand evaluation to compare multiple runs and export a summary report

## Team

| Name | Role |
| ---- | ---- |
|      |      |
|      |      |
|      |      |
