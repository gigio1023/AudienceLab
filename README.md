# 팀명

AudienceLab

## 데모

(데모 URL 또는 영상 링크)

## 문제 정의

- 기존 솔루션들은 인플루언서 검색, 분석을 지원하나 그 깊이가 한정적입니다. 검색은 카테고리나 팔로워 수 등 메타데이터 기반이고, 분석은 협업 브랜드 히스토리 정도를 알려줍니다. 저희는 인플루언서의 힘이 팔로워에서 온다고 생각하고, 팔로워에 대한 인사이트를 고객에게 전달함으로써 더 적합한 인플루언서를 선택할 수 있도록 도울 것입니다.

## 솔루션

- 문제 해결을 위해 인플루언서 팔로워 별로 페스소나를 구축할 것입니다. ~이 페르소나를 활용하면 LLM이나 벡터 검색으로 인플루언서를 분석할 수 있습니다.~(구현 안됨) 또한 페르소나로 AI Agent를 구축하면, 가상 마케팅을 집행했을 때 가상 팔로워가 어떻게 행동하는지 multi-agent simulation이 가능합니다. 이는 ML 예측 모델이 pClick, pCVR 등을 알려주는 것을 넘어선 고맥락의 정보입니다. 시뮬레이션 후 engagement 지표(e.g. like, comment 갯수)를 측정하고, 그것을 인플루언서의 전체 포스팅 engagement와 비교하여 마케팅 성과를 측정할 수 있습니다.

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

# 3) Start Dashboard (Terminal 2)
cd ../search-dashboard
npm install
npm run dev

# 4) Run Simulation (Terminal 3)
cd ../agent
uv sync
uv run python cli.py run --crowd-count 8 --max-concurrency 4

# 5) (Optional) Deploy logs to dashboard feed
python ../scripts/deploy_dashboard_data.py

# 6) Run Evaluation
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
