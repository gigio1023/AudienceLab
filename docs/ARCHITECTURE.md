# System Architecture Specification (Current Implementation)

본 문서는 **현재 저장소에 실제로 구현된 컴포넌트**만 기준으로 시스템 아키텍처를 정의한다. 현재 구현은 **Local SNS + Agent Runner + Shared File Contract**에 집중되어 있으며, UI나 크롤러는 포함되어 있지 않다.

## 1. High-Level Architecture

```mermaid
graph TD
    CLI[Agent CLI] --> Runner[agent/runner.py]
    Runner -->|Browser (Hero, computer-use-preview)| Pixelfed[Local SNS (Pixelfed)]
    Runner -->|Headless (Crowd, gpt-5-mini)| LLM[OpenAI API]
    Runner --> Shared[shared/simulation/*.json]
    Runner --> Outputs[agent/outputs/*/actions.jsonl]
    EvalCLI[Agent CLI evaluate] --> Evaluator[agent/evaluator.py]
    Evaluator --> Outputs
    Evaluator --> EvalOut[shared/evaluation/results/*.json]
    Consumer[External Consumer / Future UI] --> Shared
    Consumer --> Outputs
    Consumer --> EvalOut
```

### 1.1 Implemented Components
1. **Agent Runner (`agent/`)**
   - CLI 기반 실행: `agent/cli.py`
   - Hero + Crowd 하이브리드 구조
   - 결과 파일: `shared/simulation/*.json`, `agent/outputs/*`
2. **Local SNS (`sns/`)**
   - Pixelfed Docker 환경
   - 시드 스크립트: `sns/seed_hackathon.php`
3. **Shared Contract (`shared/`)**
   - 시뮬레이션 결과 스키마: `shared/simulation-schema.json`
4. **Automation Script (`scripts/`)**
   - SNS 초기화: `scripts/setup_sns.sh`
5. **Evaluation (`agent/evaluator.py`)**
   - 액션 로그 기반 평가
   - 출력: `shared/evaluation/results/*.json`

> **Not Included**: 대시보드 UI, 크롤러 컴포넌트는 이 저장소에 포함되어 있지 않다.

---

## 2. Runtime Data Flow

1. **CLI Trigger**
   - `uv run python agent/cli.py run ...` 실행
2. **Execution**
   - Hero: Playwright 브라우저로 Pixelfed 로그인/피드 관찰/행동
   - Crowd: 텍스트 기반 LLM 판단으로 대규모 반응 시뮬레이션
3. **Outputs**
   - 시뮬레이션 상태/결과: `shared/simulation/{simulationId}.json`
   - 에이전트 액션 로그: `agent/outputs/{runId}/{agentId}/actions.jsonl`
4. **Evaluation**
   - 평가 실행: `uv run python agent/cli.py evaluate ...`
   - 평가 결과: `shared/evaluation/results/{evaluationId}.json`

---

## 3. IPC (File-based Contract)

복잡한 메시지 브로커 없이 파일 기반으로 느슨하게 결합한다.

- **Single Writer**: Agent Runner
- **Multi Reader**: 외부 분석 도구 또는 향후 UI
- **Schema**: `shared/simulation-schema.json` + `agent/outputs/action-schema.json` + `shared/evaluation/result-schema.json`

---

## 4. Security & Local Constraints

- 모든 실행은 로컬 환경 기준
- Pixelfed는 Self-Signed HTTPS 사용 (`https://localhost:8092`)
- Playwright는 `ignore_https_errors=True`로 실행

---

## 5. Scalability Notes

- Crowd는 headless 텍스트 판단으로 병렬 확장
- Hero는 단일 브라우저 세션으로 UX 검증
- 병렬도는 `--max-concurrency`로 제어
