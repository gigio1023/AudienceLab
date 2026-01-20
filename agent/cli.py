import argparse
import asyncio
import json
import sys

from evaluator import evaluate_run
from runner import (
    build_simulation_config,
    choose_target_persona,
    default_post_context,
    load_personas,
    run_simulation,
    run_smoke_test,
    summarize_run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persona-driven SNS agent runner (hero + crowd)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a hybrid simulation")
    run_parser.add_argument("--goal", default="Hybrid SNS simulation run")
    run_parser.add_argument("--budget", type=float, default=50)
    run_parser.add_argument("--duration", type=float, default=1)
    run_parser.add_argument("--message-tone", default="neutral")
    run_parser.add_argument("--post-context", default=default_post_context())
    run_parser.add_argument("--crowd-count", type=int, default=8)
    run_parser.add_argument("--no-hero", action="store_true")
    run_parser.add_argument("--hero-persona", default=None)
    run_parser.add_argument("--persona-file", default=None)
    run_parser.add_argument("--target-persona", default=None)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--headed", action="store_true")
    run_parser.add_argument("--no-screenshots", action="store_true")
    run_parser.add_argument("--max-concurrency", type=int, default=6)
    run_parser.add_argument("--simulation-id", default=None)
    run_parser.add_argument("--run-id", default=None)

    smoke_parser = subparsers.add_parser("smoke-test", help="Quick dry-run validation")
    smoke_parser.add_argument("--verbose", action="store_true")

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate actions vs expected data")
    eval_parser.add_argument("--expected", required=True, help="Path to expected evaluation JSON")
    eval_parser.add_argument("--run-id", default=None, help="Run ID under agent/outputs")
    eval_parser.add_argument("--run-dir", default=None, help="Explicit run directory path")
    eval_parser.add_argument("--simulation-file", default=None, help="Simulation JSON path")
    eval_parser.add_argument("--output", default=None, help="Output path for evaluation JSON")
    eval_parser.add_argument("--print-json", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "smoke-test":
        exit_code, message = asyncio.run(run_smoke_test())
        if args.verbose:
            print(message)
        raise SystemExit(exit_code)

    if args.command == "evaluate":
        result = evaluate_run(
            expected_path=args.expected,
            run_id=args.run_id,
            run_dir=args.run_dir,
            simulation_file=args.simulation_file,
            output_path=args.output,
        )
        metrics = result.get("metrics", {})
        overall = metrics.get("overallSimilarity")
        if args.print_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"evaluationId={result.get('evaluationId')} overallSimilarity={overall}")
        raise SystemExit(0)

    personas = load_personas(args.persona_file)
    hero_enabled = not args.no_hero
    headless = not args.headed
    save_screenshots = not args.no_screenshots
    target_persona = args.target_persona or choose_target_persona(
        personas, args.hero_persona
    )

    config = build_simulation_config(
        goal=args.goal,
        budget=args.budget,
        duration=args.duration,
        target_persona=target_persona,
        message_tone=args.message_tone,
        crowd_count=args.crowd_count,
        hero_enabled=hero_enabled,
        hero_persona_id=args.hero_persona,
        post_context=args.post_context,
        dry_run=args.dry_run,
        save_screenshots=save_screenshots,
        headless=headless,
        max_concurrency=args.max_concurrency,
        simulation_id=args.simulation_id,
        run_id=args.run_id,
    )

    if not hero_enabled and config.crowd_count == 0:
        print("Nothing to run: hero disabled and crowd-count=0", file=sys.stderr)
        raise SystemExit(2)

    summary = asyncio.run(run_simulation(config, personas))
    print(summarize_run(summary))


if __name__ == "__main__":
    main()
