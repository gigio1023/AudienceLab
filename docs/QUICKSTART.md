# Standard Operating Procedure: Quick Start

본 문서는 **Persona-Driven Multi-Agent Simulation System**의 신규 개발자 온보딩 및 로컬 환경 구축을 위한 **표준 운영 절차(SOP)**이다. 5분 이내에 전체 시스템을 Cold Start 상태에서 시연 가능한 상태(Ready-to-Demo)로 만드는 것을 목표로 한다.

## 0. Prerequisite Check (사전 환경 검증)

시스템 기동 전 다음 소프트웨어 스택의 버전을 확인한다.

| Software | Required Version | Verification Command |
|----------|------------------|----------------------|
| **Docker** | Desktop 4.0+ | `docker info` |
| **Node.js** | LTS (v18+) | `node -v` |
| **Python** | 3.12+ | `python3 --version` |
| **uv** | Latest | `uv --version` (If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`) |

---

## 1. System Initialization (시스템 초기화)

### Step 1.1: Repository Preparation
서브모듈 의존성을 포함하여 저장소를 초기화한다. `react-bits` 및 `shadcn-ui` 컴포넌트 라이브러리가 포함된다.

```bash
git submodule update --init --recursive
```

### Step 1.2: Simulation Environment Boot (Local SNS)
Docker Compose를 사용하여 격리된 Pixelfed 인스턴스를 기동한다.

```bash
cd sns/pixelfed
# Configuration Injection (Production-like local config)
cp ../.env.fixture .env

# Container Orchestration
docker-compose up -d --force-recreate
```

> **Wait Check**: 컨테이너 3개(`pixelfed-app`, `pixelfed-db`, `pixelfed-redis`)가 모두 `Running` 상태가 될 때까지 약 30초 대기한다. (`docker ps`로 확인)

### Step 1.3: Data Seeding (World State Setting)
빈 데이터베이스에 인플루언서, 에이전트, 관리자 계정을 주입한다.

```bash
# Seed Execution Pipe
cat seed_hackathon.php | docker exec -i pixelfed-app php artisan tinker
```

---

## 2. Agent Runtime Setup (에이전트 런타임 설정)

브라우저 자동화 및 VLM 추론을 위한 Python 환경을 구성한다.

### Step 2.1: Dependency Hydration
`uv` 패키지 매니저를 통해 가상환경을 생성하고 의존성을 설치한다.

```bash
cd agent
cp .env.example .env
uv sync
```

### Step 2.2: Browser Binary Install
Headless Browser 바이너리를 설치한다.

```bash
uv run playwright install chromium
```

---

## 3. Command Center Launch (UI 기동)

React 기반의 대시보드 서버를 실행한다.

```bash
cd search-dashboard
npm install
npm run dev
```
*   **Result**: `http://localhost:5173` 접속 가능 확인.

---

## 4. Verification Checklist (기동 검증)

모든 단계 완료 후 다음 체크리스트를 수행하여 시스템 정상 가동을 확인한다.

1.  **SNS Connectivity**:
    *   `curl -k https://localhost:8092` -> `200 OK` (또는 리다이렉트) 응답 확인.
    *   브라우저 로그인: `agent1` / `password` 성공 확인.
2.  **Agent Logic**:
    *   `cd agent && uv run test_single_agent.py` 실행 시 스크린샷 캡처 성공 확인.
3.  **Dashboard Integration**:
    *   대시보드에서 "Start Simulation" 클릭 시 `agent/src/server.py` 로그에 프로세스 생성 메시지 확인.

---

> **Note**: 기동 중 오류 발생 시 [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)의 Incident Response Guide를 참조한다.
