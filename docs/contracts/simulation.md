# Simulation Integration Protocol (File Feed)

본 문서는 **Simulation Agent**가 생성하는 JSON/JSONL 파일을 **Dashboard**가 지속적으로 읽어 시각화하는 파일 기반 연동 규약을 정의한다. 대시보드는 시뮬레이션을 시작하지 않고, 결과 파일을 관찰하며 상태를 갱신한다.

## 1. Protocol Architecture

### 1.1 Communication Channel
* **Method**: Asynchronous File Polling
* **Writer**: Simulation Runner (Agent Process)
* **Reader**: Dashboard Client (React)

### 1.2 File Location
대시보드는 Vite `public/` 경로를 통해 파일을 읽는다.
```
search-dashboard/public/simulation/{simulationId}.json
search-dashboard/public/simulation/{agent-file}.jsonl
search-dashboard/public/simulation/index.json
```

> 에이전트가 `shared/simulation/`에 쓰는 경우, `public/simulation`에 심볼릭 링크를 연결한다.

---

## 2. Lifecycle States
`status` 필드는 시뮬레이션 자체의 상태를 나타낸다.

| State | Enum Value | Description |
|-------|------------|-------------|
| Initialized | `pending` | 설정 생성 후 실행 전 |
| Active | `running` | 에이전트 실행 중 |
| Finalized | `completed` | 정상 종료 |
| Aborted | `failed` | 비정상 종료 |

Dashboard는 별도로 **Feed 상태**(`loading/ready/error`)를 관리한다.

---

## 3. Interface Schema (JSON)

### 3.1 Types (TypeScript)
```typescript
interface SimulationResult {
  simulationId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;          // 0-100
  createdAt: string;         // ISO 8601
  config: {
    post_description: string;
    agent_count: number;
  };
  agents: AgentResult[];
  metrics: {
    total_agents: number;
    reactions: {
      positive: number;
      neutral: number;
      negative: number;
    };
    actions: {
      like: number;
      comment: number;
      skip: number;
    };
    positive_rate: number;   // 0-1
    engagement_rate: number; // 0-1
    sentiment_score: number; // 0-1
  };
  stigmergy_trace: string[];
}

interface AgentResult {
  persona_id: string;
  persona_name: string;
  reaction: 'positive' | 'neutral' | 'negative';
  action: 'like' | 'comment' | 'skip';
  comment_text: string | null;
  internal_thought: string;
  reasoning: string;
}
```

---

## 4. Agent Activity Feed (JSONL)

각 에이전트는 **JSONL** 파일에 활동 로그를 append 한다. (한 줄 = 하나의 이벤트)

### 4.1 Recommended Fields (Loose)
```
{
  "id": "evt_...",
  "agent_id": "agent_03",
  "action": "comment",
  "timestamp": "2025-10-03T14:44:12Z",
  "content": "Love the tone.",
  "target": "post_001",
  "metadata": {
    "platform": "pixelfed",
    "screen": "feed"
  }
}
```

### 4.2 Normalization
Dashboard는 `search-dashboard/src/lib/activityInterface.ts`에서 필드명을 정규화한다. 스펙 확정 전까지는 `action | event | type` 등 여러 키를 허용한다.

---

## 5. Feed Index (Optional)

대시보드가 에이전트 파일 목록을 자동으로 갱신하기 위해 `index.json`을 사용한다.
```
{
  "updated_at": "2025-10-03T00:00:00Z",
  "files": ["agent-01.jsonl", "agent-02.jsonl"]
}
```

`index.json`이 없으면 `VITE_AGENT_FEEDS` 값을 사용한다.

---

## 6. Writer Requirements

1. **Atomic Write**: 임시 파일로 쓰고 rename하여 부분 쓰기 방지.
2. **Monotonic Progress**: `progress` 값은 되도록 감소하지 않게 유지.
3. **Consistent Arrays**: `agents`, `stigmergy_trace`는 누적형으로 append.
4. **JSONL Append**: 에이전트 파일은 한 줄씩 append 한다.

---

## 7. Reader Behavior (Dashboard)

1. `2000ms` 간격으로 `/simulation/{id}.json` 및 `/simulation/{agent-file}.jsonl` 폴링
2. 정상 수신 시 UI 갱신
3. 실패 시 Mock 데이터로 유지하고 상태 배지에 `Feed error` 표시
