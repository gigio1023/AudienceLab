---
name: dashboard-integration
description: React 대시보드와 시뮬레이션 결과 연동. shared/simulation/ 폴더의 JSON 결과를 대시보드에서 시각화할 때 사용.
---

# Dashboard Integration Skill

## Overview

`search-dashboard/` React 앱과 `shared/simulation/` JSON 결과를 연동하여 시뮬레이션 결과를 시각화합니다.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build**: Vite 5
- **Animation**: motion (Framer Motion)
- **Styling**: Custom CSS (No Tailwind)

## Quick Start

```bash
cd search-dashboard
npm install
npm run dev
# → http://localhost:5173
```

## Data Contract

### 시뮬레이션 결과 위치
```
shared/simulation/{simulationId}.json
```

### 결과 스키마 (TypeScript)

```typescript
// search-dashboard/src/types/simulation.ts

interface SimulationResult {
  simulationId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  createdAt: string;
  
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
    positive_rate: number;
    engagement_rate: number;
    sentiment_score: number;
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

## 결과 시각화 컴포넌트

### 1. Metrics Summary Card

```tsx
// src/components/MetricsSummary.tsx
import { motion } from 'motion/react';
import { CountUp } from './animations/CountUp';

interface Props {
  metrics: SimulationResult['metrics'];
}

export function MetricsSummary({ metrics }: Props) {
  return (
    <motion.div 
      className="metrics-grid"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="metric-card positive">
        <span className="label">긍정 반응</span>
        <CountUp end={metrics.positive_rate * 100} suffix="%" />
      </div>
      
      <div className="metric-card neutral">
        <span className="label">중립</span>
        <CountUp end={(1 - metrics.positive_rate - (1 - metrics.engagement_rate)) * 100} suffix="%" />
      </div>
      
      <div className="metric-card negative">
        <span className="label">부정 반응</span>
        <CountUp end={(1 - metrics.positive_rate) * 100} suffix="%" />
      </div>
      
      <div className="metric-card engagement">
        <span className="label">참여율</span>
        <CountUp end={metrics.engagement_rate * 100} suffix="%" />
      </div>
    </motion.div>
  );
}
```

### 2. Agent Trace Timeline

```tsx
// src/components/AgentTimeline.tsx
import { motion, AnimatePresence } from 'motion/react';

interface Props {
  agents: AgentResult[];
  stigmergyTrace: string[];
}

export function AgentTimeline({ agents, stigmergyTrace }: Props) {
  return (
    <div className="timeline">
      <AnimatePresence>
        {agents.map((agent, idx) => (
          <motion.div
            key={agent.persona_id}
            className={`timeline-item ${agent.reaction}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.3 }}
          >
            <div className="persona-badge">{agent.persona_name}</div>
            
            <div className="thought-bubble">
              <span className="internal">💭 {agent.internal_thought}</span>
            </div>
            
            <div className="action">
              {agent.action === 'like' && '❤️ 좋아요'}
              {agent.action === 'comment' && `💬 "${agent.comment_text}"`}
              {agent.action === 'skip' && '⏭️ 스킵'}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

### 3. Stigmergy Visualization

```tsx
// src/components/StigmergyFlow.tsx
export function StigmergyFlow({ trace }: { trace: string[] }) {
  return (
    <div className="stigmergy-flow">
      <h3>🔗 Stigmergy: 에이전트 간 간접 협업</h3>
      
      <div className="flow-diagram">
        {trace.map((comment, idx) => (
          <motion.div
            key={idx}
            className="flow-node"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: idx * 0.5 }}
          >
            <div className="comment">{comment}</div>
            {idx < trace.length - 1 && (
              <div className="arrow">↓ 다음 에이전트에게 영향</div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
```

## 데이터 로딩 (Mock/File)

### Option A: 정적 JSON Import (가장 빠름)

```tsx
// src/data/mockSimulation.ts
import result from '../../../shared/simulation/sim_20260120_143052.json';
export const mockResult: SimulationResult = result;
```

### Option B: File Polling (실시간-ish)

```tsx
// src/hooks/useSimulationResult.ts
import { useState, useEffect } from 'react';

export function useSimulationResult(simulationId: string) {
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  
  useEffect(() => {
    const poll = async () => {
      try {
        // Vite dev server에서 public/ 폴더 서빙
        const res = await fetch(`/simulation/${simulationId}.json`);
        const data = await res.json();
        setResult(data);
        
        if (data.status === 'completed') {
          setStatus('ready');
        }
      } catch {
        setStatus('error');
      }
    };
    
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [simulationId]);
  
  return { result, status };
}
```

## CSS Styling Guide

```css
/* src/styles/simulation.css */

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.metric-card {
  padding: 1.5rem;
  border-radius: 12px;
  text-align: center;
  transition: transform 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
}

.metric-card.positive { background: linear-gradient(135deg, #10b981, #34d399); }
.metric-card.neutral { background: linear-gradient(135deg, #6b7280, #9ca3af); }
.metric-card.negative { background: linear-gradient(135deg, #ef4444, #f87171); }
.metric-card.engagement { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }

.timeline-item {
  padding: 1rem;
  margin: 0.5rem 0;
  border-left: 4px solid var(--accent-mint);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0 8px 8px 0;
}

.timeline-item.positive { border-left-color: #10b981; }
.timeline-item.neutral { border-left-color: #6b7280; }
.timeline-item.negative { border-left-color: #ef4444; }
```

## Integration Checklist

- [ ] `shared/simulation/` 폴더를 대시보드에서 접근 가능하게 설정
- [ ] TypeScript 타입 정의 완료
- [ ] MetricsSummary 컴포넌트 구현
- [ ] AgentTimeline 컴포넌트 구현
- [ ] 애니메이션 적용 (motion/react)
- [ ] Mock 데이터로 UI 테스트
- [ ] 실제 시뮬레이션 결과 연동

## Demo Flow

1. 대시보드 접속 (`localhost:5173`)
2. "시뮬레이션 실행" 버튼 클릭 (또는 Mock 결과 로드)
3. 로딩 애니메이션 표시
4. 결과 도착 시:
   - 메트릭 카드 애니메이션 (CountUp)
   - 에이전트 타임라인 순차 표시
   - Stigmergy 플로우 시각화
5. "이 인플루언서의 팔로워 중 33%가 부정적 반응 예상" 인사이트 표시
