import asyncio
import base64
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from playwright.async_api import async_playwright


@dataclass
class Persona:
    id: str
    name: str
    interests: list[str]
    tone: str


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json_atomic(path: str, payload: Dict[str, Any]) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
    os.replace(tmp_path, path)


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def build_decision_prompt(persona: Persona) -> str:
    return (
        "You are a social media user with the following persona. "
        "Look at the feed and decide one simple action. "
        "Respond ONLY with a JSON object with keys: like (boolean), comment (string), reasoning (string).\n\n"
        f"Name: {persona.name}\n"
        f"Interests: {', '.join(persona.interests)}\n"
        f"Tone: {persona.tone}\n"
    )


def default_decision(reason: str) -> Dict[str, Any]:
    return {"like": False, "comment": "", "reasoning": reason}


async def decide_with_vlm(
    client: OpenAI,
    model: str,
    persona: Persona,
    screenshot_bytes: bytes,
) -> Dict[str, Any]:
    image_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": build_decision_prompt(persona)},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                        },
                    }
                ],
            },
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content or ""
    parsed = extract_json(content)
    if parsed is None:
        return default_decision("model_response_unparseable")
    return {
        "like": bool(parsed.get("like", False)),
        "comment": str(parsed.get("comment", "") or ""),
        "reasoning": str(parsed.get("reasoning", "") or ""),
    }


async def perform_action(page, decision: Dict[str, Any]) -> Dict[str, Any]:
    action_result = {"liked": False, "commented": False, "scrolled": False}

    if decision.get("like"):
        selectors = [
            'button[aria-label="Like"]',
            'button[title="Like"]',
            'button:has-text("Like")',
            'button:has-text("좋아요")',
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                try:
                    await locator.click()
                    action_result["liked"] = True
                    break
                except Exception:
                    pass

    await page.mouse.wheel(0, 900)
    action_result["scrolled"] = True
    return action_result


async def login(page, sns_url: str, email: str, password: str) -> None:
    await page.goto(f"{sns_url}/login")
    await page.wait_for_load_state("networkidle")

    email_input = None
    for selector in ['input[name="email"]', 'input[name="username"]']:
        locator = page.locator(selector)
        if await locator.count() > 0:
            email_input = locator.first
            break

    password_input = page.locator('input[name="password"]')
    if email_input is None or await password_input.count() == 0:
        return

    await email_input.fill(email)
    await password_input.fill(password)
    await page.locator('button[type="submit"]').click()
    await page.wait_for_load_state("networkidle")


async def run_single_agent(persona: Persona) -> Dict[str, Any]:
    load_dotenv()

    sns_url = os.getenv("SNS_URL", "https://localhost:8092")
    sns_email = os.getenv("SNS_EMAIL", "agent1@audiencelab.local")
    sns_password = os.getenv("SNS_PASSWORD", "password")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    simulation_id = str(uuid.uuid4())
    created_at = iso_now()

    shared_dir = os.path.join(os.path.dirname(__file__), "..", "shared", "simulation")
    shared_dir = os.path.abspath(shared_dir)
    ensure_dir(shared_dir)
    output_path = os.path.join(shared_dir, f"{simulation_id}.json")

    base_payload = {
        "simulationId": simulation_id,
        "status": "running",
        "progress": 10,
        "createdAt": created_at,
        "updatedAt": created_at,
        "config": {
            "goal": "Run a single agent loop on local SNS feed",
            "budget": 50,
            "duration": 1,
            "targetPersona": persona.id,
            "parameters": {"agentCount": 1, "messageTone": persona.tone},
        },
    }
    write_json_atomic(output_path, base_payload)

    agent_logs: list[Dict[str, Any]] = []
    decision: Dict[str, Any] = default_decision("not_started")
    action_result = {}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"],
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        page.set_default_timeout(30000)

        try:
            await login(page, sns_url, sns_email, sns_password)
            await page.goto(f"{sns_url}/i/web")
            await page.wait_for_timeout(2000)

            screenshot_bytes = await page.screenshot(full_page=True)
            agent_logs.append(
                {
                    "timestamp": iso_now(),
                    "agentId": persona.id,
                    "action": "observe",
                    "detail": "Captured feed screenshot",
                }
            )

            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if api_key:
                client = OpenAI()
                decision = await decide_with_vlm(client, model, persona, screenshot_bytes)
            else:
                decision = default_decision("missing_OPENAI_API_KEY")

            agent_logs.append(
                {
                    "timestamp": iso_now(),
                    "agentId": persona.id,
                    "action": "decide",
                    "detail": decision,
                }
            )

            action_result = await perform_action(page, decision)
            agent_logs.append(
                {
                    "timestamp": iso_now(),
                    "agentId": persona.id,
                    "action": "act",
                    "detail": action_result,
                }
            )
        finally:
            await context.close()
            await browser.close()

    likes = 1 if decision.get("like") else 0
    comments = 1 if decision.get("comment") else 0
    engagement = likes + comments

    result_payload = {
        **base_payload,
        "status": "completed",
        "progress": 100,
        "updatedAt": iso_now(),
        "result": {
            "metrics": {
                "reach": 1,
                "engagement": engagement,
                "conversionEstimate": 0,
                "roas": 0.0,
            },
            "confidenceLevel": "low",
            "agentLogs": agent_logs,
            "personaTraces": [
                {
                    "personaId": persona.id,
                    "decision": decision,
                    "actionResult": action_result,
                }
            ],
        },
    }

    write_json_atomic(output_path, result_payload)
    return result_payload


def main() -> None:
    persona = Persona(
        id="vegan-mom",
        name="Vegan Mom",
        interests=["animal welfare", "environment", "healthy food"],
        tone="positive and supportive",
    )
    asyncio.run(run_single_agent(persona))


if __name__ == "__main__":
    main()
