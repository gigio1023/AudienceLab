"""Local Playwright agent with OpenAI decision making.

This module implements browser automation using Playwright directly,
with OpenAI for action decision making. This avoids the need for
publicly accessible MCP servers.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class ActionResponse(BaseModel):
    """Structured response for agent action decision."""
    reasoning: str
    target: str | None = None
    comment_text: str | None = None
    action: str

from accounts import (
    DEFAULT_PASSWORD,
    SNS_URL_DEFAULT,
    get_agent_email,
)

# Action types the model can choose
ACTION_TYPES = ["like", "comment", "follow", "scroll_down", "scroll_up", "noop", "done"]

# Maximum consecutive failures before stopping
MAX_CONSECUTIVE_FAILURES = 3

# Default max steps per agent loop
DEFAULT_MAX_STEPS = 35

# Exploration phase configuration
EXPLORATION_STEPS = 5  # First N steps are exploration phase
EXPLORATION_SCROLL_WEIGHT = 60  # % weight for scroll in exploration
EXPLORATION_NOOP_WEIGHT = 30    # % weight for noop in exploration

# Engagement phase configuration
ENGAGEMENT_NOOP_WEIGHT = 50    # % weight for noop in engagement
ENGAGEMENT_SCROLL_WEIGHT = 20  # % weight for scroll in engagement
ENGAGEMENT_LIKE_WEIGHT = 15    # % weight for like in engagement
ENGAGEMENT_COMMENT_WEIGHT = 10 # % weight for comment in engagement
ENGAGEMENT_FOLLOW_WEIGHT = 5   # % weight for follow in engagement

# Jinja2 environment
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env: Environment | None = None

# Session intent defaults (lightly randomized to avoid robotic patterns)
SESSION_INTENTS = [
    "catch up on friends",
    "discover new creators",
    "look for tips and inspiration",
    "skim quickly while waiting",
    "relax and browse",
]


def get_jinja_env() -> Environment:
    """Get or create Jinja2 environment."""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


@dataclass
class LocalAgentConfig:
    """Configuration for local Playwright agent."""
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    sns_url: str
    max_steps: int
    step_delay_min: float
    step_delay_max: float
    headless: bool | None  # None = auto (hero headed, others headless)
    save_screenshots: bool
    output_dir: Path


@dataclass
class Persona:
    """Agent persona definition from sns-vibe personas.json."""
    username: str
    age_range: str
    location: str
    occupation: str
    personality_traits: list[str]
    communication_style: str
    interests: list[str]
    preferred_content_types: list[str]
    engagement_level: str
    posting_frequency: str
    active_hours: str
    like_tendency: float
    comment_tendency: float
    follow_tendency: float
    behavior_prompt: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Persona":
        """Create Persona from dictionary."""
        return cls(
            username=data.get("username", "unknown"),
            age_range=data.get("age_range", "unknown"),
            location=data.get("location", "unknown"),
            occupation=data.get("occupation", "unknown"),
            personality_traits=data.get("personality_traits", []),
            communication_style=data.get("communication_style", "casual"),
            interests=data.get("interests", []),
            preferred_content_types=data.get("preferred_content_types", []),
            engagement_level=data.get("engagement_level", "medium"),
            posting_frequency=data.get("posting_frequency", "rarely"),
            active_hours=data.get("active_hours", ""),
            like_tendency=float(data.get("like_tendency", 0.5)),
            comment_tendency=float(data.get("comment_tendency", 0.3)),
            follow_tendency=float(data.get("follow_tendency", 0.2)),
            behavior_prompt=data.get("behavior_prompt", "You are a casual social media user."),
        )


def load_personas_from_seeds() -> list[Persona]:
    """Load personas from sns-vibe/seeds/personas.json."""
    agent_dir = Path(__file__).resolve().parent
    seeds_path = agent_dir.parent / "sns-vibe" / "seeds" / "personas.json"

    if not seeds_path.exists():
        logger.warning("Personas file not found at {}, using default", seeds_path)
        return []

    with seeds_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    personas = []
    for item in data:
        try:
            personas.append(Persona.from_dict(item))
        except Exception as e:
            logger.warning("Failed to parse persona: {} - {}", item.get("username"), e)

    logger.info("Loaded {} personas from {}", len(personas), seeds_path)
    return personas


@dataclass
class AgentState:
    """Runtime state for a local agent."""
    agent_id: str
    persona: Persona
    username: str
    password: str
    current_url: str = ""
    step_count: int = 0
    consecutive_failures: int = 0
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    is_logged_in: bool = False
    last_error: str | None = None
    page_content: str = ""
    session_intent: str = ""


@dataclass
class ActionDecision:
    """Parsed action decision from the model."""
    action: str
    target: str | None = None
    comment_text: str | None = None
    reasoning: str = ""


def iso_now() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def load_local_config(
    headless: bool | None = None,  # None = auto (hero headed, others headless)
    save_screenshots: bool = False,
    output_dir: Path | None = None,
) -> LocalAgentConfig:
    """Load configuration from environment."""
    agent_dir = Path(__file__).resolve().parent
    load_dotenv(agent_dir / ".env")

    # Default output to search-dashboard/public/simulation for live dashboard
    if output_dir is None:
        output_dir = agent_dir.parent / "search-dashboard" / "public" / "simulation"

    return LocalAgentConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        sns_url=os.getenv("SNS_URL", SNS_URL_DEFAULT).rstrip("/"),
        max_steps=int(os.getenv("MCP_MAX_STEPS", str(DEFAULT_MAX_STEPS))),
        step_delay_min=float(os.getenv("MCP_STEP_DELAY_MIN", "1.0")),
        step_delay_max=float(os.getenv("MCP_STEP_DELAY_MAX", "3.0")),
        headless=headless,
        save_screenshots=save_screenshots,
        output_dir=output_dir,
    )


def build_openai_client(config: LocalAgentConfig) -> OpenAI:
    """Build OpenAI client."""
    if config.openai_base_url:
        return OpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
    return OpenAI(api_key=config.openai_api_key)


def build_decision_system_prompt(
    persona: Persona,
    sns_url: str,
    step_count: int,
    max_steps: int,
) -> str:
    """Build system prompt for action decision using Jinja2 template."""
    env = get_jinja_env()
    template = env.get_template("system_prompt.j2")

    return template.render(
        persona=persona,
        sns_url=sns_url,
        actions=ACTION_TYPES,
        step_count=step_count,
        max_steps=max_steps,
        local_time=datetime.now().strftime("%H:%M"),
        exploration_steps=EXPLORATION_STEPS,
        exploration_scroll_weight=EXPLORATION_SCROLL_WEIGHT,
        exploration_noop_weight=EXPLORATION_NOOP_WEIGHT,
        engagement_noop_weight=ENGAGEMENT_NOOP_WEIGHT,
        engagement_scroll_weight=ENGAGEMENT_SCROLL_WEIGHT,
        engagement_like_weight=ENGAGEMENT_LIKE_WEIGHT,
        engagement_comment_weight=ENGAGEMENT_COMMENT_WEIGHT,
        engagement_follow_weight=ENGAGEMENT_FOLLOW_WEIGHT,
    )


def build_decision_user_prompt(
    state: AgentState,
    page_content: str,
    max_steps: int,
) -> str:
    """Build user prompt for action decision using Jinja2 template."""
    env = get_jinja_env()
    template = env.get_template("user_prompt.j2")

    # Limit page content to current visible area
    limited_content = page_content[:4000]

    phase = "exploration" if state.step_count <= EXPLORATION_STEPS else "engagement"
    recent_actions = []
    for entry in state.actions_taken[-5:]:
        action = (
            entry.get("decision", {}).get("action")
            or entry.get("result", {}).get("action")
            or entry.get("action")
        )
        if action:
            recent_actions.append(action)
    recent_targets = [
        a.get("decision", {}).get("target")
        for a in state.actions_taken[-5:]
        if a.get("decision", {}).get("target")
    ]
    engagement_level = (state.persona.engagement_level or "medium").lower()
    if engagement_level == "high":
        suggested_stop_step = max_steps - max(2, int(max_steps * 0.1))
    elif engagement_level == "low":
        suggested_stop_step = max(3, int(max_steps * 0.5))
    else:
        suggested_stop_step = max(4, int(max_steps * 0.7))

    return template.render(
        persona=state.persona,
        step_count=state.step_count,
        max_steps=max_steps,
        phase=phase,
        actions_count=len(state.actions_taken),
        recent_actions=recent_actions,
        recent_targets=[t for t in recent_targets if t],
        page_content=limited_content,
        exploration_steps=EXPLORATION_STEPS,
        suggested_stop_step=suggested_stop_step,
        session_intent=state.session_intent,
    )


def parse_action_decision(response_text: str) -> ActionDecision:
    """Parse action decision from model response."""
    try:
        # Try to find JSON in the response
        text = response_text.strip()
        # Handle markdown code blocks
        if "```json" in text:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
        elif "```" in text:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            data = json.loads(json_str)
            return ActionDecision(
                action=data.get("action", "noop"),
                target=data.get("target"),
                comment_text=data.get("comment_text"),
                reasoning=data.get("reasoning", ""),
            )
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse action: {} - {}", e, response_text[:200])

    return ActionDecision(action="noop", reasoning="Parse failed")


def extract_response_text(response: Any) -> str:
    """Extract text content from OpenAI response."""
    if hasattr(response, "output_text"):
        text_value = getattr(response, "output_text")
        if isinstance(text_value, str) and text_value:
            return text_value

    try:
        if hasattr(response, "model_dump"):
            payload = response.model_dump()
        elif isinstance(response, dict):
            payload = response
        else:
            return ""

        output = payload.get("output", [])
        texts = []

        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "output_text":
                texts.append(str(item.get("text") or ""))
            elif item_type == "message":
                for part in item.get("content", []) or []:
                    if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                        texts.append(str(part.get("text") or ""))

        return "\n".join(texts).strip()
    except Exception:
        return ""


def response_to_dict(response: Any) -> dict[str, Any]:
    """Convert response to dictionary."""
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    if hasattr(response, "to_dict"):
        return response.to_dict()
    return {}


def pick_session_intent(persona: Persona) -> str:
    """Choose a light session intent based on persona interests."""
    if persona.interests:
        topic = random.choice(persona.interests)
        return f"browse for {topic} posts"
    return random.choice(SESSION_INTENTS)


async def extract_page_content(page: Page) -> str:
    """Extract readable content from the page for decision making."""
    try:
        # Get page text content in a structured way
        content_parts = []

        # Page title and URL
        title = await page.title()
        content_parts.append(f"Page: {title}")
        content_parts.append(f"URL: {page.url}")
        content_parts.append("")

        # Try to find posts/feed items
        posts = await page.query_selector_all('[id^="post-"], .post, article, [data-post-id]')

        if posts:
            content_parts.append(f"Found {len(posts)} posts:")
            for i, post in enumerate(posts[:10]):  # Limit to 10 posts
                try:
                    post_id = await post.get_attribute("id") or await post.get_attribute("data-post-id") or f"item-{i}"
                    text = await post.inner_text()
                    text = " ".join(text.split())[:300]  # Normalize whitespace, limit length

                    # Try to find like button state
                    like_btn = await post.query_selector('[id^="like-button-"], .like-button, [data-action="like"]')
                    liked = False
                    if like_btn:
                        classes = await like_btn.get_attribute("class") or ""
                        liked = "liked" in classes or "active" in classes

                    content_parts.append(f"\n[{post_id}] {'(liked)' if liked else ''}")
                    content_parts.append(f"  {text}")
                except Exception:
                    continue
        else:
            # Fallback: get all visible text
            body_text = await page.inner_text("body")
            body_text = " ".join(body_text.split())[:2000]
            content_parts.append(f"Page content: {body_text}")

        return "\n".join(content_parts)

    except Exception as e:
        logger.warning("Failed to extract page content: {}", e)
        return f"URL: {page.url}\nError extracting content: {e}"


class LocalPlaywrightAgent:
    """Runs a single agent with local Playwright and OpenAI decision making."""

    def __init__(
        self,
        config: LocalAgentConfig,
        persona: Persona,
        agent_index: int,
        is_hero: bool = False,
    ):
        self.config = config
        self.persona = persona
        self.agent_index = agent_index
        self.is_hero = is_hero
        self.client = build_openai_client(config)

        # Resolve credentials
        email = get_agent_email(agent_index)
        username = email.split("@")[0] if "@" in email else email

        agent_type = "hero" if is_hero else "crowd"
        self.state = AgentState(
            agent_id=f"local-{agent_type}-{agent_index:03d}",
            persona=persona,
            username=username,
            password=DEFAULT_PASSWORD,
            session_intent=pick_session_intent(persona),
        )

        # Browser resources (set during run)
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        # Output directory - flat structure for dashboard
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / f"{self.state.agent_id}.jsonl"

    def _log_action(self, action_data: dict[str, Any]) -> None:
        """Append action to JSONL log."""
        entry = {
            "timestamp": iso_now(),
            "agentId": self.state.agent_id,
            "step": self.state.step_count,
            **action_data,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.state.actions_taken.append(entry)

    async def _screenshot(self, name: str) -> str | None:
        """Take screenshot if enabled."""
        if not self.config.save_screenshots or not self.page:
            return None
        try:
            # Create screenshots subdirectory
            screenshots_dir = self.output_dir / "screenshots" / self.state.agent_id
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            path = screenshots_dir / f"{self.state.step_count:03d}_{name}.png"
            await self.page.screenshot(path=str(path))
            return str(path)
        except Exception as e:
            logger.warning("Screenshot failed: {}", e)
            return None

    async def _get_decision(self, page_content: str) -> tuple[ActionDecision, str, dict[str, Any]]:
        """Get action decision from OpenAI using structured output."""
        try:
            system_prompt = build_decision_system_prompt(
                self.persona,
                self.config.sns_url,
                self.state.step_count,
                self.config.max_steps,
            )
            user_prompt = build_decision_user_prompt(
                self.state,
                page_content,
                self.config.max_steps,
            )

            response = await asyncio.to_thread(
                self.client.responses.parse,
                model=self.config.openai_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=ActionResponse,
            )
            raw_text = extract_response_text(response)
            raw_response = response_to_dict(response)
            parsed = response.output_parsed
            return (
                ActionDecision(
                    action=parsed.action,
                    target=parsed.target,
                    comment_text=parsed.comment_text,
                    reasoning=parsed.reasoning,
                ),
                raw_text,
                raw_response,
            )
        except Exception as e:
            logger.error("Decision call failed: {}", e)
            return (
                ActionDecision(action="noop", reasoning=f"API error: {e}"),
                "",
                {"error": str(e)},
            )

    def _extract_post_id(self, target: str) -> str:
        """Extract numeric post ID from target string."""
        if not target:
            return ""
        # Handle formats like "post-17", "17", "#post-17"
        import re
        match = re.search(r'(\d+)', target)
        if match:
            return match.group(1)
        return target

    async def _execute_action(self, decision: ActionDecision) -> dict[str, Any]:
        """Execute the decided action using Playwright."""
        result = {
            "action": decision.action,
            "target": decision.target,
            "reasoning": decision.reasoning,
            "success": False,
        }

        if not self.page:
            result["error"] = "No page available"
            return result

        # Extract numeric post ID from target
        post_id = self._extract_post_id(decision.target or "")

        try:
            if decision.action == "like" and post_id:
                # Try various selectors for like button
                selectors = [
                    f"#like-button-{post_id}",
                    f"#post-{post_id} [data-action='like']",
                    f"#post-{post_id} .like-button",
                    f"#post-{post_id} button:has-text('Like')",
                ]
                for selector in selectors:
                    try:
                        btn = await self.page.query_selector(selector)
                        if btn:
                            await btn.click()
                            result["success"] = True
                            result["selector"] = selector
                            break
                    except Exception:
                        continue
                if not result["success"]:
                    result["error"] = "Like button not found"

            elif decision.action == "comment" and post_id and decision.comment_text:
                # Try to find and fill comment input
                input_selectors = [
                    f"#comment-input-{post_id}",
                    f"#post-{post_id} [data-action='comment-input']",
                    f"#post-{post_id} textarea",
                    f"#post-{post_id} input[type='text']",
                ]
                button_selectors = [
                    f"#comment-button-{post_id}",
                    f"#post-{post_id} [data-action='comment-submit']",
                    f"#post-{post_id} button:has-text('Comment')",
                    f"#post-{post_id} button:has-text('Post')",
                ]

                input_found = False
                for selector in input_selectors:
                    try:
                        inp = await self.page.query_selector(selector)
                        if inp:
                            await inp.fill(decision.comment_text)
                            input_found = True
                            break
                    except Exception:
                        continue

                if input_found:
                    for selector in button_selectors:
                        try:
                            btn = await self.page.query_selector(selector)
                            if btn:
                                await btn.click()
                                result["success"] = True
                                result["comment"] = decision.comment_text
                                break
                        except Exception:
                            continue
                if not result["success"]:
                    result["error"] = "Comment input/button not found"

            elif decision.action == "follow" and decision.target:
                selectors = [
                    f"#follow-{decision.target}",
                    f"[data-user='{decision.target}'] button:has-text('Follow')",
                    f"button:has-text('Follow'):near(#{decision.target})",
                ]
                for selector in selectors:
                    try:
                        btn = await self.page.query_selector(selector)
                        if btn:
                            await btn.click()
                            result["success"] = True
                            break
                    except Exception:
                        continue
                if not result["success"]:
                    result["error"] = "Follow button not found"

            elif decision.action == "scroll_down":
                await self.page.keyboard.press("PageDown")
                await asyncio.sleep(0.5)
                result["success"] = True

            elif decision.action == "scroll_up":
                await self.page.keyboard.press("PageUp")
                await asyncio.sleep(0.5)
                result["success"] = True

            elif decision.action in ("noop", "done"):
                result["success"] = True

            else:
                result["error"] = f"Unknown action: {decision.action}"

        except Exception as e:
            result["error"] = str(e)
            logger.warning("Action execution failed: {}", e)

        return result

    async def _login(self) -> bool:
        """Perform login."""
        if not self.page:
            return False

        try:
            # Navigate to SNS
            await self.page.goto(self.config.sns_url)
            await asyncio.sleep(1)

            # Take screenshot
            await self._screenshot("login_page")

            # Check if already on feed (already logged in)
            if "/feed" in self.page.url:
                logger.info("Agent {} already logged in", self.state.agent_id)
                return True

            # Find and fill username input
            username_input = await self.page.query_selector(
                'input#username, input[name="username"], input[type="text"]'
            )
            if username_input:
                await username_input.fill(self.state.username)
            else:
                logger.warning("Username input not found")
                return False

            # Click login button
            login_btn = await self.page.query_selector(
                'button[type="submit"], button:has-text("Login"), button:has-text("Sign in")'
            )
            if login_btn:
                await login_btn.click()
            else:
                # Try pressing Enter
                await self.page.keyboard.press("Enter")

            # Wait for navigation
            await asyncio.sleep(2)

            # Check if login succeeded
            if "/feed" in self.page.url or await self.page.query_selector("#feed, .feed, [data-feed]"):
                await self._screenshot("feed_page")
                logger.info("Agent {} logged in successfully", self.state.agent_id)
                return True
            else:
                logger.warning("Agent {} login may have failed, URL: {}", self.state.agent_id, self.page.url)
                await self._screenshot("login_result")
                # Continue anyway
                return True

        except Exception as e:
            logger.error("Login failed for {}: {}", self.state.agent_id, e)
            return False

    async def run_step(self) -> dict[str, Any]:
        """Execute a single action step."""
        self.state.step_count += 1

        step_result = {
            "step": self.state.step_count,
            "status": "unknown",
        }

        try:
            # Extract current page content
            page_content = await extract_page_content(self.page) if self.page else ""
            self.state.page_content = page_content

            # Get decision from model
            decision, raw_text, raw_response = await self._get_decision(page_content)
            step_result["decision"] = {
                "action": decision.action,
                "target": decision.target,
                "comment_text": decision.comment_text,
                "reasoning": decision.reasoning,
            }
            step_result["llm"] = {
                "raw_text": raw_text,
                "raw_response": raw_response,
            }

            # Execute the action
            action_result = await self._execute_action(decision)
            step_result["result"] = action_result

            # Take screenshot after action
            if action_result.get("success"):
                await self._screenshot(f"{decision.action}")

            # Track success/failure
            if action_result.get("success"):
                self.state.consecutive_failures = 0
                step_result["status"] = "ok"
            else:
                self.state.consecutive_failures += 1
                self.state.last_error = action_result.get("error")
                step_result["status"] = "failed"

            # Check for done signal
            if decision.action == "done":
                step_result["should_stop"] = True

        except Exception as e:
            self.state.consecutive_failures += 1
            self.state.last_error = str(e)
            step_result["status"] = "error"
            step_result["error"] = str(e)
            logger.exception("Step {} failed for {}", self.state.step_count, self.state.agent_id)

        self._log_action(step_result)
        return step_result

    async def run_loop(
        self,
        max_steps: int | None = None,
        max_time_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Run the agent loop."""
        max_steps = max_steps or self.config.max_steps
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Starting local agent: id={} persona={} max_steps={}",
            self.state.agent_id, self.persona.username, max_steps,
        )

        async with async_playwright() as p:
            # Launch browser - hero agent is headed, others are headless
            headless = not self.is_hero if self.config.headless is None else self.config.headless
            self.browser = await p.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
            )
            self.page = await self.context.new_page()

            # Login first
            logged_in = await self._login()
            if not logged_in:
                logger.error("Agent {} failed to login", self.state.agent_id)
                return {
                    "agentId": self.state.agent_id,
                    "personaId": self.persona.username,
                    "status": "login_failed",
                    "stepsCompleted": 0,
                }

            self.state.is_logged_in = True
            end_reason = "max_steps"

            while self.state.step_count < max_steps:
                # Check time limit
                if max_time_seconds:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                    if elapsed >= max_time_seconds:
                        end_reason = "max_time"
                        break

                # Check consecutive failures
                if self.state.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    end_reason = "consecutive_failures"
                    logger.warning(
                        "Agent {} stopping after {} consecutive failures",
                        self.state.agent_id, self.state.consecutive_failures,
                    )
                    break

                # Execute step
                step_result = await self.run_step()

                # Check for done signal
                if step_result.get("should_stop"):
                    end_reason = "agent_done"
                    break

                # Random delay between steps
                delay = random.uniform(
                    self.config.step_delay_min,
                    self.config.step_delay_max,
                )
                engagement_level = (self.persona.engagement_level or "medium").lower()
                if engagement_level == "high":
                    delay *= 0.7
                elif engagement_level == "low":
                    delay *= 1.3
                await asyncio.sleep(delay)

            # Cleanup
            await self.page.close()
            await self.context.close()
            await self.browser.close()

        elapsed_total = (datetime.now(timezone.utc) - start_time).total_seconds()

        summary = {
            "agentId": self.state.agent_id,
            "personaId": self.persona.username,
            "stepsCompleted": self.state.step_count,
            "actionsLogged": len(self.state.actions_taken),
            "endReason": end_reason,
            "elapsedSeconds": round(elapsed_total, 2),
            "logFile": str(self.log_path),
            "consecutiveFailures": self.state.consecutive_failures,
            "lastError": self.state.last_error,
        }

        logger.info(
            "Agent {} finished: steps={} reason={} elapsed={:.1f}s",
            self.state.agent_id, self.state.step_count, end_reason, elapsed_total,
        )

        return summary


async def run_local_agents_parallel(
    personas: list[Persona],
    agent_count: int = 10,
    max_concurrency: int = 4,
    max_steps_per_agent: int | None = None,
    max_time_per_agent: float | None = None,
    headless: bool | None = None,  # None = auto (hero headed, others headless)
    save_screenshots: bool = False,
    output_dir: Path | None = None,
    hero_enabled: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run multiple local agents in parallel with concurrency control."""
    config = load_local_config(
        headless=headless,
        save_screenshots=save_screenshots,
        output_dir=output_dir,
    )

    # Cycle through personas
    agent_personas = [personas[i % len(personas)] for i in range(agent_count)]

    # Create runners (first one is hero if enabled)
    runners = []
    for i, persona in enumerate(agent_personas):
        is_hero = (i == 0 and hero_enabled)
        runners.append(
            LocalPlaywrightAgent(
                config=config,
                persona=persona,
                agent_index=i + 1,
                is_hero=is_hero,
            )
        )

    # Run with semaphore for concurrency control
    sem = asyncio.Semaphore(max_concurrency)

    async def run_one(runner: LocalPlaywrightAgent) -> dict[str, Any]:
        async with sem:
            try:
                return await runner.run_loop(
                    max_steps=max_steps_per_agent,
                    max_time_seconds=max_time_per_agent,
                )
            except Exception as e:
                logger.exception("Agent {} crashed: {}", runner.state.agent_id, e)
                return {
                    "agentId": runner.state.agent_id,
                    "personaId": runner.persona.username,
                    "status": "crashed",
                    "error": str(e),
                }

    logger.info(
        "Starting {} local agents with max_concurrency={}",
        agent_count, max_concurrency,
    )

    results = await asyncio.gather(*[run_one(r) for r in runners])

    # Calculate metrics
    completed = sum(1 for r in results if r.get("endReason") and r.get("endReason") != "crashed")
    crashed = sum(1 for r in results if r.get("status") == "crashed")
    total_steps = sum(r.get("stepsCompleted", 0) for r in results)
    total_actions = sum(r.get("actionsLogged", 0) for r in results)

    metrics = {
        "totalAgents": agent_count,
        "completed": completed,
        "crashed": crashed,
        "totalSteps": total_steps,
        "totalActions": total_actions,
    }

    logger.info(
        "All agents finished: completed={} crashed={} total={}",
        completed, crashed, agent_count,
    )

    return list(results), metrics


# CLI entry point for testing
if __name__ == "__main__":
    import argparse
    from runner import configure_logger

    # Setup argument parser with good defaults
    parser = argparse.ArgumentParser(
        description="Run multi-agent SNS simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--num-agents",
        type=int,
        default=3,
        help="Number of agents to run",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum steps per agent",
    )
    parser.add_argument(
        "--all-headed",
        action="store_true",
        help="Run all agents with visible browser (default: first agent headed, rest headless)",
    )
    parser.add_argument(
        "--all-headless",
        action="store_true",
        help="Run all agents headless",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Save screenshots during execution",
    )
    args = parser.parse_args()

    # Determine headless mode
    if args.all_headed:
        headless = False
    elif args.all_headless:
        headless = True
    else:
        headless = None  # auto: hero headed, others headless

    # Configure logging
    configure_logger("INFO")

    # Load personas from sns-vibe/seeds/personas.json
    personas = load_personas_from_seeds()
    if not personas:
        logger.error("No personas loaded, exiting")
        import sys
        sys.exit(1)

    logger.info(
        "Running {} agents with {} steps each (headless={})",
        args.num_agents, args.max_steps, headless,
    )

    results, metrics = asyncio.run(
        run_local_agents_parallel(
            personas=personas,
            agent_count=args.num_agents,
            max_concurrency=min(4, args.num_agents),
            max_steps_per_agent=args.max_steps,
            headless=headless,
            save_screenshots=args.screenshots,
        )
    )

    print("\n=== Results ===")
    print(json.dumps(results, indent=2))
    print("\n=== Metrics ===")
    print(json.dumps(metrics, indent=2))
