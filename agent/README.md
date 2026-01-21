# Agent Simulator

Persona-driven multi-agent swarm that operates a local SNS via Playwright and uses OpenAI for action decisions. It writes JSONL activity logs for the dashboard and can emit structured simulation status files for downstream consumers.

## Role in the System

- **Input**: Personas + local SNS feed
- **Action**: Browse, like, comment, follow with human-like timing
- **Output**:
  - Live JSONL logs for the dashboard
  - (Optional) `shared/simulation/{simulationId}.json` for status/progress

## Entrypoints

- `local_agent.py`: fastest path for a small swarm and live JSONL logs
- `runner.py`: structured simulation runner that writes `shared/simulation/*.json`

## Quick Start (SNS-Vibe)

**Prerequisites**:
- Node.js 18+
- Python 3.11+
- `uv`
- OpenAI API key

### 1) Start SNS-Vibe
```bash
cd ../sns-vibe
npm install
bash scripts/reset-db.sh
npm run dev -- --port 8383
```

### 2) Configure and Install Agent Dependencies
```bash
cd ../agent
cp .env.sample .env
# Set OPENAI_API_KEY and SNS_URL=http://localhost:8383
uv sync
uv run playwright install chromium
```

### 3) Run a Swarm
```bash
uv run python local_agent.py
# or: uv run python runner.py --num-agents 3
```

## Configuration

The agent reads environment variables from `agent/.env`.

**Required**:
- `OPENAI_API_KEY`

**Common**:
- `SNS_URL` (default: `http://localhost:18383`; set to `http://localhost:8383` for SNS-Vibe)
- `OPENAI_MODEL` (default: `gpt-5-mini`)
- `OPENAI_BASE_URL` (optional)
- `MCP_MAX_STEPS`, `MCP_STEP_DELAY_MIN`, `MCP_STEP_DELAY_MAX`
- `AGENT_LOG_LEVEL`

**Runner-only (used by `runner.py`)**:
- `SNS_EMAIL`, `SNS_PASSWORD`, `SNS_USERNAME`
- `OPENAI_COMPUTER_USE_MODEL`
- `OPENAI_REASONING_EFFORT`
- `OPENAI_AUTO_ACK_SAFETY_CHECKS`
- `PLAYWRIGHT_MCP_URL`

## Outputs

- **Live logs**: `dashboard/public/simulation/{agentId}__{personaId}.jsonl`
- **Screenshots** (optional): `dashboard/public/simulation/screenshots/`
- **Simulation status** (runner): `shared/simulation/{simulationId}.json`

## DOM Expectations (SNS-Vibe)

Selectors are optimized for predictable IDs. Comment actions look for:

- `#comment-input-{postId}` or `#post-{postId} [data-action='comment-input']`
- `#comment-button-{postId}` or `#post-{postId} [data-action='comment-submit']`

If you swap the SNS frontend, keep these selectors or update them in `local_agent.py`.

## Troubleshooting

- **Playwright executable missing**
  ```bash
  uv run playwright install chromium
  ```

- **Cannot reach SNS**
  - Ensure the SNS server is running
  - Verify `SNS_URL` matches the port you started

- **No comments posted**
  - Check DOM IDs in the SNS UI match the selectors above

## Related Docs

- Project overview: `../README.md`
- Shared schemas: `../shared/README.md`
- Lightweight SNS: `../sns-vibe/README.md`
