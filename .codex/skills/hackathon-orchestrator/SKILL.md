---
name: hackathon-orchestrator
description: 해커톤 프로젝트 전체 조율 및 시간 관리. 멀티에이전트 시뮬레이션 프로젝트의 7시간 타임라인 관리, 우선순위 결정, 컴포넌트 간 연계 조율에 사용.
---

# Hackathon Orchestrator Skill

## Overview

이 Skill은 **Persona-Driven Influencer Simulation** 해커톤 프로젝트의 전체 조율을 담당합니다.

**프로젝트 핵심 목표**: Real Instagram 데이터를 Ground Truth로 사용하여 Local SNS에서 Multi-Agent 시뮬레이션을 수행하고 인플루언서 캠페인 성과를 예측

## 7-Hour Timeline (11:30 ~ 18:30)

| 시간 | 단계 | 작업 내용 | 담당 컴포넌트 |
|------|------|----------|--------------|
| 11:30-12:00 | P0 | Ground Truth 데이터 수집 | `insta-crawler/` |
| 12:00-13:00 | P1 | Pixelfed 환경 구동 + 시딩 | `sns/` |
| 13:00-14:30 | P2 | Single Agent 완벽 동작 | `agent/` |
| 14:30-16:00 | P3 | Multi-Persona 순차 실행 | `agent/` |
| 16:00-17:00 | P4 | Dashboard 연결 | `search-dashboard/` |
| 17:00-18:00 | P5 | Demo Polish + 제출물 | All |
| 18:00-18:30 | Buffer | 예비 시간 | - |

## Component Directory Map

```
.
├── agent/              # [Core] Python-based Simulation Engine
├── docs/               # [Doc] Specifications & Guides
├── insta-crawler/      # [Data] Instagram Scraper
├── search-dashboard/   # [UI] React Web Application
├── shared/             # [Protocol] JSON Schemas
└── sns/                # [Env] Dockerized Pixelfed
```

## Decision Tree: What to Work On

```
현재 무엇을 해야 하는가?

1. Pixelfed가 실행 중인가?
   └─ NO → [sns-environment] Skill 사용하여 구동
   
2. 시드 데이터가 있는가?
   └─ NO → seeds.json 수동 생성 (15분)
   
3. 1개 에이전트가 동작하는가?
   └─ NO → [agent-simulation] Skill 사용하여 단일 에이전트 구현
   
4. 3개 페르소나가 순차 실행되는가?
   └─ NO → [persona-runner] Skill 사용하여 멀티 페르소나 구현
   
5. 대시보드에서 결과가 보이는가?
   └─ NO → [dashboard-integration] Skill 사용
   
6. 모든 것이 작동하는가?
   └─ YES → Demo 녹화 및 README 작성
```

## Multi-Agent Architecture Keywords

발표 시 사용할 OpenAI 공식 용어:

| 용어 | 프로젝트 적용 |
|------|-------------|
| **Orchestrator-Subagent** | Runner가 Hero/Crowd 에이전트 조율 |
| **Agent Specialization** | Hero(Action) vs Crowd(Reasoning) |
| **Stigmergy** | SNS 환경 통한 간접 협업 |
| **Agentic Loop** | Perceive→Reason→Act 사이클 |
| **Guardrails** | Sandbox 격리 환경 |
| **Tracing** | 에이전트 행동 로그 |

## Quick Commands

### Check All Systems
```bash
# Pixelfed 상태 확인
docker ps | grep pixelfed

# Agent 환경 확인
cd agent && uv --version

# Dashboard 확인
cd search-dashboard && npm run dev
```

### Emergency Fallbacks

| 문제 | Fallback |
|------|----------|
| Pixelfed 실패 | Mock SNS 화면 사용 |
| VLM API 느림 | 사전 녹화 결과 사용 |
| 시간 부족 | 2개 페르소나라도 완벽히 |

## Related Skills

- [sns-environment](../sns-environment/SKILL.md) - Pixelfed 환경 관리
- [agent-simulation](../agent-simulation/SKILL.md) - 에이전트 시뮬레이션
- [persona-runner](../persona-runner/SKILL.md) - 멀티 페르소나 실행
- [dashboard-integration](../dashboard-integration/SKILL.md) - UI 연동
