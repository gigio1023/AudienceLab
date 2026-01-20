"""Test script for MCP-based agent execution.

Usage:
    python test_mcp.py                  # Run with 2 agents, 5 steps each
    python test_mcp.py --agents 10      # Run with 10 agents
    python test_mcp.py --steps 10       # Run with 10 steps per agent
    python test_mcp.py --dry-run        # Skip MCP calls, test flow only
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from runner import (
    build_simulation_config,
    configure_logger,
    default_post_context,
    load_personas,
    run_simulation,
    summarize_run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test MCP agent execution")
    parser.add_argument("--agents", type=int, default=2, help="Number of agents to run")
    parser.add_argument("--steps", type=int, default=5, help="Max steps per agent")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual MCP calls")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--no-hero", action="store_true", help="Disable hero agent")
    parser.add_argument("--concurrency", type=int, default=4, help="Max concurrent agents")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    log_level = "DEBUG" if args.verbose else "INFO"
    configure_logger(log_level)

    personas = load_personas()

    # Determine crowd count based on hero setting
    if args.no_hero:
        crowd_count = args.agents
        hero_enabled = False
    else:
        # First agent is hero, rest are crowd
        crowd_count = max(0, args.agents - 1)
        hero_enabled = True

    config = build_simulation_config(
        goal="MCP Agent Test Run",
        budget=10,
        duration=0.5,  # 30 seconds max per agent
        target_persona=personas[0].id,
        message_tone=personas[0].tone,
        crowd_count=crowd_count,
        hero_enabled=hero_enabled,
        hero_mode="auto",
        hero_persona_id=personas[0].id if hero_enabled else None,
        post_context=default_post_context(),
        dry_run=args.dry_run,
        save_screenshots=False,
        headless=True,
        max_concurrency=args.concurrency,
        mcp_enabled=True,  # Enable MCP mode
    )

    print(f"Starting MCP test with {args.agents} agents ({crowd_count} crowd + {'1 hero' if hero_enabled else 'no hero'})")
    print(f"Max steps per agent: {args.steps}")
    print(f"Max concurrency: {args.concurrency}")
    print(f"Dry run: {args.dry_run}")
    print()

    try:
        summary = await run_simulation(config, personas)
        print()
        print("=" * 60)
        print("SIMULATION COMPLETE")
        print("=" * 60)
        print(summarize_run(summary))
        print()
        print(f"Simulation file: {summary.simulation_path}")
        print(f"Action files: {len(summary.action_files)}")

        # Print metrics
        if summary.metrics:
            print()
            print("Metrics:")
            print(json.dumps(summary.metrics, indent=2))

        return 0 if summary.status == "completed" else 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
