# Simulation Integration Protocol (Current Implementation)

본 문서는 **Agent Runner**가 생성하는 시뮬레이션 결과 파일의 규약을 설명한다. 현재 구현은 **파일 기반 상태 공유**만 사용한다.

## 1. Protocol Architecture

### 1.1 Communication Channel
- **Method**: File Polling
- **Writer**: `agent/cli.py` (single writer)
- **Reader**: 외부 소비자(향후 UI/분석 도구)
- **Resource**: `shared/simulation/{simulationId}.json`

### 1.2 Lifecycle States
| State | Enum | Description |
|---|---|---|
| Initialized | `pending` | (현재 구현에서는 미사용) |
| Active | `running` | 실행 중이며 진행률 업데이트됨 |
| Finalized | `completed` | 정상 종료 및 결과 집계 완료 |
| Aborted | `failed` | 런타임 오류 발생 |

---

## 2. Interface Schema (JSON)

> Source of Truth: `shared/simulation-schema.json`

### 2.1 Header
```typescript
interface SimulationHeader {
  simulationId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number; // 0-100
  createdAt: string;
  updatedAt: string;
}
```

### 2.2 Configuration
```typescript
interface SimulationConfig {
  goal: string;
  budget: number;
  duration: number;
  targetPersona: string;
  parameters?: {
    agentCount?: number;
    messageTone?: string;
    heroEnabled?: boolean;
    crowdCount?: number;
    postContext?: string;
    dryRun?: boolean;
    runId?: string;
  };
}
```

### 2.3 Result Payload
```typescript
interface SimulationResult {
  metrics: {
    reach: number;
    engagement: number;
    conversionEstimate: number;
    roas: number;
  };
  confidenceLevel: 'low' | 'medium' | 'high';
  agentLogs: AgentLog[];
  personaTraces: Trace[];
}
```

### 2.4 Action Logs (Per Agent)
각 에이전트의 상세 액션은 파일로 저장된다.

- JSON: `agent/outputs/{runId}/{agentId}/{sequence}_{action}.json`
- JSONL: `agent/outputs/{runId}/{agentId}/actions.jsonl`
- Schema: `agent/outputs/action-schema.json`
