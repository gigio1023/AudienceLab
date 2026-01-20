# Dashboard Technical Specification (Monitoring)

본 문서는 사전 선별된 인플루언서 리스트를 기반으로 **마케팅 시뮬레이션 결과만 시각화**하는 대시보드의 프론트엔드 기술 명세서이다. 검색/실행/트리거 UI는 범위 밖이며, 에이전트가 생성하는 파일을 계속 관찰하면서 화면을 갱신한다.

## 1. UX/UI Design Philosophy

### 1.1 Monitoring-First
실험을 시작하는 컨트롤이 아니라, **결과를 안정적으로 읽고 해석하는 화면**을 목표로 한다.
- 화면 변화는 최소화하고 텍스트/카드 위주의 정리된 레이아웃을 사용한다.
- 상태 배지는 현재 피드 상태(로딩/정상/오류)를 보여준다.
- 시뮬레이션 입력은 이미 결정되었다는 전제를 유지한다.

### 1.2 Layout Structure
```
+---------------------------------------------------------------+
| Header: Influencer + Feed status + Updated time              |
+---------------------------------------------------------------+
| Live Overview: 핵심 지표 + 예산 사용량 + 최신 활동            |
| Multi-agent Activity Map: 액션 믹스 + 에이전트별 요약          |
| User Personas: 시뮬레이션에 사용된 페르소나 정의               |
+---------------------------------------------------------------+
```

---

## 2. Frontend Architecture

### 2.1 Technology Stack
* **Core**: React 18 + TypeScript
* **Build**: Vite
* **Styling**: Custom CSS (tokens + standard CSS)
* **Animation**: Optional. 기본 플로우는 정적 렌더링만 사용한다.

### 2.2 Component Responsibility
* **App (`search-dashboard/src/App.tsx`)**
  - 폴링 훅 호출
  - 결과/상태를 섹션별로 전달
* **Simulation Feed Hook (`search-dashboard/src/hooks/useSimulationResult.ts`)**
  - `/simulation/{id}.json` 폴링
  - 로딩/오류/정상 상태 관리
* **Agent Activity Hook (`search-dashboard/src/hooks/useAgentActivityFeed.ts`)**
  - `/simulation/{agent-file}.jsonl` 폴링
  - JSONL 파싱 및 이벤트 정규화
* **Feed Index Hook (`search-dashboard/src/hooks/useActivityFeedIndex.ts`)**
  - `/simulation/index.json` 폴링
  - 에이전트 파일 목록 자동 갱신

---

## 3. Data Flow & State

### 3.1 Simulation Feed 상태
UI 내부 상태는 다음 3단계만 사용한다.
- `loading`: 최초 접근 또는 결과 미수신
- `ready`: 정상 수신
- `error`: 파일 접근 실패 또는 스키마 오류

> JSON 안의 `status` 필드(`pending/running/completed/failed`)는 시뮬레이션 자체 상태이며, UI의 feed 상태와 구분한다.

### 3.2 Polling 규칙
- **Interval**: 2000ms (기본값)
- **Fetch Path**: `/simulation/{simulationId}.json` + `/simulation/{agent-file}.jsonl`
- **Index Path**: `/simulation/index.json` (선택)
- **Cache Busting**: `?t=timestamp` 쿼리 추가
- **Fallback**: 파일이 없거나 오류 시 Mock 데이터를 표시

### 3.3 Budget usage (Optional)
- `config.budget_total`과 `config.action_costs`가 있으면 예산 사용량을 계산해 표시한다.
- `action_costs`가 없으면 기본 비용 테이블(좋아요/댓글/팔로우 등)을 사용한다.
- JSONL 이벤트가 없으면 `metrics.actions` 값을 기준으로 예산을 계산한다.

---

## 4. Integration Specifications

### 4.1 File 위치
대시보드는 Vite `public/` 경로만 읽을 수 있으므로, 결과 파일은 아래 위치로 노출되어야 한다.
```
search-dashboard/public/simulation/{simulationId}.json
search-dashboard/public/simulation/{agent-file}.jsonl
search-dashboard/public/simulation/index.json
```

### 4.2 Agent 출력 연결 방법 (권장)
에이전트가 `shared/simulation/`에 결과를 쓰는 경우, 심볼릭 링크로 연결한다.
```
ln -s ../../shared/simulation /Users/user/git/oh-fe/search-dashboard/public/simulation
```

> 파일은 **임시 파일로 쓰고 원자적으로 rename**하는 방식을 권장한다. (부분 쓰기 방지)

### 4.3 환경 변수
```
VITE_SIMULATION_ID=latest
VITE_AGENT_FEEDS=agent-01.jsonl,agent-02.jsonl,agent-03.jsonl
```
- `VITE_AGENT_FEEDS`는 콤마로 구분된 JSONL 파일 목록이다.
- `index.json`이 존재하면, `VITE_AGENT_FEEDS` 대신 index를 사용한다.

---

## 5. Agent Activity Interface (JSONL)

각 파일은 **JSONL**이며 한 줄이 하나의 이벤트를 의미한다. 스펙이 확정되기 전까지 다음과 같은 느슨한 인터페이스를 사용한다.

### 5.1 표준화 대상 키
아래 키 중 존재하는 값을 사용해 정규화한다.
- `agent_id | agentId | persona_id | personaId`
- `action | event | type`
- `timestamp | time | created_at | createdAt`
- `content | text | comment | message`
- `target | object | post_id | postId`
- `metadata | meta` (추가 정보)

### 5.2 정규화 결과 타입
```typescript
export type AgentActivityEvent = {
  id: string;
  agent_id: string;
  action: string;
  timestamp: string;
  source: string;
  target?: string | null;
  content?: string | null;
  metadata?: Record<string, unknown> | null;
};
```

> 정규화는 `search-dashboard/src/lib/activityInterface.ts`에서 수행된다.

---

## 6. 운영 시나리오

1. 에이전트가 `/shared/simulation/*.jsonl`을 주기적으로 업데이트
2. 대시보드가 `/simulation/index.json`을 통해 파일 목록을 읽음 (없으면 env 사용)
3. `/simulation/*.jsonl`을 2초마다 폴링
4. `action` 이벤트가 최신순으로 화면에 반영
5. 오류 시 Mock 데이터는 유지되고 상태 배지에 `Feed error` 표시

---

## 7. Data Contract 요약
- 시뮬레이션 요약 JSON은 `docs/contracts/simulation.md`를 따른다.
- 에이전트 JSONL은 위의 느슨한 인터페이스를 따른다.
