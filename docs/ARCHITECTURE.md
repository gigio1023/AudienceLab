# System Architecture Specification

본 문서는 **Persona-Driven Multi-Agent Simulation System**의 기술적 아키텍처를 정의한다. 시스템의 컴포넌트 간 상호작용, 데이터 흐름, 그리고 핵심 기술 결정 사항(Decision Records)을 포함한다.

## 1. High-Level Architecture (C4 Level 2: Container Diagram)

전체 시스템은 크게 **Data Pipeline**, **Simulation Runtime**, **User Interface** 세 영역으로 구분된다.

```mermaid
graph TD
    subgraph "Data Pipeline Layer"
        Crawler[Instagram Crawler] -->|Raw Data| DB[(SQLite / Files)]
        DB -->|Persona Generation| Assets[Persona Templates]
    end

    subgraph "Simulation Runtime Layer"
        Orchestrator[Agent Orchestrator] -->|Spawn| Agents[Browsing Agents]
        Agents -->|Interact| SNSServer[Local SNS (Pixelfed)]
        SNSServer -->|Store| SNSDB[(MySQL)]
    end

    subgraph "User Interface Layer"
        Dashboard[React Dashboard] -->|Command| Bridge[API Bridge]
        Bridge -->|Trigger| Orchestrator
        Dashboard -->|Poll Results| SharedStorage[Shared File System]
    end

    Assets --> Orchestrator
    Agents -->|Logs| SharedStorage
```

### 1.1 Key Components
1.  **Dashboard (UI)**: 사용자의 접점. 시뮬레이션 설정(Campaign Config)을 생성하고 결과를 시각화한다.
2.  **API Bridge**: Python `FastAPI` 기반의 경량 서버. UI의 요청을 받아 무거운 시뮬레이션 프로세스를 백그라운드에서 실행시킨다.
3.  **Agent Engine**: 핵심 로직. `Runner`가 다수의 `Agent` 인스턴스를 관리하며, 각 에이전트는 독립된 `Headless Browser`를 제어한다.
4.  **Local SNS**: 시뮬레이션의 무대. 외부와 격리된 `Pixelfed` 인스턴스로, 에이전트들의 모든 활동을 받아낸다.

## 2. Data Flow Architecture

### 2.1 The Simulation Loop (End-to-End Flow)
시뮬레이션은 단방향 데이터 흐름을 따른다.

1.  **Config**: Dashboard에서 `SimulationConfig` 생성 (Goal, Budget, Target Persona).
2.  **Dispatch**: API Bridge가 Config를 JSON으로 저장하고 `main_runner.py` 실행.
3.  **Bootstrap**: Runner가 Config를 읽고, 적절한 `Persona Templates`를 로드하여 Agent 인스턴스 초기화.
4.  **Execution (O-D-A Loop)**:
    *   **Observe**: Agent가 Browser 스크린샷 캡처.
    *   **Decide**: VLM(Vision Language Model)이 이미지와 페르소나 정보를 보고 Action 결정.
    *   **Act**: Playwright가 실제 클릭/입력 수행 -> Local SNS 상태 변경.
    *   **Log**: 수행된 Action과 결과를 `AgentLog` 객체로 메모리에 적재.
5.  **Aggregation**: 시뮬레이션 종료 시 Runner가 모든 로그를 취합하여 `SimulationResult` JSON 생성 -> `metrics` 계산.
6.  **Reporting**: Dashboard가 완료된 JSON을 읽어 최종 리포트 렌더링.

### 2.2 IPC (Inter-Process Communication) Strategy
복잡한 Message Queue(RabbitMQ 등) 도입을 지양하고, Hackathon Scope과 로컬 환경에 최적화된 **File-based State Sharing** 패턴을 채택했다.

*   **Protocol**: JSON Schema Strict Validation (`shared/simulation-schema.json`)
*   **Concurrency Control**: 단일 Writer (Runner), 다중 Reader (Dashboard) 구조로 Lock 불필요.
*   **Paths**:
    *   Configs: `shared/simulation/{sim_id}.json` (Initial)
    *   Results: `shared/simulation/{sim_id}.json` (Updated with results)

## 3. Technology Stack & Decision Records

### 3.1 VLM Agent Framework
*   **Decision**: Custom Implementation over LangChain/AutoGPT.
*   **Reasoning**:
    *   **Control**: 시뮬레이션의 정밀한 제어(스크린샷 시점, 액션 스페이스 제한)를 위해 직접 구현이 유리.
    *   **Latency**: 불필요한 추상화 레이어를 제거하여 LLM API 호출 오버헤드 최소화.
    *   **Vision-First**: 텍스트보다 시각 정보(Screenshot)가 SNS 상호작용에 더 중요함을 반영.

### 3.2 Simulation Environment
*   **Decision**: Self-hosted Pixelfed (Docker) over Real Instagram.
*   **Reasoning**:
    *   **Risk**: 실제 인스타그램 대상 시뮬레이션은 계정 밴(Ban) 및 법적 리스크 존재.
    *   **Cost**: 실제 플랫폼 API/Action 비용 문제 없음.
    *   **Observability**: DB 직접 접근을 통해 에이전트의 모든 활동 검증 가능.

### 3.3 Persona Modeling
*   **Decision**: Template-based Generation over Real-time Cloning.
*   **Reasoning**:
    *   크롤링된 데이터에서 "행동 패턴(Interests, Tone)"만 추출하여 템플릿화(Template)하고, 런타임에 이를 인스턴스화(Instantiate)하는 방식이 다양성 확보에 유리.

## 4. Security & Network Model
*   **Localhost Isolation**: 모든 컴포넌트는 `localhost` 루프백 인터페이스 내에서만 통신한다.
*   **HTTPS (Self-Signed)**: Pixelfed의 ActivityPub 호환성 및 브라우저 보안 정책 준수를 위해 로컬 HTTPS 필수 적용 (`:8092`).
*   **CORS**: Dashboard(Port 5173)와 Bridge Server(Port 8000) 간의 통신을 위해 `CORSMiddleware` 적용.

## 5. Scalability Considerations
현재 아키텍처는 **Vertical Scaling** (로컬 머신 리소스 내)을 전제로 한다.
*   **BottleNeck**: Chrome Instance Memory Usage & LLM API Rate Limits.
*   **Expansion Path**: 향후 Cloud 기반의 Kubernetes 배포 시, `Runner`를 분산 워커 패턴(Celery 등)으로 전환하여 수평 확장 가능.
