# Quick Start (Current Implementation)

본 문서는 **현재 구현된 구성요소만** 대상으로 5분 내 로컬 시뮬레이션을 실행하는 방법을 안내한다.

## 0. Prerequisites

| Software | Required Version | Verification Command |
|----------|------------------|----------------------|
| **Docker** | Desktop 4.0+ | `docker info` |
| **Python** | 3.12+ | `python3 --version` |
| **uv** | Latest | `uv --version` |

---

## 1. Local SNS (Pixelfed) Setup

### Option A: Script (Recommended)

```bash
./scripts/setup_sns.sh
```

### Option B: Manual

```bash
cd sns/pixelfed
cp .env.docker.example .env

docker-compose up -d --force-recreate

cat ../seed_hackathon.php | docker-compose exec -T pixelfed php artisan tinker
```

---

## 2. Agent Runtime Setup

```bash
cd agent
cp .env.sample .env
# .env에 OPENAI_API_KEY 설정 (선택: OPENAI_BASE_URL)
# SNS 설정이 다르면 SNS_URL/SNS_EMAIL/SNS_PASSWORD도 수정
# 기본 모델: crowd=gpt-5-mini, hero=computer-use-preview
# 로그 레벨 조정: AGENT_LOG_LEVEL=DEBUG (선택)

uv sync
uv run playwright install chromium
```

---

## 3. Smoke Test (Dry Run)

```bash
cd agent
uv run python cli.py smoke-test --verbose
```

> `--dry-run` 기반 실행이므로 OPENAI_API_KEY 없이도 동작한다.

---

## 4. Run a Simulation

### Hybrid (Hero + Crowd)

```bash
uv run python cli.py run --crowd-count 5
```

### Crowd Only (No Browser)

```bash
uv run python cli.py run --no-hero --crowd-count 8
```

### Debug with Visible Browser

```bash
uv run python cli.py run --headed --crowd-count 2
```

---

## 5. Verify Outputs

- Simulation file: `shared/simulation/{simulationId}.json`
- Action logs: `agent/outputs/{runId}/{agentId}/actions.jsonl`

---

## 6. Evaluate Like/Comment Similarity

```bash
cd agent
uv run python cli.py evaluate \
  --expected ../shared/evaluation/expected.example.json \
  --run-id <runId>
```

`runId`는 `agent/outputs/` 아래 폴더명으로 확인 가능.

> 자세한 평가 규칙은 `docs/EVALUATION.md` 참고.

> UI/대시보드는 이 저장소에 포함되어 있지 않다.
