"""MCP-based Playwright agent runner.

This module implements the MCP (Model Context Protocol) integration for
browser automation using Playwright MCP server. The model decides and
executes actions through MCP tool calls.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from accounts import (
    AGENT_EMAILS,
    DEFAULT_PASSWORD,
    SNS_URL_DEFAULT,
    get_agent_email,
)

# Action types the model can choose
ACTION_TYPES = ["like", "comment", "follow", "scroll_up", "scroll_down", "noop"]

# Maximum consecutive failures before stopping
MAX_CONSECUTIVE_FAILURES = 3

# Default max steps per agent loop
DEFAULT_MAX_STEPS = 35

# Default step delay range (seconds)
DEFAULT_STEP_DELAY_MIN = 1.0
DEFAULT_STEP_DELAY_MAX = 3.0

# Session intent defaults (lightly randomized to avoid robotic patterns)
SESSION_INTENTS = [
    "catch up on friends",
    "discover new creators",
    "look for tips and inspiration",
    "skim quickly while waiting",
    "relax and browse",
]


@dataclass
class MCPConfig:
    """Configuration for MCP-based agent."""
    playwright_mcp_url: str
    require_approval: str  # "never", "always", or specific conditions
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    sns_url: str
    max_steps: int
    step_delay_min: float
    step_delay_max: float


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
    """Runtime state for an MCP agent."""
    agent_id: str
    persona: Persona
    username: str
    password: str
    current_url: str
    step_count: int
    consecutive_failures: int
    actions_taken: list[dict[str, Any]]
    is_logged_in: bool
    last_error: str | None
    session_intent: str


def iso_now() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def pick_session_intent(persona: Persona) -> str:
    """Choose a light session intent based on persona interests."""
    if persona.interests:
        topic = random.choice(persona.interests)
        return f"browse for {topic} posts"
    return random.choice(SESSION_INTENTS)


def safe_slug(value: str) -> str:
    """Normalize a value for filenames."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or "unknown"


def load_mcp_config() -> MCPConfig:
    """Load MCP configuration from environment."""
    agent_dir = Path(__file__).resolve().parent
    load_dotenv(agent_dir / ".env")

    return MCPConfig(
        playwright_mcp_url=os.getenv("PLAYWRIGHT_MCP_URL", "http://localhost:8931/mcp"),
        require_approval=os.getenv("MCP_REQUIRE_APPROVAL", "never"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        sns_url=os.getenv("SNS_URL", SNS_URL_DEFAULT).rstrip("/"),
        max_steps=int(os.getenv("MCP_MAX_STEPS", str(DEFAULT_MAX_STEPS))),
        step_delay_min=float(os.getenv("MCP_STEP_DELAY_MIN", str(DEFAULT_STEP_DELAY_MIN))),
        step_delay_max=float(os.getenv("MCP_STEP_DELAY_MAX", str(DEFAULT_STEP_DELAY_MAX))),
    )


def build_openai_client(config: MCPConfig) -> OpenAI:
    """Build OpenAI client with optional custom base URL."""
    if config.openai_base_url:
        return OpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
    return OpenAI(api_key=config.openai_api_key)


def build_mcp_tools(config: MCPConfig) -> list[dict[str, Any]]:
    """Build MCP tool configuration for Playwright."""
    return [
        {
            "type": "mcp",
            "server_label": "playwright",
            "server_url": config.playwright_mcp_url,
            "require_approval": config.require_approval,
        }
    ]


def build_system_prompt(persona: Persona, config: MCPConfig, session_intent: str) -> str:
    """Build system prompt for the MCP agent."""
    return f"""You are a social media user controlling a browser through Playwright MCP tools.
You have a specific persona and should act according to it.

## Your Persona
- Name: {persona.name}
- Interests: {', '.join(persona.interests)}
- Tone: {persona.tone}
- Reaction bias: {persona.reaction_bias}
- Session intent: {session_intent}

## Rules
1. You are browsing a local SNS at {config.sns_url}.
2. Do NOT navigate to external sites or domains.
3. Available actions: like, comment, follow, scroll_up, scroll_down, noop.
4. Make decisions based on your persona's interests and reaction bias.
5. Act naturally - don't like/comment on everything.
6. Avoid repeating the same action more than twice in a row.
7. If an action fails, don't retry - just move on.

## Action Guidelines by Persona Bias
- positive: Like ~60% of relevant posts, comment ~30%, follow occasionally
- neutral: Like ~30% of relevant posts, comment ~15%, rarely follow
- negative: Like ~10% of posts, comment ~5% (often critical), almost never follow

## Tool Calling Rules
- Always call browser_snapshot at the start of each step.
- Use the snapshot to find real post IDs (e.g., #post-17).
- Only click/type when a valid selector is visible; otherwise scroll or noop.
- After any navigation or action that changes the page, call browser_snapshot again to confirm.
- Never claim you clicked/typed without using a tool.

## SNS-Vibe Interface Guide
The SNS uses these DOM elements:
- Login page: input#username for username entry, button[type="submit"] to login
- Feed page: #feed contains all posts
- Each post: #post-{{id}} with like button #like-button-{{id}}, comment input #comment-input-{{id}}, comment button #comment-button-{{id}}
- User profiles: #user-{{user_id}} for user links
- New post: #new-post-input (textarea), #new-post-button
- Logout: #logout-button

## Important
- Use Playwright MCP tools to interact with the page.
- First navigate to the SNS URL if not there.
- After each action, report what you did in a brief JSON format:
  {{"action": "<type>", "target": "<element>", "success": true/false, "reasoning": "<why>"}}
"""


def build_action_prompt(
    state: AgentState,
    post_candidates: list[dict[str, Any]],
    page_snapshot: str | None = None,
) -> str:
    """Build the action decision prompt for a step."""
    recent_actions = []
    recent_targets = []
    for entry in state.actions_taken[-5:]:
        action = (
            entry.get("action_result", {}).get("action")
            or entry.get("action")
            or entry.get("response", {}).get("action")
        )
        target = (
            entry.get("action_result", {}).get("target")
            or entry.get("target")
            or entry.get("response", {}).get("target")
        )
        if action:
            recent_actions.append(action)
        if target:
            recent_targets.append(str(target))

    candidates_text = ""
    if post_candidates:
        for idx, post in enumerate(post_candidates[:5]):  # Limit to 5 posts
            candidates_text += f"\n{idx+1}. @{post.get('username', 'unknown')}: {post.get('content', '')[:100]}..."
            if post.get('hashtags'):
                candidates_text += f" (tags: {', '.join(post['hashtags'][:3])})"
    else:
        candidates_text = "\nNo post context provided. Use browser_snapshot to see the page."

    snapshot_text = ""
    if page_snapshot:
        snapshot_text = f"\n\nCurrent page snapshot:\n{page_snapshot[:2000]}"

    return f"""Current state:
- URL: {state.current_url}
- Step: {state.step_count}
- Actions so far: {len(state.actions_taken)}
- Logged in: {state.is_logged_in}
- Recent actions: {", ".join(recent_actions) if recent_actions else "None"}
- Recent targets: {", ".join(recent_targets) if recent_targets else "None"}
- Session intent: {state.session_intent}

Post context:{candidates_text}{snapshot_text}

## Your Task
Based on your persona ({state.persona.name}, {state.persona.reaction_bias} bias):
1. First use browser_snapshot to see the current page
2. Decide what action to take based on visible posts
3. Execute the action using Playwright MCP tools
4. Avoid repeating the same action or target you used very recently

## Available Actions
- **like**: Click #like-button-{{post_id}} on a post you want to like
- **comment**: Fill #comment-input-{{post_id}} with text, then click #comment-button-{{post_id}}
- **scroll_down**: Use browser_press_key with PageDown or scroll the window
- **scroll_up**: Use browser_press_key with PageUp
- **noop**: Do nothing this step (if no interesting posts)

## MCP Tools to Use
- browser_snapshot: See current page state
- browser_click: Click on elements
- browser_type: Type text into inputs
- browser_press_key: Press keyboard keys
- browser_navigate: Go to a URL

After your action, respond with JSON:
{{"action": "<type>", "target": "<what you interacted with>", "success": true/false, "reasoning": "<why>"}}

Your username is: {state.username}
"""


def build_login_prompt(state: AgentState, config: MCPConfig) -> str:
    """Build prompt for login action."""
    return f"""You need to log in to the SNS first.

Current URL: {state.current_url}
Target SNS: {config.sns_url}
Your username: {state.username}

## Login Steps
1. Use browser_navigate to go to {config.sns_url} (if not already there)
2. Use browser_snapshot to see the page
3. Fill the username input field (selector: input#username) with "{state.username}"
4. Click the login button (selector: button[type="submit"])
5. Use browser_snapshot again to confirm the feed is visible

## Expected Result
After clicking login, you should be redirected to /feed with posts visible.

Use Playwright MCP tools to perform these actions.
After attempting login, respond with a JSON summary:
{{"action": "login", "success": true/false, "reasoning": "<what happened>"}}
"""


def extract_action_result(response_text: str) -> dict[str, Any]:
    """Extract action result JSON from model response."""
    try:
        # Try to find JSON in the response
        text = response_text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Fallback
    return {
        "action": "unknown",
        "success": False,
        "reasoning": "Could not parse response",
        "raw_response": response_text[:500],
    }


def extract_response_text(response: Any) -> str:
    """Extract text content from OpenAI response."""
    if hasattr(response, "output_text"):
        text_value = getattr(response, "output_text")
        if isinstance(text_value, str) and text_value:
            return text_value

    # Try to extract from output structure
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


class MCPAgentRunner:
    """Runs a single MCP-based agent."""

    def __init__(
        self,
        config: MCPConfig,
        persona: Persona,
        agent_index: int,
        output_dir: Path,
    ):
        self.config = config
        self.persona = persona
        self.agent_index = agent_index
        self.output_dir = output_dir
        self.client = build_openai_client(config)
        self.tools = build_mcp_tools(config)

        # Resolve credentials
        email = get_agent_email(agent_index)
        username = email.split("@")[0] if "@" in email else email

        self.state = AgentState(
            agent_id=f"mcp-agent-{agent_index:03d}",
            persona=persona,
            username=username,
            password=DEFAULT_PASSWORD,
            current_url="",
            step_count=0,
            consecutive_failures=0,
            actions_taken=[],
            is_logged_in=False,
            last_error=None,
            session_intent=pick_session_intent(persona),
        )

        # Conversation history for context
        self.messages: list[dict[str, Any]] = []

        # Action log file
        agent_dir = output_dir / self.state.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        persona_slug = safe_slug(self.persona.name)
        self.log_path = agent_dir / f"{persona_slug}.jsonl"

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

    def _call_model(self, user_prompt: str) -> tuple[str, dict[str, Any]]:
        """Call the model with MCP tools."""
        # Build messages
        if not self.messages:
            self.messages.append({
                "role": "system",
                "content": build_system_prompt(self.persona, self.config, self.state.session_intent),
            })

        self.messages.append({
            "role": "user",
            "content": user_prompt,
        })

        try:
            response = self.client.responses.create(
                model=self.config.openai_model,
                tools=self.tools,
                input=self.messages,
                truncation="auto",
            )

            response_text = extract_response_text(response)
            response_dict = response_to_dict(response)

            # Add assistant response to history
            if response_text:
                self.messages.append({
                    "role": "assistant",
                    "content": response_text,
                })

            return response_text, response_dict

        except Exception as e:
            logger.error("Model call failed: {}", e)
            raise

    async def run_step(self, post_candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Execute a single action step."""
        self.state.step_count += 1

        # Build appropriate prompt
        if not self.state.is_logged_in:
            prompt = build_login_prompt(self.state, self.config)
        else:
            prompt = build_action_prompt(
                self.state,
                post_candidates or [],
            )

        step_result = {
            "step": self.state.step_count,
            "prompt_type": "login" if not self.state.is_logged_in else "action",
        }

        try:
            response_text, response_raw = await asyncio.to_thread(
                self._call_model, prompt
            )

            action_result = extract_action_result(response_text)
            step_result["response"] = response_text[:1000]  # Truncate for logging
            step_result["action_result"] = action_result
            step_result["raw_output_length"] = len(json.dumps(response_raw))
            step_result["llm"] = {
                "raw_text": response_text,
                "raw_response": response_raw,
            }

            # Check if login succeeded
            if action_result.get("action") == "login" and action_result.get("success"):
                self.state.is_logged_in = True
                logger.info("Agent {} logged in successfully", self.state.agent_id)

            # Track success/failure
            if action_result.get("success"):
                self.state.consecutive_failures = 0
            else:
                self.state.consecutive_failures += 1
                self.state.last_error = action_result.get("reasoning")

            step_result["status"] = "ok" if action_result.get("success") else "failed"

        except Exception as e:
            self.state.consecutive_failures += 1
            self.state.last_error = str(e)
            step_result["status"] = "error"
            step_result["error"] = str(e)
            logger.exception("Step {} failed for agent {}", self.state.step_count, self.state.agent_id)

        self._log_action(step_result)
        return step_result

    async def run_loop(
        self,
        max_steps: int | None = None,
        max_time_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Run the agent loop until termination condition."""
        max_steps = max_steps or self.config.max_steps
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Starting MCP agent loop: agent={} persona={} max_steps={}",
            self.state.agent_id, self.persona.id, max_steps,
        )

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
            await self.run_step()

            # Random delay between steps
            delay = random.uniform(
                self.config.step_delay_min,
                self.config.step_delay_max,
            )
            await asyncio.sleep(delay)

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


async def run_mcp_agents_parallel(
    personas: list[Persona],
    agent_count: int = 10,
    max_concurrency: int = 4,
    max_steps_per_agent: int | None = None,
    max_time_per_agent: float | None = None,
    output_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Run multiple MCP agents in parallel with concurrency control."""
    config = load_mcp_config()
    output_dir = output_dir or Path(__file__).resolve().parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cycle through personas
    agent_personas = [personas[i % len(personas)] for i in range(agent_count)]

    # Create runners
    runners = [
        MCPAgentRunner(
            config=config,
            persona=persona,
            agent_index=i + 1,
            output_dir=output_dir,
        )
        for i, persona in enumerate(agent_personas)
    ]

    # Run with semaphore for concurrency control
    sem = asyncio.Semaphore(max_concurrency)

    async def run_one(runner: MCPAgentRunner) -> dict[str, Any]:
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
        "Starting {} MCP agents with max_concurrency={}",
        agent_count, max_concurrency,
    )

    results = await asyncio.gather(*[run_one(r) for r in runners])

    # Summary
    completed = sum(1 for r in results if r.get("endReason") and r.get("endReason") != "crashed")
    crashed = sum(1 for r in results if r.get("status") == "crashed")

    logger.info(
        "All agents finished: completed={} crashed={} total={}",
        completed, crashed, agent_count,
    )

    return list(results)


# CLI entry point for testing
if __name__ == "__main__":
    import sys
    from runner import load_personas, configure_logger

    configure_logger("INFO")
    personas = load_personas()

    agent_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    results = asyncio.run(
        run_mcp_agents_parallel(
            personas=personas,
            agent_count=agent_count,
            max_concurrency=min(4, agent_count),
            max_steps_per_agent=max_steps,
        )
    )

    print(json.dumps(results, indent=2))
