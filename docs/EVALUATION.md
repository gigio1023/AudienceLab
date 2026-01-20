# Agent Evaluation (Like/Comment Similarity)

본 문서는 **에이전트 액션 로그**를 기반으로 실제 평가 데이터(ground truth)와 얼마나 유사한지 측정하는 방법을 정의한다.

## 1. Goal

- **관심 지표**: `like`, `comment` 반응의 유사도
- **입력**: 평가 데이터(기대값), 실제 실행 액션 로그(JSONL)
- **출력**: 유사도 점수 + 오차 메트릭

---

## 2. Inputs

### 2.1 Expected Data (Ground Truth)
- 파일: `shared/evaluation/expected.example.json`
- 스키마: `shared/evaluation/expected-schema.json`

필수 필드:
- `expected.likeCount` 또는 `expected.commentCount` 또는 `expected.likeRate` 또는 `expected.commentRate`

옵션:
- `perPersona`: 페르소나별 기대값
- `weights`: 메트릭 가중치

### 2.2 Actual Data (Agent Actions)
- JSONL: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- `action.type == "act"` AND `action.status == "ok"`만 집계
- `result.liked`, `result.commented` 값을 사용

---

## 3. Actual Metric Extraction

집계되는 실제 지표:

- `totalActs` : 전체 act 횟수
- `likeCount` : liked == true 횟수
- `commentCount` : commented == true 횟수
- `likeRate` : likeCount / totalActs
- `commentRate` : commentCount / totalActs
- `engagementCount` : likeCount + commentCount

---

## 4. Similarity Metrics

### 4.1 Count Similarity

```text
similarity = max(0, 1 - |actual - expected| / max(expected, 1))
```

- 기대값이 0일 때 분모는 1로 고정
- 0~1 범위로 클램프

### 4.2 Rate Similarity

```text
similarity = max(0, 1 - |actualRate - expectedRate|)
```

- Rate는 0~1 범위
- 절대 차이를 직접 유사도로 변환

### 4.3 Overall Similarity

```text
overallSimilarity = sum(metricSimilarity * weight) / sum(weights)
```

기본 가중치:
- `likeCount`: 0.5
- `commentCount`: 0.5
- `likeRate`: 0.0
- `commentRate`: 0.0

---

## 5. CLI Usage

```bash
cd agent
uv run python cli.py evaluate \
  --expected ../shared/evaluation/expected.example.json \
  --run-id <runId>
```

옵션:
- `--run-id`: `agent/outputs/{runId}` 사용
- `--run-dir`: 실행 디렉터리를 직접 지정
- `--simulation-file`: `shared/simulation/{simulationId}.json`에서 runId 추출
- `--output`: 결과 JSON 경로 지정
- `--print-json`: 결과 JSON 전체 출력

`--run-id`/`--run-dir`/`--simulation-file`이 없으면 최신 실행 디렉터리를 자동 선택한다.
`runId`는 `agent/outputs/` 아래 생성된 디렉터리 이름으로 확인할 수 있다.

---

## 6. Evaluation Output

기본 경로:
- `shared/evaluation/results/{evaluationId}.json`

스키마:
- `shared/evaluation/result-schema.json`

출력 예시 (요약):
```json
{
  "schemaVersion": "1.0",
  "evaluationId": "example-eval",
  "metrics": {
    "likeCount": {
      "expected": 30,
      "actual": 27,
      "absError": 3,
      "relativeError": 0.1,
      "similarity": 0.9
    },
    "commentCount": {
      "expected": 10,
      "actual": 12,
      "absError": 2,
      "relativeError": 0.2,
      "similarity": 0.8
    },
    "overallSimilarity": 0.85
  }
}
```

---

## 7. Interpretation Guidelines

- **0.9+**: 기대값과 매우 유사
- **0.7~0.9**: 근접하지만 편차 존재
- **0.5~0.7**: 모델/페르소나 튜닝 필요
- **< 0.5**: 기대값과 큰 괴리

> 평가 데이터는 실제 캠페인/크롤링 결과에서 추출한 카운트 또는 비율로 구성한다.
