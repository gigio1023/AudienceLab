import asyncio

from runner import build_simulation_config, default_post_context, load_personas, run_simulation


def main() -> None:
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
        hero_persona_id=persona.id,
        post_context=default_post_context(),
        dry_run=False,
        save_screenshots=True,
        headless=True,
        max_concurrency=1,
    )
    asyncio.run(run_simulation(config, personas))


if __name__ == "__main__":
    main()
