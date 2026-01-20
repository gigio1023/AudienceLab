# 팀명

AudienceLab

## 데모


### Dashboard
![](images/dash01.png)
![](images/dash02.png)

### Persona-based User Agent Swarm for SNS Simulation
![](images/agent.png)

### SNS created by Vibe Coding
![](images/sns.png)

### Evaluation: Engagement Score + LLM-as-a-judge Quality Score
![](images/eval.png)

## 문제 정의

인플루언서 마케팅 성과 예측의 어려움



- 기존 솔루션들은 인플루언서 검색, 분석을 지원하나 그 깊이가 한정적입니다. 검색은 카테고리나 팔로워 수 등 메타데이터 기반이고, 분석은 협업 브랜드 히스토리 정도를 알려줍니다.
- 실제 마케팅 성과 지표(ROI, 구매 전환, CTR 등)는 캠페인이 끝나기 전까지 측정이 어렵고, 데이터가 없으면 사전 예측도 불가능합니다. 결국 "가상 캠페인"을 해보지 않으면 인플루언서의 실제 적합성을 판단하기 어렵습니다.

## 솔루션

<Multi agent 기반 sns simuation>

### 1) 페르소나 기반 스웜
- 문제 해결을 위해 인플루언서 팔로워 별로 페르소나를 구축합니다. ~이 페르소나를 활용하면 LLM이나 벡터 검색으로 인플루언서를 분석할 수 있습니다.~(구현 안됨)
- 페르소나 기반 AI Agent가 로컬 SNS에서 활동하는 **user persona 기반 swarm** 구조로 구성되어 있으며, 각 에이전트는 로컬 Playwright로 페이지를 탐색하고 OpenAI가 행동 결정을 내립니다.

### 2) 참여도 기반 성과 추정
- 성과 지표는 **실제 데이터 기반의 engagement proxy(Like/Comment)**로 합성합니다. 이 값은 engagement rate의 베이스라인이며, 인플루언서의 과거 게시물 engagement와 비교해 상대적 성과를 봅니다.

### 3) 평가 자동화 (eval-agent)
- **실제 지표 해석(ROI/전환 등)에 대한 평가는 `eval-agent`가 담당**합니다. 시뮬레이션 로그(JSONL)를 수집해 참여율과 액션 분포를 정량화하고, LLM으로 댓글 품질을 평가해 종합 등급을 산출합니다.

## 조건 충족 여부

- [x] OpenAI API 사용
- [x] 멀티에이전트 구현
- [ ] 실행 가능한 데모

## 아키텍처

```
Persona/Seed Data (sns-vibe/seeds.json)
        |
        v
agent/cli.py
  -> agent/runner.py (Python + Playwright + OpenAI)
        |                         |
        |                         v
        |                   OpenAI API
        v
Local SNS (sns-vibe: SvelteKit + SQLite)
        |
        v
Outputs
  - shared/simulation/{simulationId}.json
  - agent/outputs/{runId}/{agentId}/actions.jsonl
  - (optional) search-dashboard/public/simulation/*.jsonl
        |                              |
        |                              v
        |                        Search Dashboard (React/Vite)
        v
eval-agent -> shared/evaluation/results/{evaluationId}.json
```

## 기술 스택

- Agent/Simulation: Python 3.12+, OpenAI API, Playwright, uv, Jinja2, Loguru
- Local SNS: SvelteKit + TypeScript, TailwindCSS, SQLite (better-sqlite3), Docker
- Dashboard: React 18 + TypeScript, Vite, motion
- Evaluation: Python, pandas, pydantic, OpenAI API
- Contracts: JSON Schema (shared/)

## 설치 및 실행

```bash
# 1) Configure agent env (only required .env in the repo)
cp agent/.env.sample agent/.env
# Set:
# OPENAI_API_KEY=...
# SNS_URL=http://localhost:51737
# (Optional for sns-vibe login) SNS_USERNAME=agent1

# 2) Start SNS (Terminal 1)
cd sns-vibe
npm install
bash scripts/reset-db.sh
npm run dev
# 실행만 해두면 됩니다. 추가 액션은 필요 없습니다.

# 3) Start Dashboard (Terminal 2)
cd ../search-dashboard
npm install
npm run dev
# 실행만 해두면 됩니다. 추가 액션은 필요 없습니다.

# 4) Run Simulation (Terminal 3)
cd ../agent
uv sync
uv run python local_agent.py
# 실행 후 진행이 되도록 잠시 기다리면 됩니다.
# 실시간 과정은 Start Dashboard에서 띄운 http://localhost:51730/ 에서
# 멀티 에이전트 스웜 결과 + SNS 활동을 모니터링할 수 있습니다.

# 5) (Optional) Deploy logs to dashboard feed
python ../scripts/deploy_dashboard_data.py

# 6) Run Evaluation
# 시뮬레이션이 적당히 진행되면 Run Simulation 콘솔을 닫고 평가를 돌리세요.
cd ../eval-agent
uv sync
uv run python evaluate.py
```

## 향후 계획 (Optional)

- 인플루언서 검색을 지원해서 검색->가상마케팅 시나리오를 지원할 계획입니다.

## 팀원

| 이름 | 역할 |
| ---- | ---- |
| 박성호 | 시뮬레이션, sns 개발 |
| 이승현 | 크롤링 개발 |
|      |      |
