# Agent System - Local Playwright + OpenAI

Simple swarm-based simulation for social media engagement using local Playwright automation with OpenAI decision-making. The current entrypoint is `local_agent.py`, and logs are written for live dashboard monitoring and evaluation.

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

### Simple Swarm Design

The agent system is **local-first**:

1. **Playwright runs locally** - Browser automation executes on your machine
2. **OpenAI makes decisions** - AI determines actions based on page content and persona
3. **Single entrypoint** - `local_agent.py` starts the swarm and writes logs for monitoring

**LocalPlaywrightAgent** (`local_agent.py`)
- Manages browser lifecycle and page navigation
- Extracts visible page content for decision-making
- Executes actions (like, comment, scroll, noop)
- Logs all actions to JSONL files (dashboard + evaluation input)

**Personas**
- Each agent has a unique persona with interests and behavior patterns
- Personas influence action decisions and comment content

## Quick Start

```bash
cd agent
uv sync
uv run python local_agent.py
```

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
MCP_MAX_STEPS=35
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
uv run python local_agent.py
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
| `MCP_MAX_STEPS` | `35` | Maximum steps per agent |
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

Make sure SNS-Vibe is running first:

```bash
# In terminal 1
cd sns-vibe
npm run dev -- --port 8383

# In terminal 2
cd agent
uv run python local_agent.py
```

**Options:**
- `--num-agents N` - Number of swarm agents (default: 3)
- `--max-steps N` - Maximum steps per agent (default: 10)
- `--all-headed` - Show all browser windows
- `--all-headless` - Run all agents headless
- `--screenshots` - Save screenshots during execution

## Outputs

Agent action logs are written as JSONL for live monitoring in the dashboard and for evaluation:

- **Dashboard logs**: `search-dashboard/public/simulation/*.jsonl` (default output dir)
- **Evaluation**: run `eval-agent/` after the swarm finishes to assess results

### JSONL Action Log Format

Each agent log file (`{agentId}__{personaId}.jsonl`) contains one JSON object per line:

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
- Reduce `--num-agents`: `uv run python local_agent.py --num-agents 2`
- Use headless mode (default) instead of `--all-headed`

### Debug Mode

Enable verbose logging:

```bash
# Set log level in .env
AGENT_LOG_LEVEL=DEBUG

# Or use environment variable
AGENT_LOG_LEVEL=DEBUG uv run python local_agent.py
```

### Viewing Logs

```bash
# View agent action logs
tail -f search-dashboard/public/simulation/*.jsonl

# Pretty-print JSONL
cat search-dashboard/public/simulation/*.jsonl | jq
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

Update `sns-vibe/seeds/personas.json` (used by `local_agent.py`) to include your custom personas:
```bash
cp custom_personas.json ../sns-vibe/seeds/personas.json
```

### Extending the Swarm

See `local_agent.py:run_local_agents_parallel()` for the orchestration logic. Key extension points:

- **Pre-run hooks**: Add setup logic before agent execution
- **Post-run hooks**: Add cleanup or aggregation logic
- **Custom metrics**: Modify result aggregation
- **Agent lifecycle**: Customize agent creation and configuration

### Testing Changes

```bash
# Test with small swarm
uv run python local_agent.py --num-agents 2 --max-steps 5
```

### Code Structure

```
agent/
├── local_agent.py       # Core local Playwright agent
├── runner.py            # Multi-agent orchestration
├── cli.py               # Legacy command-line interface
├── single_agent.py      # Legacy single-agent runner
├── accounts.py          # Account management
├── run_all.sh           # Legacy total solution script
├── .env                 # Configuration
├── personas.json        # Default personas
└── output/              # Local artifacts (optional)
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
2. Review logs in `search-dashboard/public/simulation/`
3. Enable debug mode with `AGENT_LOG_LEVEL=DEBUG`

## License

See project root LICENSE file.
