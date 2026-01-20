---
name: jsonl-activity-feed
description: Integrate per-agent JSONL activity logs into the dashboard using index.json, normalization, and polling. Use when the user asks about agent log files, JSONL schemas, activity feeds, or dashboard updates from agent actions.
---

# JSONL Activity Feed

## Purpose

Connect per-agent JSONL activity logs to the dashboard. This skill applies when the system writes one JSONL file per agent and the dashboard polls those files for live activity.

## Workflow

1. Confirm the feed root is `search-dashboard/public/simulation/`.
2. Use `index.json` to discover active JSONL files (fallback to `VITE_AGENT_FEEDS`).
3. Normalize loose JSONL records via `src/lib/activityInterface.ts`.
4. Render the most recent events only (avoid loading the entire file).
5. Update docs in `docs/components/dashboard.md` and `docs/contracts/simulation.md` after schema changes.

## Implementation anchors

- Feed index: `search-dashboard/public/simulation/index.json`
- Polling hooks: `search-dashboard/src/hooks/useAgentActivityFeed.ts`, `search-dashboard/src/hooks/useActivityFeedIndex.ts`
- Normalization: `search-dashboard/src/lib/activityInterface.ts`
- Types: `search-dashboard/src/types/activity.ts`

## Data formats

For JSONL and index formats, see [references/FEED_FORMATS.md](references/FEED_FORMATS.md).

## Guardrails

- Keep JSONL append-only.
- Prefer rolling files by time or size.
- Avoid heavy reads: parse only the last N lines.
- Treat malformed lines as non-fatal.
