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
from loguru import logger
from openai import OpenAI
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

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
DEFAULT_MAX_STEPS = 20


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
    headless: bool
    save_screenshots: bool
    output_dir: Path


@dataclass
class Persona:
    """Agent persona definition."""
    id: str
    name: str
    interests: list[str]
    tone: str
    reaction_bias: str = "neutral"


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
    headless: bool = True,
    save_screenshots: bool = False,
    output_dir: Path | None = None,
) -> LocalAgentConfig:
    """Load configuration from environment."""
    agent_dir = Path(__file__).resolve().parent
    load_dotenv(agent_dir / ".env")

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
        output_dir=output_dir or agent_dir / "outputs",
    )


def build_openai_client(config: LocalAgentConfig) -> OpenAI:
    """Build OpenAI client."""
    if config.openai_base_url:
        return OpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
    return OpenAI(api_key=config.openai_api_key)


def build_decision_system_prompt(persona: Persona, sns_url: str) -> str:
    """Build system prompt for action decision."""
    return f"""You are a social media user deciding what action to take on a feed.
You have a specific persona and should act according to it.

## Your Persona
- Name: {persona.name}
- Interests: {', '.join(persona.interests)}
- Tone: {persona.tone}
- Reaction bias: {persona.reaction_bias}

## Rules
1. You are browsing a local SNS at {sns_url}
2. Available actions: like, comment, follow, scroll_down, scroll_up, noop, done
3. Make decisions based on your persona's interests and reaction bias
4. If you have a positive bias, you're more likely to like/comment
5. If you have a negative bias, you're more critical and selective
6. Act naturally - don't like/comment on everything

## Action Guidelines by Persona Bias
- positive: Like ~60% of relevant posts, comment ~30%, follow interesting users
- neutral: Like ~30% of relevant posts, comment ~15%, rarely follow
- negative: Like ~10% of posts, comment ~5% (often critical), almost never follow

## Response Format
You MUST respond with ONLY valid JSON in this exact format:
{{"action": "<action_type>", "target": "<post_id or user_id or null>", "comment_text": "<text if commenting, else null>", "reasoning": "<brief explanation>"}}

Valid action types: like, comment, follow, scroll_down, scroll_up, noop, done

Examples:
{{"action": "like", "target": "post-123", "comment_text": null, "reasoning": "Post about veganism matches my interests"}}
{{"action": "comment", "target": "post-456", "comment_text": "Great point about climate change!", "reasoning": "Want to engage with environmental content"}}
{{"action": "scroll_down", "target": null, "comment_text": null, "reasoning": "Looking for more interesting posts"}}
{{"action": "noop", "target": null, "comment_text": null, "reasoning": "No interesting posts visible"}}
{{"action": "done", "target": null, "comment_text": null, "reasoning": "Finished browsing for now"}}
"""


def build_decision_user_prompt(state: AgentState, page_content: str) -> str:
    """Build user prompt for action decision."""
    return f"""Current state:
- Step: {state.step_count}
- Actions taken: {len(state.actions_taken)}
- Recent actions: {[a.get('action') for a in state.actions_taken[-5:]]}

## Current Page Content
{page_content[:4000]}

## Your Task
Based on your persona ({state.persona.name}, {state.persona.reaction_bias} bias), decide what action to take.

Remember:
- Look at the post content, usernames, and topics
- Consider if posts match your interests
- Don't over-engage (be selective based on your bias)
- Use "done" if you've done enough actions or the feed is exhausted

Respond with ONLY valid JSON:
{{"action": "<type>", "target": "<id or null>", "comment_text": "<text or null>", "reasoning": "<why>"}}
"""


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
        )

        # Browser resources (set during run)
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        # Output directory
        self.output_dir = config.output_dir / self.state.agent_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "actions.jsonl"

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
            path = self.output_dir / f"{self.state.step_count:03d}_{name}.png"
            await self.page.screenshot(path=str(path))
            return str(path)
        except Exception as e:
            logger.warning("Screenshot failed: {}", e)
            return None

    async def _get_decision(self, page_content: str) -> ActionDecision:
        """Get action decision from OpenAI."""
        try:
            # Build request params - handle different model requirements
            model = self.config.openai_model
            is_new_model = "gpt-5" in model or "o1" in model or "o3" in model

            request_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": build_decision_system_prompt(self.persona, self.config.sns_url)},
                    {"role": "user", "content": build_decision_user_prompt(self.state, page_content)},
                ],
            }

            # Newer models (gpt-5, o1, o3) don't support temperature and use max_completion_tokens
            if is_new_model:
                request_params["max_completion_tokens"] = 500
                # Don't add temperature - these models only support default (1)
            else:
                request_params["max_tokens"] = 500
                request_params["temperature"] = 0.7

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                **request_params,
            )
            response_text = response.choices[0].message.content or ""
            return parse_action_decision(response_text)
        except Exception as e:
            logger.error("Decision call failed: {}", e)
            return ActionDecision(action="noop", reasoning=f"API error: {e}")

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
            decision = await self._get_decision(page_content)
            step_result["decision"] = {
                "action": decision.action,
                "target": decision.target,
                "comment_text": decision.comment_text,
                "reasoning": decision.reasoning,
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
            self.state.agent_id, self.persona.id, max_steps,
        )

        async with async_playwright() as p:
            # Launch browser
            self.browser = await p.chromium.launch(headless=self.config.headless)
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
                    "personaId": self.persona.id,
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
                await asyncio.sleep(delay)

            # Cleanup
            await self.page.close()
            await self.context.close()
            await self.browser.close()

        elapsed_total = (datetime.now(timezone.utc) - start_time).total_seconds()

        summary = {
            "agentId": self.state.agent_id,
            "personaId": self.persona.id,
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
    headless: bool = True,
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
                    "personaId": runner.persona.id,
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
    import sys

    # Simple CLI
    agent_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    headless = "--headed" not in sys.argv

    # Load personas from runner
    from runner import load_personas, configure_logger
    configure_logger("INFO")

    personas_data = load_personas()
    # Convert to local Persona format
    personas = [
        Persona(
            id=p.id,
            name=p.name,
            interests=p.interests,
            tone=p.tone,
            reaction_bias=getattr(p, "reaction_bias", "neutral"),
        )
        for p in personas_data
    ]

    results, metrics = asyncio.run(
        run_local_agents_parallel(
            personas=personas,
            agent_count=agent_count,
            max_concurrency=min(4, agent_count),
            max_steps_per_agent=max_steps,
            headless=headless,
        )
    )

    print("\n=== Results ===")
    print(json.dumps(results, indent=2))
    print("\n=== Metrics ===")
    print(json.dumps(metrics, indent=2))
