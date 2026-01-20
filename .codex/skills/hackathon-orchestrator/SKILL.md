---
name: hackathon-orchestrator
description: Coordinate hackathon execution across the repo with a priority order (SNS -> agent MVP -> output validation -> demo), including optional steps when other components exist. Use when planning or triaging end-to-end progress.
---

# Hackathon Orchestrator

## Priority order

1. **Submodule ready**: `git submodule update --init --recursive`.
2. **SNS up**: use `sns-environment` to bring up Pixelfed and seed data.
3. **Agent MVP**: use `agent-simulation` to run `agent/single_agent.py`.
4. **Output check**: ensure `shared/simulation/*.json` matches `shared/simulation-schema.json`.
5. **Demo prep**: use `demo-preparation` for the walkthrough script.

## Optional components

- If `search-dashboard/` exists, wire file polling for `shared/simulation/`.
- If `insta-crawler/` exists, run data collection before seeding Pixelfed.

## Quick checks

```bash
# Pixelfed containers
docker ps | grep pixelfed

# Agent env
cd agent && uv --version

# Latest simulation output
ls -lt shared/simulation | head -5
```

## Fallbacks

- Pixelfed unstable: show CLI output + JSON results only.
- VLM rate limits: run without API key (fallback decision) and explain in demo.
