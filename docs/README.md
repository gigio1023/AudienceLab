# Project Definition: Persona-Driven Influencer Simulation (Current Implementation)

> **One-line Summary**: Local Pixelfed에서 Persona 기반 시뮬레이션을 실행하고, 결과를 파일로 저장하는 로컬-first 에이전트 러너.

## Agent Skills Guide

Agent Skills 운영 가이드는 `docs/AGENT_SKILLS.md`를 참고하십시오.

본 문서는 **현재 저장소에 구현된 기능**만 기준으로 프로젝트의 범위와 동작 방식을 정리한다.

## 1. Current Product Flow

1. **Input**: CLI로 캠페인 목표/톤/페르소나 수 등을 전달한다.
2. **Simulation**:
   - **Hero**: Playwright 브라우저로 Pixelfed 피드를 관찰하고 행동한다.
   - **Crowd**: 텍스트 기반 LLM 판단으로 다수 반응을 시뮬레이션한다.
3. **Output**:
   - `shared/simulation/{simulationId}.json`에 상태/결과 기록
   - `agent/outputs/{runId}/{agentId}/actions.jsonl`에 에이전트별 액션 로그 기록
4. **Evaluation**:
   - 기대 데이터 대비 like/comment 유사도 평가
   - 결과: `shared/evaluation/results/{evaluationId}.json`
   - 상세: `docs/EVALUATION.md`

---

## 2. Implemented Components

### 2.1 Agent (`agent/`)
- CLI 실행 (`agent/cli.py`)
- Hero + Crowd 하이브리드 구조
- 액션 로그 JSON + JSONL 저장

### 2.2 Local SNS (`sns/`)
- Pixelfed Docker 환경
- 시드 스크립트: `sns/seed_hackathon.php`

### 2.3 Shared Contract (`shared/`)
- 시뮬레이션 결과 스키마: `shared/simulation-schema.json`

### 2.4 Scripts (`scripts/`)
- SNS 초기화 자동화: `scripts/setup_sns.sh`

### 2.5 Evaluation
- 평가 CLI: `agent/cli.py evaluate`
- 문서: `docs/EVALUATION.md`

> **Not Included**: Dashboard UI, Instagram Crawler는 이 저장소에 포함되어 있지 않다.

---

## 3. Data Contract & Output

- **Simulation Status**: `shared/simulation/{simulationId}.json`
- **Action Logs (per agent)**:
  - JSON 파일: `agent/outputs/{runId}/{agentId}/{sequence}_{action}.json`
  - JSONL 스트림: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- **Evaluation Results**: `shared/evaluation/results/{evaluationId}.json`
- **Schemas**:
  - `shared/simulation-schema.json`
  - `agent/outputs/action-schema.json`
  - `shared/evaluation/expected-schema.json`
  - `shared/evaluation/result-schema.json`

---

## 4. Directory Map

```
.
├── agent/              # Python-based Simulation Engine (Hero + Crowd)
├── docs/               # Documentation (Current Implementation)
├── scripts/            # Setup helpers (SNS)
├── shared/             # Simulation contract + outputs
└── sns/                # Pixelfed environment + seed
```

---

## 5. Hackathon Constraints (Applied)

- **Local-first**: 모든 구성요소는 로컬에서 실행
- **Speed over Security**: 약한 비밀번호/권한 허용
- **File-based IPC**: 프로세스 간 통신은 파일로 공유
