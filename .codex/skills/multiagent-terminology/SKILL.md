---
name: multiagent-terminology
description: Reference OpenAI multi-agent terminology and how it maps to this project. Use when writing docs, slides, or demo narration that needs precise terminology.
---

# Multi-Agent Terminology

## Core terms

- **Orchestrator-Subagent**: central runner coordinating agents.
- **Agent Specialization**: distinct roles (e.g., reasoning vs action).
- **Agentic Loop**: observe->reason->act->log.
- **Stigmergy**: indirect coordination through the environment.
- **Guardrails**: sandbox + budget limits + schema checks.
- **Tracing**: structured logs and artifacts for inspection.

## Project mapping (current MVP + planned)

- **Orchestrator**: future runner that spawns agents (planned).
- **Subagents**: `agent/single_agent.py` today; multi-agent planned.
- **Stigmergy**: comments and feed state as shared context (planned).
- **Tracing**: `shared/simulation/*.json` with `agentLogs`.

## Phrases to use

- “persona-driven multi-agent simulation”
- “orchestrator-subagent pattern with sandboxed SNS”
- “stigmergic coordination via shared feed state”
