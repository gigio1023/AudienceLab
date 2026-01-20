# Eval Agent (평가 에이전트)

이 디렉토리는 AudienceLab 에이전트들의 활동을 평가하는 모듈을 담고 있습니다. 정량적 지표 분석과 LLM 기반의 정성적 평가를 통해 에이전트의 행동 패턴과 품질을 종합적으로 분석합니다.

## 📌 개요

Eval Agent는 **user persona 기반 swarm** 에이전트의 활동 로그(`search-dashboard/public/simulation/*.jsonl`)를 수집 및 분석합니다. 단순한 수치 측정을 넘어, 해당 수치가 **좋은지 나쁜지(Verdict)**를 판단할 수 있는 등급 시스템을 포함하고 있습니다.

## 📊 평가 지표 및 방법 (Evaluation Metrics & Methods)

### 1. 종합 등급 (Performance Verdict) - 솔루션
측정된 수치를 바탕으로 시스템이 자동으로 등급을 매겨 "좋음/나쁨"을 직관적으로 판단합니다.

| 지표 (Metric) | 기준 (Criteria) | 등급 (Grade) | 의미 |
| :--- | :--- | :--- | :--- |
| **Marketing Engagement Rate** | 50% 이상 | **High (적극적)** | 마케팅 포스트에 대해 매우 활발하게 상호작용함 |
| (참여율) | 20% ~ 49% | **Medium (보통)** | 적절한 수준의 활동성 |
| | 20% 미만 | **Low (소극적)** | 활동이 저조하여 개선이 필요함 |
| **Quality Score** | 4.5점 이상 | **Excellent (최우수)** | 페르소나 완벽 일치, 문맥 파악 뛰어남 |
| (LLM 평가 평균) | 4.0점 ~ 4.4점 | **Good (우수)** | 준수한 품질, 큰 문제 없음 |
| | 3.0점 ~ 3.9점 | **Fair (보통)** | 무난하나 디테일 부족 가능성 있음 |
| | 3.0점 미만 | **Poor (미흡)** | 엉뚱한 소리를 하거나 페르소나 붕괴 |

### 2. 정량적 지표 (Quantitative Metrics) - 솔루션
- **Marketing Engagement Rate**: $$ \frac{\text{마케팅 포스트에 대한 성공 상호작용 수 (Like/Comment)}}{\text{전체 스텝 수}} $$
- **Action Distribution**: 액션 유형별 성공/실패 분포.

### 3. 정성적 분석 (Qualitative Analysis) - 솔루션
`gpt-5-mini`를 사용하여 **마케팅 포스트에 달린 댓글**의 품질을 3가지 축으로 평가합니다:
1.  **Relevance (관련성)**: 문맥에 맞는가?
2.  **Tone (어조)**: 페르소나에 어울리는가?
3.  **Consistency (일관성)**: 의도와 행동이 일치하는가?

## 🛠 구현 상세

- `evaluate.py`: 로그 파싱 -> 메트릭 계산 -> **등급 판정(Grading)** -> CLI 리포트 출력
- 기준치는 `evaluate.py` 내부에 하드코딩 되어 있으며, 프로젝트 성격에 따라 조정 가능합니다.

## 🚀 실행 방법

```bash
cd eval-agent
cp .env.sample .env
# OPENAI_API_KEY를 설정한 뒤 실행
uv sync
uv run python evaluate.py
```

실행 후 CLI 출력에서 **"Performance Verdict (종합 평가)"** 섹션을 확인합니다.
