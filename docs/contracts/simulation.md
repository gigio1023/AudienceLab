# Simulation Integration Protocol

본 문서는 **Simulation Engine (Agent)**과 **Command Center (Dashboard)** 간의 데이터 교환 규약(Interface Contract)을 정의한다. 두 시스템은 직접적인 동기 통신을 최소화하고, **File-based State Replication** 패턴을 통해 느슨하게 결합(Loosely Coupled)된다.

## 1. Protocol Architecture

### 1.1 Communication Channel
*   **Method**: Asynchronous File Polling
*   **Shared Resource**: `shared/simulation/{simulationId}.json`
*   **Access Pattern**:
    *   **Writer**: Simulation Runner (Agent Process) - *Single Writer Principle*
    *   **Reader**: Dashboard Client (React App) - *Multi Reader*

### 1.2 Lifecycle States
시뮬레이션 객체는 정의된 상태 머신(Finite State Machine)에 따라 전이된다.

| State | Enum Value | Description | Transition Trigger |
|-------|------------|-------------|-------------------|
| **Initialized** | `pending` | 설정이 생성되었으나 리소스 할당 전. | API Request Accepted |
| **Active** | `running` | 에이전트 프로세스가 구동 중. | Runner Process Spawned |
| **Finalized** | `completed` | 정상 종료 및 결과 집계 완료. | All Agents Finished |
| **Aborted** | `failed` | 런타임 에러 또는 타임아웃. | Uncaught Exception |

---

## 2. Interface Schema (JSON)

모든 데이터 교환은 아래 정의된 JSON Schema를 엄격히 준수해야 한다.
> **Source of Truth**: [`shared/simulation-schema.json`](../../shared/simulation-schema.json)

### 2.1 Header (Meta Information)
모든 상태 파일에 공통적으로 포함되는 메타데이터.

```typescript
interface SimulationHeader {
  simulationId: string;    // UUID v4 format
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;        // Integer 0-100
  createdAt: string;       // ISO 8601 UTC
  updatedAt: string;       // ISO 8601 UTC
}
```

### 2.2 Configuration Context
시뮬레이션 실행을 위한 입력 파라미터 불변 객체.

```typescript
interface SimulationConfig {
  goal: string;            // Natural language validation required (min 10 chars)
  budget: number;          // USD value
  duration: number;        // Days
  targetPersona: string;   // Template ID reference
  parameters: {            // Optional advanced params
    agentCount?: number;
    messageTone?: string;
  };
}
```

### 2.3 Result Payload (Available only in `completed` state)
최종 의사결정을 위한 정량/정성 데이터 집계.

```typescript
interface SimulationResult {
  metrics: {
    reach: number;         // Total impressions
    engagement: number;    // Likes + Comments + Shares
    conversionEstimate: number;
    roas: number;
  };
  confidenceLevel: 'low' | 'medium' | 'high'; // Based on data tier
  agentLogs: AgentLog[];   // Time-series action logs
  personaTraces: Trace[];  // Representative user journeys
}
```

---

## 3. Integration Workflow

시스템 간 상호작용의 시퀀스 다이어그램.

1.  **Request (Dashboard -> Bridge)**
    *   `POST /api/simulation/start`
    *   Bridge는 즉시 `simulationId` 생성 및 `pending` 상태 파일 작성 후 202 응답.

2.  **Execution (Bridge -> Runner)**
    *   Bridge는 `main_runner.py`를 서브프로세스로 스폰(Spawn).
    *   Runner는 시작 시 상태를 `running`으로 업데이트.

3.  **Monitoring (Dashboard -> File System)**
    *   Dashboard는 `2000ms` 간격으로 JSON 파일 폴링.
    *   `progress` 필드를 UI 프로그레스 바에 바인딩.

4.  **Completion (Runner -> File System)**
    *   Runner는 집계 완료 후 `result` 객체를 포함하여 `completed` 상태로 원자적(Atomic) 쓰기 수행.
    *   Dashboard는 `completed` 감지 시 폴링 중단 및 리포트 렌더링.

---

## 4. Error Handling Standards

### 4.1 Runner Failures
Runner 프로세스가 비정상 종료된 경우, Bridge 서버 또는 별도의 Watchdog이 이를 감지하여 상태 파일을 `failed`로 업데이트해야 한다.

### 4.2 Schema Validation
Reader(Dashboard)는 JSON 파일을 읽을 때 필수 필드 누락 여부를 검증해야 한다. 스키마 불일치 시 `Corrupted Data` 에러로 처리하고 사용자에게 알린다.
