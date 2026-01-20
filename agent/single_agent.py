"""Single agent runner for testing.

Usage:
    python single_agent.py          # Traditional Playwright mode
    python single_agent.py --mcp    # MCP-based mode
"""

import argparse
import asyncio

from runner import build_simulation_config, default_post_context, load_personas, run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single hero agent")
    parser.add_argument("--mcp", action="store_true", help="Use MCP-based execution")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    personas = load_personas()
    persona = personas[0]
    config = build_simulation_config(
        goal="Single hero agent run on local SNS",
        budget=10,
        duration=0.5,
        target_persona=persona.id,
        message_tone=persona.tone,
        crowd_count=0,
        hero_enabled=True,
        hero_mode="auto",
        hero_persona_id=persona.id,
        post_context=default_post_context(),
        dry_run=False,
        save_screenshots=True,
        headless=not args.headed,
        max_concurrency=1,
        mcp_enabled=args.mcp,
    )
    asyncio.run(run_simulation(config, personas))


if __name__ == "__main__":
    main()
