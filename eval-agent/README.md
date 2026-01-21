# Eval Agent

Analyzes agent activity logs and produces a combined quantitative + qualitative assessment of the simulation.

- **Quantitative**: engagement rates, action distribution
- **Qualitative**: LLM-based comment quality scoring (relevance, tone, consistency)

This module was built for the hackathon demo. It prints a CLI summary and writes an evaluation JSON file for the dashboard.

## Inputs

- JSONL logs: `dashboard/public/simulation/*.jsonl`
- Seed posts: `sns-vibe/seeds/posts.json`
  - Used to detect marketing posts via `#ad` / `#sponsored`

## Quick Start

```bash
cd eval-agent
cp .env.sample .env
# Set OPENAI_API_KEY
uv sync
uv run python evaluate.py
```

## Configuration

Environment variables (via `eval-agent/.env` or `agent/.env`):

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (default: `gpt-5-mini`)
- `OPENAI_BASE_URL` (optional)
- `OPENAI_MAX_WORKERS` (default: `16`)
- `EVALUATION_EXPECTED_PATH` (optional expected baseline JSON)
- `EVALUATION_ID` (optional evaluation ID override)

## Outputs

- CLI summary
- `shared/evaluation/results/{evaluationId}.json`
- `dashboard/public/evaluation/results/{evaluationId}.json`
- `dashboard/public/evaluation/latest.json`

Structured output schemas live in `shared/evaluation/`.

## Notes

- If no marketing posts are found, the LLM judge step is skipped.
- Ensure SNS-Vibe seed data exists before running the evaluator.
