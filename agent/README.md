# Agent System - Local Playwright + OpenAI

Multi-agent simulation system for social media engagement using local Playwright automation with OpenAI decision-making. This hybrid approach combines the efficiency of local browser automation with AI-powered decision logic, avoiding the need for publicly accessible MCP servers.

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Setup](#setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Architecture

### Hybrid Agent Design

The agent system uses a **local-first architecture** where:

1. **Playwright runs locally** - Browser automation executes on your machine
2. **OpenAI makes decisions** - AI determines which actions to take based on page content and persona
3. **No MCP server required** - Unlike traditional MCP implementations that need public URLs

```
┌─────────────────┐
│  Agent Runner   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ Hero │  │Crowd │  (Multiple agents run concurrently)
└───┬──┘  └──┬───┘
    │         │
┌───▼─────────▼────┐
│ LocalPlaywright  │  (Local browser automation)
│     Agent        │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──────┐ │
│Playwright│ │
│ (Local)  │ │
└──────────┘ │
             │
      ┌──────▼──────┐
      │   OpenAI    │  (Decision making only)
      │  API Call   │
      └─────────────┘
```

### Key Components

**LocalPlaywrightAgent** (`local_agent.py`)
- Manages browser lifecycle and page navigation
- Extracts visible page content for decision-making
- Executes actions (like, comment, scroll, noop)
- Logs all actions to JSONL files

**Runner** (`runner.py`)
- Orchestrates multiple agents (hero + crowd)
- Manages concurrency with semaphores
- Aggregates results and metrics

**Personas**
- Each agent has a unique persona with interests and behavior patterns
- Personas influence action decisions and comment content

## Quick Start

The fastest way to get started is using the total solution script:

```bash
cd agent
./run_all.sh --crowd-count 9 --max-concurrency 4
```

This will:
1. Check prerequisites (Node.js, Python, uv)
2. Install dependencies if needed
3. Start SNS-Vibe server on port 8383
4. Run the agent simulation
5. Clean up on exit

## Setup

### Prerequisites

- **Node.js 18+** - For SNS-Vibe server
- **Python 3.10+** - For agent system
- **uv** (recommended) - Fast Python package manager

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Manual Setup

#### 1. Set up SNS-Vibe

```bash
cd ../sns-vibe
npm install
```

#### 2. Set up Agent Environment

```bash
cd agent
cp .env.sample .env
# Edit .env and set OPENAI_API_KEY

# Using uv (recommended)
uv sync
uv run playwright install chromium

# Or using pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

#### 3. Configure Environment

Edit `agent/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# SNS Configuration
SNS_URL=http://localhost:8383
SNS_EMAIL=local-hero-001@example.com
SNS_PASSWORD=password

# Agent Configuration
MCP_MAX_STEPS=20
MCP_STEP_DELAY_MIN=1.0
MCP_STEP_DELAY_MAX=3.0
```

#### 4. Start SNS-Vibe Server

```bash
cd ../sns-vibe
npm run dev -- --port 8383
```

#### 5. Run Agent Simulation

```bash
cd ../agent
uv run python cli.py run --crowd-count 9 --max-concurrency 4
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-5-mini` | OpenAI model to use |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API endpoint |
| `SNS_URL` | `http://localhost:8383` | SNS-Vibe server URL |
| `SNS_EMAIL` | `local-hero-001@example.com` | Login email for hero agent |
| `SNS_PASSWORD` | `password` | Login password |
| `MCP_MAX_STEPS` | `20` | Maximum steps per agent |
| `MCP_STEP_DELAY_MIN` | `1.0` | Minimum delay between steps (seconds) |
| `MCP_STEP_DELAY_MAX` | `3.0` | Maximum delay between steps (seconds) |
| `MCP_REQUIRE_APPROVAL` | `never` | Approval mode (never/always) |

### Model Compatibility

The system automatically handles different OpenAI model requirements:

**New models (gpt-5, o1, o3)**:
- Use `max_completion_tokens` instead of `max_tokens`
- Only support default temperature (1)

**Legacy models (gpt-4, gpt-3.5)**:
- Use `max_tokens`
- Support custom `temperature` values

This is handled automatically in `local_agent.py:_get_decision()`.

## Usage

### Using run_all.sh (Recommended)

```bash
# Basic usage - 9 crowd agents, max 4 concurrent
./run_all.sh

# Custom configuration
./run_all.sh --crowd-count 20 --max-concurrency 8

# Show browser windows (headed mode)
./run_all.sh --headed

# Dry-run mode (skip actual actions)
./run_all.sh --dry-run

# Combined options
./run_all.sh --crowd-count 15 --max-concurrency 6 --headed
```

**Options:**
- `--crowd-count N` - Number of crowd agents (default: 9)
- `--max-concurrency N` - Max concurrent agents (default: 4)
- `--headed` - Show browser windows
- `--dry-run` - Skip actual browser actions
- `--help` - Show help message

### Using CLI Directly

Make sure SNS-Vibe is running first:

```bash
# In terminal 1
cd sns-vibe
npm run dev -- --port 8383

# In terminal 2
cd agent
source .venv/bin/activate

# Run simulation
python cli.py run --goal "Engagement simulation" --crowd-count 9
```

**CLI Options:**
- `--goal TEXT` - Simulation goal description
- `--crowd-count N` - Number of crowd agents (default: 8)
- `--max-concurrency N` - Max concurrent agents (default: 4)
- `--dry-run` - Skip OpenAI calls and actual actions
- `--no-hero` - Disable hero agent
- `--headed` - Show browser windows
- `--no-screenshots` - Disable screenshots
- `--persona-file PATH` - Custom personas JSON file
- `--post-context TEXT` - Override post context

### Single Agent (for Testing)

```bash
uv run python single_agent.py --mcp --headed
```

### Smoke Test

Quick validation of the system:

```bash
uv run python cli.py smoke-test --verbose
```

## Outputs

All simulation outputs are stored in `agent/outputs/{runId}/`:

### Directory Structure

```
outputs/
└── {runId}/
    ├── hero/
    │   ├── actions.jsonl
    │   ├── 001_navigate.json
    │   ├── 002_login.json
    │   └── ...
    ├── local-crowd-001/
    │   ├── actions.jsonl
    │   └── ...
    ├── local-crowd-002/
    │   ├── actions.jsonl
    │   └── ...
    └── ...
```

### JSONL Action Log Format

Each `actions.jsonl` contains one JSON object per line:

```json
{
  "timestamp": "2026-01-20T06:15:25.136941+00:00",
  "agentId": "local-crowd-001",
  "step": 1,
  "status": "success",
  "decision": {
    "action": "comment",
    "target": "post-17",
    "comment_text": "This looks amazing!",
    "reasoning": "Post aligns with my interests"
  },
  "result": {
    "action": "comment",
    "target": "post-17",
    "success": true
  }
}
```

### Simulation State

Global simulation state is saved to `shared/simulation/{simulationId}.json`:

```json
{
  "simulationId": "uuid",
  "status": "completed",
  "totalAgents": 10,
  "completedAgents": 10,
  "engagement": 45,
  "runId": "timestamp-based-id"
}
```

### Schema Documentation

- Action log schema: `agent/outputs/action-schema.json`
- Simulation schema: `shared/simulation-schema.json`

## Troubleshooting

### Common Issues

#### 1. "Comment input/button not found"

**Problem**: Agent cannot find comment input or button selectors.

**Solution**: The system automatically extracts numeric post IDs from targets. Ensure SNS-Vibe DOM structure matches:
- Comment input: `#comment-input-{postId}`
- Comment button: `#comment-button-{postId}`

See `local_agent.py:_extract_post_id()` for ID extraction logic.

#### 2. "Unsupported parameter: 'max_tokens'"

**Problem**: Using incompatible parameters with newer OpenAI models.

**Solution**: The system auto-detects model type. If you see this error, ensure `local_agent.py:_get_decision()` has proper model detection:
```python
is_new_model = "gpt-5" in model or "o1" in model or "o3" in model
```

#### 3. "Temperature does not support 0.7"

**Problem**: New models only support default temperature.

**Solution**: System automatically omits temperature for new models. No action needed.

#### 4. SNS-Vibe Connection Failed

**Problem**: Cannot connect to `http://localhost:8383`

**Solutions**:
- Verify SNS-Vibe is running: `curl http://localhost:8383`
- Check port 8383 is not in use: `lsof -i :8383`
- Restart SNS-Vibe: `cd sns-vibe && npm run dev -- --port 8383`

#### 5. Playwright Browser Not Installed

**Problem**: `playwright._impl._api_types.Error: Executable doesn't exist`

**Solution**:
```bash
uv run playwright install chromium
```

#### 6. Too Many Concurrent Agents

**Problem**: System slows down or crashes with many agents.

**Solutions**:
- Reduce `--max-concurrency`: `./run_all.sh --max-concurrency 2`
- Reduce `--crowd-count`: `./run_all.sh --crowd-count 5`
- Use headless mode (default) instead of `--headed`

### Debug Mode

Enable verbose logging:

```bash
# Set log level in .env
AGENT_LOG_LEVEL=DEBUG

# Or use environment variable
AGENT_LOG_LEVEL=DEBUG uv run python cli.py run --crowd-count 9
```

### Viewing Logs

```bash
# Watch SNS-Vibe logs
tail -f /tmp/sns-vibe.log

# View agent action logs
tail -f agent/outputs/{runId}/local-crowd-001/actions.jsonl

# Pretty-print JSONL
cat agent/outputs/{runId}/local-crowd-001/actions.jsonl | jq
```

## Development

### Adding New Actions

Edit `local_agent.py:_execute_action()`:

```python
async def _execute_action(self, decision: ActionDecision) -> dict[str, Any]:
    action = decision.action

    if action == "your_new_action":
        # Implement action logic
        await page.click("#your-selector")
        return {
            "action": action,
            "success": True,
        }
```

Update decision prompt in `_get_decision()` to include new action.

### Custom Personas

Create a JSON file with persona definitions:

```json
[
  {
    "name": "FitnessEnthusiast",
    "interests": ["health", "fitness", "nutrition"],
    "behavior": "active",
    "bias": "positive"
  }
]
```

Use with `--persona-file`:
```bash
uv run python cli.py run --persona-file custom_personas.json
```

### Extending the Runner

See `runner.py:run_mcp_agents()` for the main orchestration logic. Key extension points:

- **Pre-run hooks**: Add setup logic before agent execution
- **Post-run hooks**: Add cleanup or aggregation logic
- **Custom metrics**: Modify result aggregation
- **Agent lifecycle**: Customize agent creation and configuration

### Testing Changes

```bash
# Test with single agent
uv run python single_agent.py --mcp --headed

# Test with small crowd
./run_all.sh --crowd-count 2 --max-concurrency 1 --headed

# Dry-run mode (no actual actions)
./run_all.sh --dry-run --crowd-count 5
```

### Code Structure

```
agent/
├── local_agent.py       # Core local Playwright agent
├── runner.py            # Multi-agent orchestration
├── cli.py               # Command-line interface
├── single_agent.py      # Single agent runner (legacy)
├── accounts.py          # Account management
├── run_all.sh           # Total solution script
├── .env                 # Configuration
├── personas.json        # Default personas
└── outputs/             # Simulation outputs
```

## Advanced Topics

### Budget Tracking

The system tracks OpenAI API costs per agent. See `runner.py` for budget management.

### Concurrency Control

Agent concurrency is managed with `asyncio.Semaphore`:

```python
semaphore = asyncio.Semaphore(max_concurrency)
async with semaphore:
    await agent.run_loop(max_steps, max_time_seconds)
```

### Action Biases

Personas have action biases that influence behavior:

- **positive**: Prefers liking and positive comments
- **neutral**: Balanced mix of actions
- **negative**: More critical engagement

See `local_agent.py:Persona` dataclass.

### Evaluation

Compare simulation results with expected outcomes:

```bash
uv run python cli.py evaluate \
  --expected ../shared/evaluation/expected.example.json \
  --run-id {runId}
```

## Account Management

Default seed accounts are documented in `agent/ACCOUNTS.md`. Override with `SNS_EMAIL` environment variable.

## Related Documentation

- **SNS-Vibe**: `../sns-vibe/README.md` - Local social network platform
- **Shared Contracts**: `../shared/README.md` - Data schemas and contracts
- **Project Overview**: `../README.md` - Top-level project documentation

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs in `agent/outputs/` and `/tmp/sns-vibe.log`
3. Enable debug mode with `AGENT_LOG_LEVEL=DEBUG`
4. Test with `--dry-run` to isolate issues

## License

See project root LICENSE file.
