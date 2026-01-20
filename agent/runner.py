from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from playwright.async_api import async_playwright

from accounts import (
    AGENT_EMAILS,
    DEFAULT_PASSWORD,
    SNS_URL_DEFAULT,
    get_agent_email,
)

ACTION_SCHEMA_VERSION = "1.0"
CUA_VIEWPORT = {"width": 1024, "height": 768}


@dataclass
class Persona:
    id: str
    name: str
    interests: list[str]
    tone: str
    reaction_bias: str = "neutral"


@dataclass
class EnvConfig:
    sns_url: str
    sns_email: str
    sns_password: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    openai_reasoning_effort: str
    openai_computer_use_model: str
    openai_auto_ack_safety_checks: bool
    agent_log_level: str


@dataclass
class SimulationConfig:
    simulation_id: str
    run_id: str
    goal: str
    budget: float
    duration: float
    target_persona: str
    message_tone: str
    crowd_count: int
    hero_enabled: bool
    hero_persona_id: str | None
    post_context: str
    dry_run: bool
    save_screenshots: bool
    headless: bool
    max_concurrency: int


@dataclass
class RunSummary:
    simulation_id: str
    run_id: str
    status: str
    end_reason: str
    simulation_path: Path
    action_files: list[Path]
    metrics: dict[str, Any]


DEFAULT_PERSONAS = [
    Persona(
        id="vegan-mom",
        name="Vegan Mom",
        interests=["animal welfare", "environment", "healthy food"],
        tone="positive and supportive",
        reaction_bias="positive",
    ),
    Persona(
        id="beauty-analyst",
        name="Beauty Analyst",
        interests=["skincare", "ingredients", "product reviews"],
        tone="curious and analytical",
        reaction_bias="neutral",
    ),
    Persona(
        id="cynical-memer",
        name="Cynical Memer",
        interests=["memes", "authenticity", "pop culture"],
        tone="dry and skeptical",
        reaction_bias="negative",
    ),
]


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
    tmp_path.replace(path)


def get_agent_dir() -> Path:
    return Path(__file__).resolve().parent


def get_repo_root() -> Path:
    return get_agent_dir().parent


def load_env() -> EnvConfig:
    agent_dir = get_agent_dir()
    load_dotenv(agent_dir / ".env")
    sns_url = os.getenv("SNS_URL", SNS_URL_DEFAULT).rstrip("/")
    return EnvConfig(
        sns_url=sns_url,
        sns_email=os.getenv("SNS_EMAIL", get_agent_email(1)),
        sns_password=os.getenv("SNS_PASSWORD", DEFAULT_PASSWORD),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low").strip(),
        openai_computer_use_model=os.getenv("OPENAI_COMPUTER_USE_MODEL", "computer-use-preview").strip(),
        openai_auto_ack_safety_checks=parse_bool(os.getenv("OPENAI_AUTO_ACK_SAFETY_CHECKS"), False),
        agent_log_level=os.getenv("AGENT_LOG_LEVEL", "INFO").strip(),
    )


def configure_logger(level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=level.upper())


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "persona"


def load_personas(persona_file: str | None = None) -> list[Persona]:
    agent_dir = get_agent_dir()
    if persona_file is None:
        default_path = agent_dir / "personas.json"
        if default_path.exists():
            persona_file = str(default_path)

    if not persona_file:
        return list(DEFAULT_PERSONAS)

    path = Path(persona_file)
    if not path.exists():
        return list(DEFAULT_PERSONAS)

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "personas" in payload:
        payload = payload["personas"]

    personas: list[Persona] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "Persona")
            persona_id = str(item.get("id") or slugify(name))
            interests = item.get("interests") or []
            tone = str(item.get("tone") or "neutral")
            reaction_bias = str(item.get("reaction_bias") or item.get("reactionBias") or "neutral")
            personas.append(
                Persona(
                    id=persona_id,
                    name=name,
                    interests=[str(value) for value in interests],
                    tone=tone,
                    reaction_bias=reaction_bias,
                )
            )

    return personas or list(DEFAULT_PERSONAS)


def normalize_goal(goal: str) -> str:
    goal = goal.strip()
    if len(goal) >= 10:
        return goal
    return f"{goal} campaign simulation".strip()


def build_decision_prompt(persona: Persona, post_context: str) -> str:
    return (
        "You are a social media user with the persona below. "
        "Decide how you would react to the post context. "
        "Respond ONLY with a JSON object with keys: "
        "like (boolean), comment (string), follow (boolean), sentiment (string), reasoning (string).\n\n"
        f"Name: {persona.name}\n"
        f"Interests: {', '.join(persona.interests)}\n"
        f"Tone: {persona.tone}\n"
        f"Post context: {post_context}\n"
    )


def build_vision_prompt(persona: Persona) -> str:
    return (
        "You are a social media user with the persona below. "
        "Look at the feed screenshot and decide one simple action. "
        "Respond ONLY with a JSON object with keys: "
        "like (boolean), comment (string), follow (boolean), sentiment (string), reasoning (string).\n\n"
        f"Name: {persona.name}\n"
        f"Interests: {', '.join(persona.interests)}\n"
        f"Tone: {persona.tone}\n"
    )


def build_computer_use_prompt(
    persona: Persona,
    sns_url: str,
    login_email: str,
    login_password: str,
) -> str:
    return (
        "You are a social media user controlling a browser.\n"
        "Stay within the local SNS domain and do not navigate to external sites.\n"
        "If you see a login screen, log in with the provided credentials.\n"
        "Type credentials carefully: click the field, clear it, then type exactly.\n"
        "Double-check there are no extra spaces or missing characters.\n"
        "If login fails, retry once using the same credentials.\n"
        "Goal: Browse the feed, like one relevant post, and optionally leave a short comment.\n"
        "When you are done, respond with a JSON object with keys: "
        "like (boolean), comment (string), follow (boolean), sentiment (string), reasoning (string).\n\n"
        f"Allowed domain: {sns_url}\n"
        f"Login email: {login_email}\n"
        f"Login password: {login_password}\n"
        f"Name: {persona.name}\n"
        f"Interests: {', '.join(persona.interests)}\n"
        f"Tone: {persona.tone}\n"
    )


def extract_json(text: str) -> dict[str, Any] | None:
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


def response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    if hasattr(response, "to_dict"):
        return response.to_dict()
    return {}


def extract_response_text(response: Any) -> str:
    if hasattr(response, "output_text"):
        text_value = getattr(response, "output_text")
        if isinstance(text_value, str) and text_value:
            return text_value

    payload = response_to_dict(response)
    output = payload.get("output", [])
    texts: list[str] = []

    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "output_text":
            texts.append(str(item.get("text") or ""))
        elif item_type == "message":
            for part in item.get("content", []) or []:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type in {"output_text", "text"}:
                    texts.append(str(part.get("text") or ""))
        elif item_type == "reasoning":
            for part in item.get("summary", []) or []:
                if isinstance(part, dict) and part.get("type") == "summary_text":
                    texts.append(str(part.get("text") or ""))

    return "\n".join(texts).strip()


def extract_computer_calls(response: Any) -> list[dict[str, Any]]:
    payload = response_to_dict(response)
    output = payload.get("output", [])
    calls: list[dict[str, Any]] = []
    for item in output:
        if isinstance(item, dict) and item.get("type") == "computer_call":
            calls.append(item)
    return calls


def normalize_decision(parsed: dict[str, Any] | None, fallback_reason: str) -> dict[str, Any]:
    if not parsed:
        return fallback_decision("neutral", fallback_reason)

    like = bool(parsed.get("like", False))
    follow = bool(parsed.get("follow", False))
    comment = str(parsed.get("comment") or "").strip()
    sentiment = str(parsed.get("sentiment") or "").lower().strip()
    reasoning = str(parsed.get("reasoning") or fallback_reason).strip()

    if sentiment not in {"positive", "neutral", "negative"}:
        if like or comment:
            sentiment = "positive"
        else:
            sentiment = "neutral"

    return {
        "like": like,
        "comment": comment,
        "follow": follow,
        "sentiment": sentiment,
        "reasoning": reasoning,
    }


def fallback_decision(bias: str, reason: str) -> dict[str, Any]:
    bias = bias.lower().strip()
    if bias == "positive":
        return {
            "like": True,
            "comment": "Looks great. Love the vibe.",
            "follow": False,
            "sentiment": "positive",
            "reasoning": reason,
        }
    if bias == "negative":
        return {
            "like": False,
            "comment": "Not my style, but good luck.",
            "follow": False,
            "sentiment": "negative",
            "reasoning": reason,
        }
    return {
        "like": False,
        "comment": "",
        "follow": False,
        "sentiment": "neutral",
        "reasoning": reason,
    }


def build_openai_client(env: EnvConfig) -> OpenAI:
    if env.openai_base_url:
        return OpenAI(api_key=env.openai_api_key, base_url=env.openai_base_url)
    return OpenAI(api_key=env.openai_api_key)


def resolve_login_credentials(env: EnvConfig, agent_index: int) -> tuple[str, str]:
    email = env.sns_email.strip()
    password = env.sns_password.strip() or DEFAULT_PASSWORD
    if email in AGENT_EMAILS:
        return email, password
    return get_agent_email(agent_index), password


def decide_with_text_llm(env: EnvConfig, persona: Persona, post_context: str) -> dict[str, Any]:
    prompt = build_decision_prompt(persona, post_context)
    client = build_openai_client(env)
    reasoning = {"effort": env.openai_reasoning_effort} if env.openai_reasoning_effort else None
    kwargs = {
        "model": env.openai_model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_text", "text": "Return JSON only."},
                ],
            }
        ],
        "truncation": "auto",
    }
    if reasoning:
        kwargs["reasoning"] = reasoning
    response = client.responses.create(**kwargs)
    content = extract_response_text(response)
    return normalize_decision(extract_json(content), "text_model_unparseable")


def decide_with_vision_llm(
    env: EnvConfig,
    persona: Persona,
    screenshot_bytes: bytes,
) -> dict[str, Any]:
    prompt = build_vision_prompt(persona)
    image_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
    client = build_openai_client(env)
    response = client.chat.completions.create(
        model=env.openai_model,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    }
                ],
            },
        ],
        max_tokens=400,
    )
    content = response.choices[0].message.content or ""
    return normalize_decision(extract_json(content), "vision_model_unparseable")


class ActionWriter:
    def __init__(
        self,
        base_dir: Path,
        repo_root: Path,
        run_id: str,
        simulation_id: str,
        agent_id: str,
        agent_type: str,
        persona: Persona,
    ) -> None:
        self.base_dir = base_dir / run_id / agent_id
        self.repo_root = repo_root
        self.run_id = run_id
        self.simulation_id = simulation_id
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.persona = persona
        self.sequence = 0
        self.jsonl_path = self.base_dir / "actions.jsonl"
        ensure_dir(self.base_dir)

    def write(
        self,
        action_type: str,
        status: str,
        input_payload: dict[str, Any] | None,
        output_payload: dict[str, Any] | None,
        artifacts: list[dict[str, Any]] | None = None,
        error: str | dict[str, Any] | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        self.sequence += 1
        payload: dict[str, Any] = {
            "schemaVersion": ACTION_SCHEMA_VERSION,
            "runId": self.run_id,
            "simulationId": self.simulation_id,
            "sequence": self.sequence,
            "timestamp": iso_now(),
            "agent": {
                "id": self.agent_id,
                "type": self.agent_type,
                "personaId": self.persona.id,
                "personaName": self.persona.name,
            },
            "action": {
                "type": action_type,
                "status": status,
                "input": input_payload or {},
                "output": output_payload or {},
            },
            "artifacts": artifacts or [],
        }
        if error is not None:
            payload["action"]["error"] = error

        self._append_jsonl(payload)
        filename = f"{self.sequence:04d}_{action_type}.json"
        path = self.base_dir / filename
        write_json_atomic(path, payload)
        return path, payload

    def save_artifact(self, filename: str, content: bytes) -> Path:
        path = self.base_dir / filename
        with path.open("wb") as handle:
            handle.write(content)
        return path

    def _append_jsonl(self, payload: dict[str, Any]) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True))
            handle.write("\n")

    def to_relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)


async def find_first_locator(page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count() > 0:
            return locator.first
    return None


async def fill_field_exact(locator, value: str, field_name: str) -> tuple[bool, str | None]:
    await locator.click()
    await locator.fill("")
    await locator.type(value, delay=25)
    try:
        current_value = await locator.input_value()
    except Exception:
        return True, None

    if current_value != value:
        await locator.fill(value)
        try:
            current_value = await locator.input_value()
        except Exception:
            return True, None

    if current_value != value:
        return False, f"{field_name}_value_mismatch"

    return True, None


async def collect_login_error(page) -> str | None:
    selectors = [
        '[role="alert"]',
        ".alert",
        ".invalid-feedback",
        'text=/credentials|invalid|failed|error|incorrect/i',
    ]
    messages: list[str] = []
    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count() == 0:
            continue
        try:
            messages.extend([text.strip() for text in await locator.all_text_contents()])
        except Exception:
            continue
    messages = [message for message in messages if message]
    if not messages:
        return None
    return "; ".join(sorted(set(messages)))


async def login(page, sns_url: str, email: str, password: str) -> tuple[bool, str | None]:
    try:
        logger.info("Login start url={} user={}", sns_url, email)
        await page.goto(f"{sns_url}/login", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        if "/login" not in page.url:
            logger.info("Login skipped: already authenticated url={}", page.url)
            return True, "already_authenticated"

        email_selectors = [
            'input[name="email"]',
            'input#email',
            'input[type="email"]',
            'input[name="username"]',
            'input#username',
            'input[autocomplete="username"]',
        ]
        password_selectors = [
            'input[name="password"]',
            'input#password',
            'input[type="password"]',
            'input[autocomplete="current-password"]',
        ]
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'input[type="submit"]',
        ]

        email_input = await find_first_locator(page, email_selectors)
        password_input = await find_first_locator(page, password_selectors)
        submit_button = await find_first_locator(page, submit_selectors)

        if email_input is None or password_input is None:
            logger.warning("Login failed: missing form fields url={}", page.url)
            return False, "login_fields_not_found"

        ok, error = await fill_field_exact(email_input, email, "email")
        if not ok:
            logger.warning("Login failed: {}", error)
            return False, error

        ok, error = await fill_field_exact(password_input, password, "password")
        if not ok:
            logger.warning("Login failed: {}", error)
            return False, error

        if submit_button is not None:
            await submit_button.click()
        else:
            await password_input.press("Enter")

        try:
            await page.wait_for_url(lambda url: "/login" not in url, timeout=8000)
        except Exception:
            await page.wait_for_load_state("networkidle")

        if "/login" in page.url:
            error_text = await collect_login_error(page)
            logger.warning("Login failed: still on login page url={}", page.url)
            return False, error_text or "login_still_on_login_page"

        logger.info("Login ok url={}", page.url)
        return True, None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Login error: {}", exc)
        return False, str(exc)


async def perform_action(page, decision: dict[str, Any]) -> dict[str, Any]:
    result = {"liked": False, "commented": False, "followed": False, "scrolled": False}

    if decision.get("like"):
        selectors = [
            'button[aria-label="Like"]',
            'button[title="Like"]',
            'button:has-text("Like")',
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                try:
                    await locator.click()
                    result["liked"] = True
                    break
                except Exception:
                    pass

    comment_text = str(decision.get("comment") or "").strip()
    if comment_text:
        selectors = [
            'textarea[name="comment"]',
            'textarea[placeholder*="Comment"]',
            "textarea",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                try:
                    await locator.click()
                    await locator.fill(comment_text)
                    await locator.press("Enter")
                    result["commented"] = True
                    break
                except Exception:
                    pass

    await page.mouse.wheel(0, 900)
    result["scrolled"] = True
    return result


async def execute_computer_action(page, action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("type")
    result: dict[str, Any] = {"actionType": action_type, "success": True}

    try:
        if action_type == "click":
            x = int(action.get("x", 0))
            y = int(action.get("y", 0))
            button = action.get("button", "left")
            if button not in {"left", "right", "middle"}:
                button = "left"
            await page.mouse.click(x, y, button=button)
        elif action_type == "double_click":
            x = int(action.get("x", 0))
            y = int(action.get("y", 0))
            button = action.get("button", "left")
            await page.mouse.dblclick(x, y, button=button)
        elif action_type == "scroll":
            x = int(action.get("x", 0))
            y = int(action.get("y", 0))
            scroll_x = int(action.get("scrollX", action.get("scroll_x", 0)))
            scroll_y = int(action.get("scrollY", action.get("scroll_y", 0)))
            await page.mouse.move(x, y)
            await page.evaluate(
                "(coords) => window.scrollBy(coords.x, coords.y)",
                {"x": scroll_x, "y": scroll_y},
            )
        elif action_type == "keypress":
            keys = action.get("keys") or []
            for key in keys:
                key = str(key)
                if key.lower() == "enter":
                    await page.keyboard.press("Enter")
                elif key.lower() == "space":
                    await page.keyboard.press(" ")
                else:
                    await page.keyboard.press(key)
        elif action_type == "type":
            text = str(action.get("text") or "")
            if text:
                await page.keyboard.type(text)
        elif action_type == "wait":
            await page.wait_for_timeout(2000)
        elif action_type == "screenshot":
            result["success"] = True
        else:
            result["success"] = False
            result["error"] = f"unsupported_action:{action_type}"
    except Exception as exc:  # noqa: BLE001
        result["success"] = False
        result["error"] = str(exc)

    return result


async def run_computer_use_loop(
    page,
    env: EnvConfig,
    persona: Persona,
    login_email: str,
    login_password: str,
    writer: ActionWriter,
    action_files: list[Path],
    agent_logs: list[dict[str, Any]],
    save_screenshots: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    page.set_viewport_size(CUA_VIEWPORT)
    screenshot_bytes = await page.screenshot()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")

    logger.info(
        "CUA start model={} persona={} url={}",
        env.openai_computer_use_model,
        persona.id,
        page.url,
    )

    tools = [
        {
            "type": "computer_use_preview",
            "display_width": CUA_VIEWPORT["width"],
            "display_height": CUA_VIEWPORT["height"],
            "environment": "browser",
        }
    ]
    prompt = build_computer_use_prompt(
        persona,
        env.sns_url,
        login_email,
        login_password,
    )
    client = build_openai_client(env)

    response = client.responses.create(
        model=env.openai_computer_use_model,
        tools=tools,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{screenshot_b64}",
                    },
                ],
            }
        ],
        reasoning={"summary": "concise"},
        truncation="auto",
    )

    total_actions = 0
    end_reason = "completed"
    last_response = response
    while True:
        computer_calls = extract_computer_calls(last_response)
        if not computer_calls:
            end_reason = "no_computer_calls"
            break

        response_payload = response_to_dict(last_response)
        previous_response_id = response_payload.get("id") or getattr(last_response, "id", None)

        for computer_call in computer_calls:
            call_id = computer_call.get("call_id")
            action = computer_call.get("action", {}) if isinstance(computer_call, dict) else {}
            pending_checks = computer_call.get("pending_safety_checks", []) if isinstance(computer_call, dict) else []

            if pending_checks and not env.openai_auto_ack_safety_checks:
                logger.warning("CUA halted: pending safety checks (%s)", pending_checks)
                path, payload = writer.write(
                    "computer_action",
                    "error",
                    {"action": action},
                    {"result": {}},
                    error={"reason": "pending_safety_checks", "checks": pending_checks},
                )
                action_files.append(path)
                agent_logs.append(
                    {
                        "timestamp": payload["timestamp"],
                        "agentId": writer.agent_id,
                        "action": "computer_action",
                        "detail": {"outputPath": writer.to_relative(path)},
                    }
                )
                decision = fallback_decision(persona.reaction_bias, "pending_safety_checks")
                return decision, {
                    "method": "computer_use",
                    "actions": total_actions,
                    "status": "blocked",
                    "endReason": "pending_safety_checks",
                }

            action_result = await execute_computer_action(page, action)
            await page.wait_for_timeout(1000)
            status = "ok" if action_result.get("success") else "error"

            path, payload = writer.write(
                "computer_action",
                status,
                {"action": action},
                {"result": action_result},
                error=action_result.get("error"),
            )
            action_files.append(path)
            agent_logs.append(
                {
                    "timestamp": payload["timestamp"],
                    "agentId": writer.agent_id,
                    "action": "computer_action",
                    "detail": {"outputPath": writer.to_relative(path)},
                }
            )
            total_actions += 1

            screenshot_bytes = await page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            call_output = {
                "type": "computer_call_output",
                "call_id": call_id,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_b64}",
                },
                "current_url": page.url,
            }
            if pending_checks and env.openai_auto_ack_safety_checks:
                call_output["acknowledged_safety_checks"] = pending_checks

            next_kwargs = {
                "model": env.openai_computer_use_model,
                "tools": tools,
                "input": [call_output],
                "truncation": "auto",
            }
            if previous_response_id:
                next_kwargs["previous_response_id"] = previous_response_id
            last_response = client.responses.create(**next_kwargs)

    summary_text = extract_response_text(last_response)
    decision = normalize_decision(extract_json(summary_text), "computer_use_no_summary")
    action_summary = {
        "method": "computer_use",
        "actions": total_actions,
        "status": "completed",
        "finalUrl": page.url,
        "endReason": end_reason,
    }
    logger.info(
        "CUA end status={} reason={} actions={} url={}",
        action_summary["status"],
        end_reason,
        total_actions,
        page.url,
    )
    return decision, action_summary


def choose_persona(personas: list[Persona], persona_id: str | None) -> Persona:
    if persona_id:
        for persona in personas:
            if persona.id == persona_id:
                return persona
    return personas[0]


def cycle_personas(personas: list[Persona], count: int) -> list[Persona]:
    if not personas:
        return []
    return [personas[idx % len(personas)] for idx in range(count)]


async def run_hero_agent(
    env: EnvConfig,
    config: SimulationConfig,
    persona: Persona,
    outputs_dir: Path,
    repo_root: Path,
    agent_logs: list[dict[str, Any]],
    action_files: list[Path],
) -> tuple[dict[str, Any], dict[str, Any]]:
    writer = ActionWriter(
        base_dir=outputs_dir,
        repo_root=repo_root,
        run_id=config.run_id,
        simulation_id=config.simulation_id,
        agent_id="hero-1",
        agent_type="hero",
        persona=persona,
    )

    decision = fallback_decision(persona.reaction_bias, "hero_not_started")
    action_result: dict[str, Any] = {}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=config.headless,
            args=["--ignore-certificate-errors"],
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        page.set_default_timeout(30000)

        try:
            login_email, login_password = resolve_login_credentials(env, 1)
            login_ok, login_error = await login(page, env.sns_url, login_email, login_password)
            path, payload = writer.write(
                "login",
                "ok" if login_ok else "error",
                {"url": f"{env.sns_url}/login"},
                {"loggedIn": login_ok},
                error=login_error,
            )
            action_files.append(path)
            agent_logs.append(
                {
                    "timestamp": payload["timestamp"],
                    "agentId": "hero-1",
                    "action": "login",
                    "detail": {"outputPath": writer.to_relative(path)},
                }
            )

            feed_url = f"{env.sns_url}/i/web"
            screenshot_bytes: bytes | None = None
            artifacts: list[dict[str, Any]] = []
            observe_status = "ok"
            observe_error: str | None = None

            try:
                await page.goto(feed_url)
                await page.wait_for_timeout(2000)
                screenshot_bytes = await page.screenshot(full_page=True)
                if config.save_screenshots and screenshot_bytes:
                    screenshot_path = writer.save_artifact("observe.png", screenshot_bytes)
                    artifacts.append(
                        {"type": "screenshot", "path": writer.to_relative(screenshot_path)}
                    )
            except Exception as exc:  # noqa: BLE001
                observe_status = "error"
                observe_error = str(exc)

            path, payload = writer.write(
                "observe",
                observe_status,
                {"url": feed_url},
                {"captured": bool(screenshot_bytes)},
                artifacts=artifacts,
                error=observe_error,
            )
            action_files.append(path)
            agent_logs.append(
                {
                    "timestamp": payload["timestamp"],
                    "agentId": "hero-1",
                    "action": "observe",
                    "detail": {"outputPath": writer.to_relative(path)},
                }
            )

            decide_status = "ok"
            decide_error: str | None = None
            if env.openai_api_key and not config.dry_run:
                try:
                    decision, action_result = await run_computer_use_loop(
                        page,
                        env,
                        persona,
                        login_email,
                        login_password,
                        writer,
                        action_files,
                        agent_logs,
                        config.save_screenshots,
                    )
                    if isinstance(action_result, dict):
                        action_result.setdefault("endReason", "completed")
                except Exception as exc:  # noqa: BLE001
                    decide_status = "error"
                    decide_error = str(exc)
                    decision = fallback_decision(persona.reaction_bias, "openai_error")
                    action_result = {
                        "method": "computer_use",
                        "actions": 0,
                        "status": "error",
                        "endReason": "openai_error",
                        "error": str(exc),
                    }
            else:
                reason = "dry_run" if config.dry_run else "missing_OPENAI_API_KEY"
                decision = fallback_decision(persona.reaction_bias, reason)
                try:
                    action_result = await perform_action(page, decision)
                    action_result["method"] = "playwright"
                    action_result["status"] = "completed"
                    action_result["endReason"] = reason
                except Exception as exc:  # noqa: BLE001
                    decide_status = "error"
                    decide_error = str(exc)
                    action_result = {
                        "liked": False,
                        "commented": False,
                        "followed": False,
                        "scrolled": False,
                        "method": "playwright",
                        "status": "error",
                        "endReason": "act_error",
                        "error": str(exc),
                    }

            path, payload = writer.write(
                "decide",
                decide_status,
                {"model": env.openai_model, "dryRun": config.dry_run},
                {"decision": decision},
                error=decide_error,
            )
            action_files.append(path)
            agent_logs.append(
                {
                    "timestamp": payload["timestamp"],
                    "agentId": "hero-1",
                    "action": "decide",
                    "detail": {"outputPath": writer.to_relative(path)},
                }
            )

            act_status = "ok"
            act_error: str | None = None
            if isinstance(action_result, dict) and action_result.get("status") == "error":
                act_status = "error"
                act_error = action_result.get("error")
            if action_result is None:
                action_result = {}
            path, payload = writer.write(
                "act",
                act_status,
                {"decision": decision},
                {"result": action_result},
                error=act_error,
            )
            action_files.append(path)
            agent_logs.append(
                {
                    "timestamp": payload["timestamp"],
                    "agentId": "hero-1",
                    "action": "act",
                    "detail": {"outputPath": writer.to_relative(path)},
                }
            )
        finally:
            await context.close()
            await browser.close()

    return decision, action_result


async def run_crowd_agent(
    env: EnvConfig,
    config: SimulationConfig,
    persona: Persona,
    agent_index: int,
    outputs_dir: Path,
    repo_root: Path,
    agent_logs: list[dict[str, Any]],
    action_files: list[Path],
) -> dict[str, Any]:
    agent_id = f"crowd-{agent_index:03d}"
    writer = ActionWriter(
        base_dir=outputs_dir,
        repo_root=repo_root,
        run_id=config.run_id,
        simulation_id=config.simulation_id,
        agent_id=agent_id,
        agent_type="crowd",
        persona=persona,
    )

    decide_status = "ok"
    decide_error: str | None = None
    if env.openai_api_key and not config.dry_run:
        try:
            decision = await asyncio.to_thread(decide_with_text_llm, env, persona, config.post_context)
        except Exception as exc:  # noqa: BLE001
            decide_status = "error"
            decide_error = str(exc)
            decision = fallback_decision(persona.reaction_bias, "openai_error")
    else:
        reason = "dry_run" if config.dry_run else "missing_OPENAI_API_KEY"
        decision = fallback_decision(persona.reaction_bias, reason)

    path, payload = writer.write(
        "decide",
        decide_status,
        {"postContext": config.post_context, "model": env.openai_model},
        {"decision": decision},
        error=decide_error,
    )
    action_files.append(path)
    agent_logs.append(
        {
            "timestamp": payload["timestamp"],
            "agentId": agent_id,
            "action": "decide",
            "detail": {"outputPath": writer.to_relative(path)},
        }
    )

    action_result = {
        "liked": bool(decision.get("like")),
        "commented": bool(decision.get("comment")),
        "followed": bool(decision.get("follow")),
        "method": "headless",
    }
    path, payload = writer.write(
        "act",
        "ok",
        {"decision": decision},
        {"result": action_result},
    )
    action_files.append(path)
    agent_logs.append(
        {
            "timestamp": payload["timestamp"],
            "agentId": agent_id,
            "action": "act",
            "detail": {"outputPath": writer.to_relative(path)},
        }
    )

    return {
        "agentId": agent_id,
        "personaId": persona.id,
        "decision": decision,
        "actionResult": action_result,
    }


def build_base_payload(config: SimulationConfig) -> dict[str, Any]:
    created_at = iso_now()
    return {
        "simulationId": config.simulation_id,
        "status": "running",
        "progress": 5,
        "createdAt": created_at,
        "updatedAt": created_at,
        "config": {
            "goal": normalize_goal(config.goal),
            "budget": config.budget,
            "duration": config.duration,
            "targetPersona": config.target_persona,
            "parameters": {
                "agentCount": config.crowd_count + (1 if config.hero_enabled else 0),
                "messageTone": config.message_tone,
                "heroEnabled": config.hero_enabled,
                "crowdCount": config.crowd_count,
                "postContext": config.post_context,
                "dryRun": config.dry_run,
                "runId": config.run_id,
            },
        },
    }


async def run_simulation(config: SimulationConfig, personas: list[Persona]) -> RunSummary:
    env = load_env()
    configure_logger(env.agent_log_level)
    repo_root = get_repo_root()
    shared_dir = repo_root / "shared" / "simulation"
    outputs_dir = get_agent_dir() / "outputs"
    ensure_dir(shared_dir)
    ensure_dir(outputs_dir)

    simulation_path = shared_dir / f"{config.simulation_id}.json"
    base_payload = build_base_payload(config)
    write_json_atomic(simulation_path, base_payload)

    agent_logs: list[dict[str, Any]] = []
    persona_traces: list[dict[str, Any]] = []
    action_files: list[Path] = []

    likes = 0
    comments = 0

    status = "completed"
    end_reason = "completed"
    metrics: dict[str, Any] = {}

    try:
        logger.info(
            "Simulation start id={} run={} hero={} crowd={} dry_run={} headless={} model={} cua_model={}",
            config.simulation_id,
            config.run_id,
            config.hero_enabled,
            config.crowd_count,
            config.dry_run,
            config.headless,
            env.openai_model,
            env.openai_computer_use_model,
        )
        if config.hero_enabled:
            hero_persona = choose_persona(personas, config.hero_persona_id)
            hero_decision, hero_action = await run_hero_agent(
                env,
                config,
                hero_persona,
                outputs_dir,
                repo_root,
                agent_logs,
                action_files,
            )
            likes += 1 if hero_decision.get("like") else 0
            comments += 1 if hero_decision.get("comment") else 0
            persona_traces.append(
                {
                    "personaId": hero_persona.id,
                    "agentId": "hero-1",
                    "decision": hero_decision,
                    "actionResult": hero_action,
                }
            )
            if isinstance(hero_action, dict) and hero_action.get("endReason"):
                end_reason = str(hero_action["endReason"])

            base_payload.update(
                {
                    "status": "running",
                    "progress": 50,
                    "updatedAt": iso_now(),
                }
            )
            write_json_atomic(simulation_path, base_payload)

        if config.crowd_count > 0:
            crowd_personas = cycle_personas(personas, config.crowd_count)
            sem = asyncio.Semaphore(max(1, config.max_concurrency))

            async def run_one(idx: int, persona: Persona) -> dict[str, Any]:
                async with sem:
                    return await run_crowd_agent(
                        env,
                        config,
                        persona,
                        idx + 1,
                        outputs_dir,
                        repo_root,
                        agent_logs,
                        action_files,
                    )

            tasks = [
                run_one(idx, persona)
                for idx, persona in enumerate(crowd_personas)
            ]
            results = await asyncio.gather(*tasks)
            for result in results:
                decision = result["decision"]
                likes += 1 if decision.get("like") else 0
                comments += 1 if decision.get("comment") else 0
                persona_traces.append(result)

            base_payload.update(
                {
                    "status": "running",
                    "progress": 90,
                    "updatedAt": iso_now(),
                }
            )
            write_json_atomic(simulation_path, base_payload)

        engagement = likes + comments
        metrics = {
            "reach": config.crowd_count + (1 if config.hero_enabled else 0),
            "engagement": engagement,
            "conversionEstimate": round(engagement * 0.05, 2),
            "roas": round(engagement * 0.02, 2),
            "engagementBreakdown": {
                "likes": likes,
                "comments": comments,
            },
        }

        used_model = bool(env.openai_api_key and not config.dry_run)
        confidence = "medium" if used_model else "low"

        result_payload = {
            **base_payload,
            "status": "completed",
            "progress": 100,
            "updatedAt": iso_now(),
            "result": {
                "metrics": {
                    "reach": metrics["reach"],
                    "engagement": metrics["engagement"],
                    "conversionEstimate": metrics["conversionEstimate"],
                    "roas": metrics["roas"],
                },
                "confidenceLevel": confidence,
                "agentLogs": agent_logs,
                "personaTraces": persona_traces,
            },
        }
        write_json_atomic(simulation_path, result_payload)
        if not config.hero_enabled:
            end_reason = "crowd_only" if config.crowd_count > 0 else "no_agents"
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        end_reason = "exception"
        failure_payload = {
            **base_payload,
            "status": "failed",
            "progress": 100,
            "updatedAt": iso_now(),
            "error": str(exc),
            "result": {
                "metrics": {
                    "reach": 0,
                    "engagement": 0,
                    "conversionEstimate": 0,
                    "roas": 0,
                },
                "confidenceLevel": "low",
                "agentLogs": agent_logs,
                "personaTraces": persona_traces,
            },
        }
        write_json_atomic(simulation_path, failure_payload)
        logger.exception("Simulation failed: {}", exc)
        logger.info("Simulation end status={} reason={} simulation={}", status, end_reason, simulation_path)
    else:
        logger.info("Simulation end status={} reason={} simulation={}", status, end_reason, simulation_path)

    return RunSummary(
        simulation_id=config.simulation_id,
        run_id=config.run_id,
        status=status,
        end_reason=end_reason,
        simulation_path=simulation_path,
        action_files=action_files,
        metrics=metrics,
    )


def validate_simulation_output(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing simulation output at {path}"]

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    for key in ["simulationId", "status", "progress", "createdAt", "updatedAt", "config"]:
        if key not in payload:
            errors.append(f"missing field: {key}")

    if payload.get("status") == "completed":
        result = payload.get("result")
        if not isinstance(result, dict):
            errors.append("missing result block")
        else:
            metrics = result.get("metrics")
            if not isinstance(metrics, dict):
                errors.append("missing metrics block")
            else:
                for key in ["reach", "engagement", "conversionEstimate", "roas"]:
                    if key not in metrics:
                        errors.append(f"missing metrics.{key}")
    return errors


def build_simulation_config(
    goal: str,
    budget: float,
    duration: float,
    target_persona: str,
    message_tone: str,
    crowd_count: int,
    hero_enabled: bool,
    hero_persona_id: str | None,
    post_context: str,
    dry_run: bool,
    save_screenshots: bool,
    headless: bool,
    max_concurrency: int,
    simulation_id: str | None = None,
    run_id: str | None = None,
) -> SimulationConfig:
    return SimulationConfig(
        simulation_id=simulation_id or str(uuid.uuid4()),
        run_id=run_id or str(uuid.uuid4()),
        goal=goal,
        budget=budget,
        duration=duration,
        target_persona=target_persona,
        message_tone=message_tone,
        crowd_count=max(0, crowd_count),
        hero_enabled=hero_enabled,
        hero_persona_id=hero_persona_id,
        post_context=post_context,
        dry_run=dry_run,
        save_screenshots=save_screenshots,
        headless=headless,
        max_concurrency=max(1, max_concurrency),
    )


def default_post_context() -> str:
    return (
        "Local SNS campaign post about an eco-friendly travel bag with bright visuals, "
        "short caption, and a call-to-action to learn more."
    )


async def run_smoke_test() -> tuple[int, str]:
    personas = load_personas()
    config = build_simulation_config(
        goal="Smoke test for agent runner",
        budget=1,
        duration=0.1,
        target_persona=personas[0].id,
        message_tone=personas[0].tone,
        crowd_count=2,
        hero_enabled=False,
        hero_persona_id=None,
        post_context="Smoke test post context",
        dry_run=True,
        save_screenshots=False,
        headless=True,
        max_concurrency=2,
    )
    summary = await run_simulation(config, personas)
    errors = validate_simulation_output(summary.simulation_path)
    if errors:
        return 1, "Smoke test failed: " + ", ".join(errors)

    expected_actions = config.crowd_count * 2
    if len(summary.action_files) < expected_actions:
        return 1, f"Smoke test failed: expected >= {expected_actions} actions"

    agent_dirs = {path.parent for path in summary.action_files}
    missing_logs = []
    for agent_dir in agent_dirs:
        jsonl_path = agent_dir / "actions.jsonl"
        if not jsonl_path.exists():
            missing_logs.append(str(jsonl_path))
            continue
        if jsonl_path.stat().st_size == 0:
            missing_logs.append(str(jsonl_path))
    if missing_logs:
        return 1, "Smoke test failed: missing actions.jsonl for " + ", ".join(missing_logs)

    return 0, (
        "Smoke test ok. "
        f"simulation={summary.simulation_path} actions={len(summary.action_files)}"
    )


def summarize_run(summary: RunSummary) -> str:
    metrics = summary.metrics or {}
    return (
        f"status={summary.status} simulation={summary.simulation_path} "
        f"actions={len(summary.action_files)} "
        f"engagement={metrics.get('engagement', 0)} "
        f"end_reason={summary.end_reason}"
    )


def choose_target_persona(personas: list[Persona], hero_persona_id: str | None) -> str:
    if hero_persona_id:
        return hero_persona_id
    if personas:
        return personas[0].id
    return "mixed"
