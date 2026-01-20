---
name: demo-preparation
description: Prepare a short hackathon demo script and recording checklist for the current MVP (Pixelfed + single agent + shared JSON output). Use when assembling a live walkthrough or README demo section.
---

# Demo Preparation

## 3-minute demo flow

1. **Problem + goal (20s)**: explain pre-campaign uncertainty and need for simulation.
2. **SNS stage (30s)**: show Pixelfed running at `https://localhost:8092`.
3. **Agent run (60s)**: run `uv run python agent/single_agent.py` and narrate the observe->decide->act loop.
4. **Result (60s)**: open the newest `shared/simulation/*.json` and point at metrics + logs.
5. **Close (10s)**: highlight local-first, sandboxed, expandable to multi-agent.

## Quick commands

```bash
# Run agent from repo root
cd agent
uv run python single_agent.py

# Show latest simulation result
ls -t ../shared/simulation | head -1
```

## Recording checklist

- Pixelfed accessible on `https://localhost:8092`.
- API key loaded in `agent/.env` (optional, for VLM).
- Terminal font size readable at 1080p.
- One dry run before recording.
