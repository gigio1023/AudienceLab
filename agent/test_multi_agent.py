"""Multi-agent test: 1 headed + 3 headless, 100 actions each."""
import asyncio
from pathlib import Path

from local_agent import (
    LocalAgentConfig,
    LocalPlaywrightAgent,
    Persona,
    load_local_config,
)
from runner import load_personas, configure_logger


async def run_multi_agents():
    configure_logger("INFO")

    # Load personas
    personas_data = load_personas()
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

    # Create configs
    output_dir = Path(__file__).parent / "outputs" / "multi_agent_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1 headed + 3 headless = 4 agents total
    configs = []

    # Agent 1: headed
    configs.append(load_local_config(headless=False, save_screenshots=True, output_dir=output_dir))

    # Agent 2-4: headless
    for _ in range(3):
        configs.append(load_local_config(headless=True, save_screenshots=False, output_dir=output_dir))

    # Create agents
    agents = []
    for i, config in enumerate(configs):
        persona = personas[i % len(personas)]
        agent = LocalPlaywrightAgent(
            config=config,
            persona=persona,
            agent_index=i + 1,
            is_hero=(i == 0),
        )
        agents.append(agent)

    # Run all agents concurrently
    async def run_agent(agent: LocalPlaywrightAgent, max_steps: int):
        try:
            return await agent.run_loop(max_steps=max_steps, max_time_seconds=300)
        except Exception as e:
            return {"agentId": agent.state.agent_id, "error": str(e)}

    print(f"Starting {len(agents)} agents (1 headed, 3 headless), 100 steps each...")

    results = await asyncio.gather(*[run_agent(a, 100) for a in agents])

    print("\n=== Results ===")
    for r in results:
        print(f"  {r.get('agentId')}: steps={r.get('stepsCompleted', 0)} reason={r.get('endReason', 'unknown')}")

    return results


if __name__ == "__main__":
    asyncio.run(run_multi_agents())
