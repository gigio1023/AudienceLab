---
name: agent-simulation
description: VLM 기반 브라우저 에이전트 구현. Playwright + OpenAI Vision으로 SNS에서 자율적으로 상호작용하는 에이전트를 만들 때 사용.
---

# Agent Simulation Skill

## Overview

VLM(Vision Language Model) 기반의 자율 브라우저 에이전트를 구현합니다. 각 에이전트는 페르소나를 가지고 Local SNS에서 탐색, 좋아요, 댓글 등을 수행합니다.

## Tech Stack

- **Language**: Python + `uv` (pip/poetry 사용 금지)
- **Browser**: Playwright (Headless)
- **AI**: OpenAI GPT-4o Vision API

## Quick Start

### 1. 환경 설정

```bash
cd agent
uv init  # 이미 초기화된 경우 스킵
uv add playwright openai python-dotenv
uv run playwright install chromium
```

### 2. .env 설정

```bash
# agent/.env
OPENAI_API_KEY=sk-...
SNS_URL=https://localhost:8092
```

## Single Agent Implementation (MVP)

### 최소 동작 코드

```python
# agent/single_agent.py
import asyncio
from playwright.async_api import async_playwright
from openai import OpenAI

client = OpenAI()

async def run_single_agent(persona: dict):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. 로그인
        await page.goto("https://localhost:8092/login")
        await page.fill('input[name="email"]', "agent1@example.com")
        await page.fill('input[name="password"]', "password")
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        
        # 2. 피드 탐색
        await page.goto("https://localhost:8092/i/web")
        await page.wait_for_timeout(2000)
        
        # 3. 스크린샷 캡처
        screenshot = await page.screenshot()
        
        # 4. VLM 결정
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a social media user with this persona:
                    - Name: {persona['name']}
                    - Interests: {persona['interests']}
                    - Tone: {persona['tone']}
                    
                    Look at this social media feed and decide:
                    1. Do you want to like this post? (yes/no)
                    2. Do you want to comment? If yes, write a comment.
                    3. Your reasoning for this decision.
                    
                    Respond in JSON format."""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot.hex()}"}}
                    ]
                }
            ],
            max_tokens=500
        )
        
        decision = response.choices[0].message.content
        print(f"[{persona['name']}] Decision: {decision}")
        
        # 5. 행동 실행 (간단 버전)
        # TODO: Parse JSON and execute actions
        
        await browser.close()
        return decision

# 실행
persona = {
    "name": "비건맘",
    "interests": ["환경", "건강", "비건"],
    "tone": "긍정적, 환경 의식적"
}

asyncio.run(run_single_agent(persona))
```

## Agentic Loop Pattern

```
┌──────────────────────────────────────────────────────────┐
│                    AGENTIC LOOP                          │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│   │ OBSERVE │───▶│ DECIDE  │───▶│   ACT   │             │
│   │(Screen) │    │ (VLM)   │    │(Click)  │             │
│   └─────────┘    └─────────┘    └─────────┘             │
│        ▲                              │                  │
│        └──────────LOOP────────────────┘                  │
└──────────────────────────────────────────────────────────┘
```

## Persona Templates

```python
PERSONAS = [
    {
        "name": "비건맘",
        "interests": ["동물복지", "환경", "건강식품"],
        "tone": "긍정적, 지지적",
        "reaction_bias": "positive"
    },
    {
        "name": "뷰티덕후", 
        "interests": ["화장품", "스킨케어", "성분분석"],
        "tone": "분석적, 질문형",
        "reaction_bias": "neutral"
    },
    {
        "name": "냉소적MZ",
        "interests": ["밈", "유머", "진정성"],
        "tone": "냉소적, 비판적",
        "reaction_bias": "negative"
    }
]
```

## Output Format

```python
# shared/simulation/{simulation_id}.json
{
    "simulationId": "uuid-v4",
    "status": "completed",
    "agents": [
        {
            "persona": "비건맘",
            "decision": "like",
            "comment": "좋아요! 동물실험 안 하는 거 맞죠?",
            "reasoning": "비건 가치관에 부합하는 제품으로 보임"
        }
    ],
    "metrics": {
        "positive": 1,
        "neutral": 1,
        "negative": 1,
        "engagement_rate": 0.67
    }
}
```

## Resource Optimization

| 모드 | 용도 | 비용 |
|------|------|------|
| **Headless API** | Crowd (다수) | ~$0.01/agent |
| **Full Browser** | Hero (1개) | ~$0.10/agent |

```python
# Headless 모드 (Crowd용) - 브라우저 없이 텍스트만
def cognitive_only_agent(post_description: str, persona: dict):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"You are {persona['name']}..."},
            {"role": "user", "content": f"Post: {post_description}. React."}
        ]
    )
    return response.choices[0].message.content
```

## Troubleshooting

### SSL 인증서 오류
```python
# 로컬 개발 시
browser = await p.chromium.launch(
    headless=True,
    args=['--ignore-certificate-errors']
)
```

### 타임아웃
```python
page.set_default_timeout(30000)  # 30초
```

## Success Criteria

- [ ] 1개 에이전트가 로그인 가능
- [ ] 스크린샷 캡처 및 VLM 분석 가능
- [ ] 좋아요/댓글 결정 출력
- [ ] 결과 JSON 파일 생성
