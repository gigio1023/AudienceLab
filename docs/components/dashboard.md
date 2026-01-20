# Dashboard (Current Status)

본 저장소에는 **대시보드 UI가 포함되어 있지 않다**. 현재 구현된 데이터 소스는 아래 파일 기반 출력이며, 향후 UI는 이를 읽어 시각화하면 된다.

## 1. Data Sources

- **Simulation Status**: `shared/simulation/{simulationId}.json`
- **Action Logs**: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- **Evaluation Results**: `shared/evaluation/results/{evaluationId}.json`
- **Schema**:
  - `shared/simulation-schema.json`
  - `agent/outputs/action-schema.json`
  - `shared/evaluation/result-schema.json`

## 2. Expected Consumer Behavior (Future UI)

- `shared/simulation/*.json` 파일을 폴링하여 진행률과 결과 렌더링
- 필요 시 `agent/outputs/*/actions.jsonl`로 상세 액션 타임라인 구성

> CLI 실행이 유일한 트리거 방식이며, HTTP Bridge는 현재 구현되어 있지 않다.
