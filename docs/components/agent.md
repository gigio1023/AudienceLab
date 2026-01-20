# Agent Simulation Engine (Current Implementation)

본 문서는 `agent/` 디렉토리에 구현된 **CLI 기반 시뮬레이션 엔진**의 실제 동작을 설명한다.

## 1. Overview

- **Entry**: `agent/cli.py`
- **Core**: `agent/runner.py`
- **Persona Source**: `agent/personas.json` (optional override 가능)
- **Environment**: `agent/.env`
- **Hero Model**: `computer-use-preview` via Responses API (computer actions)
- **Crowd Model**: `gpt-5-mini` via Responses API (text decisions)

## 2. Execution Model (Hero + Crowd)

### 2.1 Hero Agent
- Playwright 브라우저로 Pixelfed 로그인
- 피드 스크린샷 캡처 → Computer Use 모델이 좌표 액션 생성 → 실제 클릭/스크롤
- `--headed`로 UI 디버깅 가능

### 2.2 Crowd Agents
- 브라우저 없이 텍스트 기반 LLM 판단
- `postContext`를 입력으로 사용
- `--max-concurrency`로 병렬도 제어

> Hero는 `computer-use-preview` 모델을 Responses API로 호출한다.
> Crowd는 `gpt-5-mini` 모델을 Responses API로 호출한다.

---

## 3. CLI Interface

```bash
uv run python cli.py run \
  --goal "Hybrid SNS simulation run" \
  --crowd-count 8
```

주요 옵션:
- `--dry-run`: LLM 호출 없이 실행 (fallback decision)
- `--no-hero`: Hero 비활성화
- `--hero-persona`: Hero 페르소나 ID 지정
- `--persona-file`: 페르소나 JSON 경로 지정
- `--headed`: 브라우저 UI 표시
- `--no-screenshots`: Hero 스크린샷 저장 비활성화
- `--post-context`: Crowd가 사용할 텍스트 컨텍스트 지정
- `--max-concurrency`: Crowd 병렬도 제한

---

## 4. Environment (.env)

`.env.sample`을 복사해 사용한다.

```bash
cp agent/.env.sample agent/.env
```

`.env` 예시:
```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
OPENAI_REASONING_EFFORT=low
OPENAI_COMPUTER_USE_MODEL=computer-use-preview
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_AUTO_ACK_SAFETY_CHECKS=false
AGENT_LOG_LEVEL=INFO
SNS_URL=https://localhost:8092
SNS_EMAIL=agent1@local.dev
SNS_PASSWORD=password
```

- `OPENAI_MODEL`: Crowd 판단 모델 (텍스트 기반)
- `OPENAI_COMPUTER_USE_MODEL`: Hero용 CUA 모델 (컴퓨터 액션)
- `OPENAI_REASONING_EFFORT`: Crowd 모델 추론 강도 (low 권장)
- `OPENAI_AUTO_ACK_SAFETY_CHECKS`: CUA 안전 경고 자동 승인 여부 (기본 false)
- `AGENT_LOG_LEVEL`: Loguru 로그 레벨 (DEBUG/INFO/WARNING/ERROR)
- `SNS_EMAIL`: seed 계정 이메일 중 하나를 지정하면 해당 계정으로 로그인

---

## 5. Persona Schema (`agent/personas.json`)

```json
{
  "id": "string",
  "name": "string",
  "interests": ["string"],
  "tone": "string",
  "reaction_bias": "positive | neutral | negative"
}
```

---

## 6. Outputs

### 6.1 Simulation Status
- Path: `shared/simulation/{simulationId}.json`
- Schema: `shared/simulation-schema.json`

### 6.2 Action Logs (Per Agent)
- JSONL: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- JSON: `agent/outputs/{runId}/{agentId}/{sequence}_{action}.json`
- Schema: `agent/outputs/action-schema.json`

Action log 예시:
```json
{
  "schemaVersion": "1.0",
  "runId": "uuid",
  "simulationId": "uuid",
  "sequence": 1,
  "timestamp": "2025-01-01T00:00:00+00:00",
  "agent": {
    "id": "hero-1",
    "type": "hero",
    "personaId": "vegan-mom",
    "personaName": "Vegan Mom"
  },
  "action": {
    "type": "observe",
    "status": "ok",
    "input": {"url": "https://localhost:8092/i/web"},
    "output": {"captured": true}
  },
  "artifacts": [{"type": "screenshot", "path": "agent/outputs/.../observe.png"}]
}
```

---

## 7. O-D-A Loop (Simplified)

1. **Observe**: 화면 또는 `postContext` 관찰
2. **Decide**: LLM이 `like/comment/follow/sentiment` 결정
3. **Act**: Hero는 UI 행동, Crowd는 headless 기록

---

## 8. Runtime Notes

- `--dry-run`은 테스트/데모용으로 안정적
- `OPENAI_API_KEY`가 없으면 자동으로 fallback decision 사용
- `agentLogs`는 per-action JSON 파일 경로(`{sequence}_{action}.json`)를 참조
- JSONL은 에이전트별 스트림으로 별도 저장

---

## 9. Evaluation

```bash
uv run python cli.py evaluate \
  --expected ../shared/evaluation/expected.example.json \
  --run-id <runId>
```

평가 규칙과 스키마는 `docs/EVALUATION.md` 참고.
