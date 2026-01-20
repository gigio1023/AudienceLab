# AudienceLab

Local-first multi-agent orchestrator for simulating influencer marketing campaigns using AI-powered social media agents. The system combines real Instagram engagement data with local SNS simulation to evaluate campaign performance.

## Overview

AudienceLab is a hackathon project that demonstrates a closed-loop system: **Data → Personas → Simulation → Metrics → Ranking + Explanation**. It helps evaluate influencer marketing candidates by simulating follower engagement on a local social network platform.

### Key Features

- **Multi-Agent Simulation**: 100+ concurrent AI agents with unique personas
- **Local-First Architecture**: All components run locally, no cloud deployment needed
- **Hybrid Agent System**: Combines local Playwright automation with OpenAI decision-making
- **Real Data Calibration**: Uses actual Instagram engagement metrics as baseline
- **Visual Dashboard**: Interactive UI for simulation results and reporting

## Components

The project is organized into separate components with clear data contracts:

```
AudienceLab/
├── agent/              # AI agent simulation system
├── sns-vibe/           # Local social network (SvelteKit)
├── search-dashboard/   # Simulation & reporting UI (React)
├── insta-crawler/      # Instagram data collection tools
├── shared/             # Data schemas and contracts
└── context/            # Research notes and documentation
```

### Component Details

| Component | Technology | Description |
|-----------|-----------|-------------|
| **[agent/](agent/README.md)** | Python, Playwright, OpenAI | Persona-based browser agents with local execution |
| **[sns-vibe/](sns-vibe/README.md)** | SvelteKit, SQLite | Local social network platform for simulation stage |
| **search-dashboard/** | React, TypeScript, Vite | Simulation configuration and results dashboard |
| **insta-crawler/** | Python, Playwright | Instagram data collection and dataset tools |
| **shared/** | JSON Schema | File-based data exchange contracts |

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- uv (recommended) - `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Run Complete Simulation

The fastest way to run a full simulation:

```bash
cd agent
./run_all.sh --crowd-count 9 --max-concurrency 4
```

This automatically:
1. Checks prerequisites
2. Installs dependencies
3. Starts SNS-Vibe server
4. Runs agent simulation
5. Outputs results to `agent/outputs/`

See [agent/README.md](agent/README.md) for detailed setup and usage instructions.

### Manual Setup

If you prefer step-by-step setup:

#### 1. Set up SNS-Vibe

```bash
cd sns-vibe
npm install
npm run dev -- --port 8383
```

#### 2. Set up Agent System

```bash
cd agent
cp .env.sample .env
# Edit .env and add your OPENAI_API_KEY

uv sync
uv run playwright install chromium
```

#### 3. Run Simulation

```bash
cd agent
uv run python cli.py run --crowd-count 9 --max-concurrency 4
```

## Architecture

### Data Flow

```
Instagram Data → Crawler → SQLite
                              ↓
                     Persona Generator
                              ↓
                     Agent Simulation
                    (Local SNS Platform)
                              ↓
                     Metrics Aggregation
                              ↓
                      Dashboard Display
```

### Component Integration

**Data Contracts** (`shared/`):
- Simulation results: `simulation/{simulationId}.json`
- Action logs: JSONL format in `agent/outputs/`
- Schemas: `simulation-schema.json`, `action-schema.json`

**Agent System** (`agent/`):
- Reads persona definitions
- Executes browser automation locally
- Uses OpenAI for decision-making (no MCP server needed)
- Writes action logs and aggregated results

**SNS Platform** (`sns-vibe/`):
- Provides simulation environment
- Handles user authentication
- Stores posts, comments, likes
- Serves feed to agents

**Dashboard** (`search-dashboard/`):
- Polls `shared/simulation/` for results
- Displays pre-selected influencer candidates
- Shows simulation progress and metrics
- Generates comparison reports

## Agent System Architecture

The agent system uses a **hybrid local-first approach**:

- **Playwright runs locally** - Browser automation on your machine
- **OpenAI makes decisions** - AI determines actions based on page content
- **No MCP server required** - Avoids need for publicly accessible URLs

See [agent/README.md](agent/README.md) for complete documentation on:
- Architecture details
- Setup and configuration
- Usage examples
- Troubleshooting
- Development guide

## Data Requirements

### Tier System

| Tier | Content | Status |
|------|---------|--------|
| **Tier 1** | Influencer profiles + posts + engagement counts | MVP required |
| **Tier 2** | Tier 1 + sample comments + commenter profiles | Stretch goal |
| **Tier 3** | Tier 2 + follower edges + post likers | Optional |

### Minimum Data Contract (MVP)

```
Influencer: username, biography, followers, is_private, fetched_at
Post: shortcode, user_username, taken_at, caption, like_count, comment_count
Comment (Tier 2+): comment_id, shortcode, owner_username, text, created_at
```

## Simulation Details

### What is Simulated

- Influencers post campaign content on local SNS
- Followers represented by personas (from Instagram data or templates)
- Each persona drives a browser agent with realistic timing
- Agents navigate, like, comment, follow with consistent behavior
- Actions logged for analysis and metrics

### Engagement as Proxy Metric

- Real conversion tracking is out of scope
- Engagement signals (likes, comments, follows) serve as primary evaluation proxy
- Assumption: Higher engagement correlates with better marketing performance

### Evaluation Logic

- **Tier 1+**: Compare simulated engagement to historical Instagram metrics
- Use normalized metrics (engagement rate per post) to avoid scale bias
- Always label confidence based on data coverage (Tier 1 vs 2/3)

## Configuration

Main configuration files:

- `agent/.env` - Agent system configuration (OpenAI, SNS, timing)
- `sns-vibe/.env` - SNS platform settings
- `agent/personas.json` - Agent persona definitions

See component-specific documentation for detailed configuration options.

## Outputs

### Agent Simulation Outputs

```
agent/outputs/{runId}/
├── hero/
│   └── actions.jsonl           # Hero agent action log
├── local-crowd-001/
│   └── actions.jsonl           # Crowd agent action log
└── ...
```

### Simulation Results

```
shared/simulation/{simulationId}.json  # Aggregated results
```

See [agent/README.md](agent/README.md#outputs) for output format details.

## Development Guidelines

- **Hackathon Mode**: Speed over best practices; local-only deployment
- **Component Isolation**: Use explicit data contracts between components
- **Python Projects**: Use `uv` CLI for dependency management (not pip/poetry)
- **Light Dependencies**: Keep dependency footprint minimal
- **Mock When Needed**: Use fixtures when backend dependencies unavailable

## Troubleshooting

### Common Issues

**SNS-Vibe won't start**:
```bash
# Check port availability
lsof -i :8383
# Kill existing process
pkill -f "vite.*sns-vibe"
```

**Agent simulation fails**:
- Check `OPENAI_API_KEY` in `agent/.env`
- Verify SNS-Vibe running: `curl http://localhost:8383`
- Review logs in `agent/outputs/{runId}/`

**Browser automation errors**:
```bash
cd agent
uv run playwright install chromium
```

See [agent/README.md#troubleshooting](agent/README.md#troubleshooting) for comprehensive troubleshooting guide.

## Documentation

- **Project Overview**: `AGENTS.md` - Comprehensive architecture guide (Korean)
- **Agent System**: `agent/README.md` - Complete agent documentation
- **Data Contracts**: `shared/README.md` - Schema documentation
- **Component Guides**: Each component has its own README

## Success Criteria (Hackathon)

- ✅ Local SNS running and accessible
- ✅ Agents can authenticate and perform realistic actions
- ✅ Dashboard shows end-to-end flow: shortlist → simulation → reporting
- 🎯 Tier 1 Instagram dataset collected and loaded
- 🎯 Tier 2+ data (stretch goal)

## Known Limitations

- Instagram crawling is manual/one-time (no automated pipeline)
- Resource limits may constrain true 100+ concurrent agents without scheduling
- Influencer matching/ranking not fully end-to-end (dashboard uses mock data)
- Single simulation mode (no parallel runs)

## Future Improvements

- [ ] Real-time simulation progress via WebSocket
- [ ] Multi-simulation comparison
- [ ] Export functionality (CSV, PDF)
- [ ] Enhanced persona generation from Tier 2+ data
- [ ] Automated Instagram data refresh pipeline

## License

See LICENSE file for details.

## Support

For issues:
1. Check component-specific README (especially [agent/README.md](agent/README.md))
2. Review logs in `agent/outputs/` and `/tmp/sns-vibe.log`
3. Enable debug mode: `AGENT_LOG_LEVEL=DEBUG`

## Contributing

This is a hackathon project. When making changes:
- Follow component-specific conventions
- Keep changes focused and small
- Use typed interfaces for data contracts
- Document new features in component READMEs
