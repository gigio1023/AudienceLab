import argparse
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "dashboard" / "public" / "simulation"
SEED_POSTS_PATH = REPO_ROOT / "sns-vibe" / "seeds" / "posts.json"
FEED_INDEX_CANDIDATES = [DATA_DIR / "__files.json", DATA_DIR / "index.json"]
MARKETING_TAGS = ("#ad", "#sponsored")
SCHEMA_VERSION = "1.0"

SHARED_RESULTS_DIR = REPO_ROOT / "shared" / "evaluation" / "results"
DASHBOARD_RESULTS_DIR = REPO_ROOT / "dashboard" / "public" / "evaluation" / "results"
DASHBOARD_LATEST_PATH = REPO_ROOT / "dashboard" / "public" / "evaluation" / "latest.json"

# Load env from agent directory if present
agent_env = REPO_ROOT / "agent" / ".env"
if agent_env.exists():
    load_dotenv(agent_env)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MAX_WORKERS = int(os.getenv("OPENAI_MAX_WORKERS", "16"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required to run the evaluator.")

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)


class JudgeResult(BaseModel):
    relevance_score: int = Field(description="1-5 score on relevance to context/reasoning")
    tone_score: int = Field(description="1-5 score on appropriate tone for the persona")
    consistency_score: int = Field(description="1-5 score on consistency between reasoning and action")
    explanation: str


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate agent engagement logs")
    parser.add_argument(
        "--expected",
        dest="expected_path",
        default=os.getenv("EVALUATION_EXPECTED_PATH", ""),
        help="Path to expected evaluation JSON",
    )
    parser.add_argument(
        "--evaluation-id",
        dest="evaluation_id",
        default=os.getenv("EVALUATION_ID", ""),
        help="Evaluation ID (default: generated)",
    )
    parser.add_argument(
        "--simulation-id",
        dest="simulation_id",
        default=os.getenv("SIMULATION_ID", ""),
        help="Simulation ID to attach to the evaluation",
    )
    parser.add_argument(
        "--run-id",
        dest="run_id",
        default=os.getenv("SIMULATION_RUN_ID", ""),
        help="Run ID to attach to the evaluation",
    )
    return parser.parse_args()


def evaluate_comment(reasoning: str | None, comment: str) -> JudgeResult | None:
    prompt = f"""
    Evaluate the following social media comment action performed by an AI agent.

    Agent Reasoning for Action: "{reasoning}"
    Actual Comment Posted: "{comment}"

    Assess the quality of this interaction:
    1. Relevance: Does the comment actually address the topic mentions in the reasoning?
    2. Tone: Is the comment style appropriate (supportive, casual, etc) as implied by the reasoning?
    3. Consistency: Does the actual comment match the intent described in the reasoning?

    Provide integer scores (1-5) for each and a brief explanation.
    """

    try:
        completion = client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a social media engagement evaluator evaluating AI agent performance."},
                {"role": "user", "content": prompt},
            ],
            response_format=JudgeResult,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"LLM Call failed: {e}")
        return None


def load_expected(path_value: str) -> dict | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    if not path.exists():
        print(f"Expected file not found: {path}")
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_persona_id(path: Path) -> str | None:
    stem = path.stem
    if "__" not in stem:
        return None
    return stem.split("__", 1)[1] or None


def load_feed_files() -> list[Path]:
    for candidate in FEED_INDEX_CANDIDATES:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as file:
                index = json.load(file)
            files = [DATA_DIR / name for name in index.get("files", [])]
            return [f for f in files if f.exists()]
    return list(DATA_DIR.glob("*.jsonl"))


def normalize_target_id(target: str | None, seed_ids: set[str]) -> str | None:
    if not target:
        return None
    if target in seed_ids:
        return target
    if target.startswith("post-"):
        raw = target[len("post-"):]
        if raw.isdigit():
            return raw.zfill(3)
        return raw
    return target


def metric(expected: float, actual: float) -> dict:
    abs_error = abs(actual - expected)
    if expected == 0:
        relative_error = 0 if actual == 0 else 1
        similarity = 1.0 if actual == 0 else 0.0
    else:
        relative_error = abs_error / expected
        similarity = max(0.0, 1 - relative_error)
    return {
        "expected": expected,
        "actual": actual,
        "absError": abs_error,
        "relativeError": relative_error,
        "similarity": similarity,
    }


def weighted_similarity(metrics: dict, weights: dict | None) -> float | None:
    items = []
    for key, value in metrics.items():
        if not isinstance(value, dict) or "similarity" not in value:
            continue
        items.append((key, value["similarity"]))
    if not items:
        return None
    if not weights:
        return sum(sim for _, sim in items) / len(items)
    weight_sum = 0.0
    weighted_total = 0.0
    for key, sim in items:
        weight = float(weights.get(key, 0.0))
        if weight <= 0:
            continue
        weighted_total += weight * sim
        weight_sum += weight
    if weight_sum == 0:
        return sum(sim for _, sim in items) / len(items)
    return weighted_total / weight_sum


def compute_rates(count: int, total: int) -> float:
    return count / total if total > 0 else 0.0


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    expected_payload = load_expected(args.expected_path)

    evaluation_id = (
        args.evaluation_id
        or (expected_payload or {}).get("evaluationId")
        or f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    )
    simulation_id = args.simulation_id or (expected_payload or {}).get("simulationId")
    run_id = args.run_id or (expected_payload or {}).get("runId")

    if not SEED_POSTS_PATH.exists():
        print(f"Missing seed posts file: {SEED_POSTS_PATH}")
        return

    with SEED_POSTS_PATH.open("r", encoding="utf-8") as file:
        seed_posts = json.load(file)

    seed_ids = {post["id"] for post in seed_posts}
    marketing_post_ids = {
        post["id"]
        for post in seed_posts
        if any(tag in post.get("content", "").lower() for tag in MARKETING_TAGS)
    }

    actions = []
    files = load_feed_files()

    print(f"Found {len(files)} log files in {DATA_DIR}")

    for f in files:
        persona_id = extract_persona_id(f)
        agent_id_from_file = f.stem
        with f.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    decision = data.get("decision", {})
                    result = data.get("result", {})
                    target = decision.get("target")
                    normalized_target = normalize_target_id(target, seed_ids)

                    row = {
                        "agent_id": data.get("agentId", agent_id_from_file),
                        "persona_id": persona_id or "unknown",
                        "timestamp": data.get("timestamp"),
                        "step": data.get("step"),
                        "action": decision.get("action"),
                        "success": result.get("success", False),
                        "target": target,
                        "normalized_target": normalized_target,
                        "is_marketing_post": normalized_target in marketing_post_ids,
                        "comment_text": result.get("comment") or decision.get("comment_text"),
                        "reasoning": decision.get("reasoning"),
                    }
                    actions.append(row)
                except Exception as e:
                    print(f"Skipping bad line in {f}: {e}")
                    continue

    df = pd.DataFrame(actions)
    quality_grade = "N/A"
    quality_msg = "No comments evaluated."
    avg_quality_score = 0.0

    if df.empty:
        print("No actions found.")
        total_steps = 0
        total_agents = 0
        engagements = pd.DataFrame()
        engagement_count = 0
        engagement_rate = 0.0
        marketing_engagement_count = 0
        marketing_engagement_rate = 0.0
        judge_results = []
        avg_scores = None
    else:
        total_steps = len(df)
        total_agents = df["agent_id"].nunique()

        engagements = df[(df["success"] == True) & (df["action"].isin(["like", "comment", "follow"]))]
        engagement_count = len(engagements)
        engagement_rate = compute_rates(engagement_count, total_steps)

        marketing_engagements = engagements[
            (engagements["is_marketing_post"] == True)
            & (engagements["action"].isin(["like", "comment"]))
        ]
        marketing_engagement_count = len(marketing_engagements)
        marketing_engagement_rate = compute_rates(marketing_engagement_count, total_steps)

        action_counts = df.groupby(["action", "success"]).size().unstack(fill_value=0)

        print("\n=== Quantitative Metrics ===")
        print(f"Total Agents: {total_agents}")
        print(f"Total Steps: {total_steps}")
        print(f"Total Engagements (Like/Comment/Follow): {engagement_count}")
        print(f"Engagement Rate: {engagement_rate:.2%}")
        print(f"Marketing Engagements (Like/Comment): {marketing_engagement_count}")
        print(f"Marketing Engagement Rate: {marketing_engagement_rate:.2%}")
        print("\nAction Distribution:")
        print(action_counts)

        comments = df[
            (df["action"] == "comment")
            & (df["success"] == True)
            & (df["is_marketing_post"] == True)
            & (df["comment_text"].notna())
            & (df["comment_text"] != "")
        ]

        judge_results = []
        if not comments.empty:
            print(f"\n=== LLM Judge Evaluation ({len(comments)} comments) ===")
            print("Running LLM evaluation (this may take a moment)...")

            comment_rows = list(comments.to_dict(orient="records"))
            worker_count = max(1, min(OPENAI_MAX_WORKERS, len(comment_rows)))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(evaluate_comment, row["reasoning"], row["comment_text"]): row
                    for row in comment_rows
                }
                for future in as_completed(futures):
                    row = futures[future]
                    res = future.result()
                    if res:
                        judge_results.append(
                            {
                                "agent_id": row["agent_id"],
                                "persona_id": row["persona_id"],
                                "step": row["step"],
                                "comment": row["comment_text"],
                                "reasoning": row["reasoning"],
                                "relevance": res.relevance_score,
                                "tone": res.tone_score,
                                "consistency": res.consistency_score,
                                "explanation": res.explanation,
                            }
                        )
                        print(
                            f"[{row['agent_id']}]: R={res.relevance_score} T={res.tone_score} C={res.consistency_score}"
                        )
        else:
            print("\nNo successful marketing comments found to evaluate.")

        print("\n=== Performance Verdict (종합 평가) ===")

        if marketing_engagement_rate >= 0.5:
            eng_grade = "High (active)"
            eng_msg = "Strong interaction with marketing posts."
        elif marketing_engagement_rate >= 0.2:
            eng_grade = "Medium (steady)"
            eng_msg = "Reasonable interaction with marketing posts."
        else:
            eng_grade = "Low (passive)"
            eng_msg = "Low interaction with marketing posts."

        print(f"Engagement Level: {eng_grade}")
        print(f"Comment: {eng_msg}")

        if judge_results:
            judged_df = pd.DataFrame(judge_results)
            avg_scores = judged_df[["relevance", "tone", "consistency"]].mean()
            avg_quality_score = float(avg_scores.mean())

            if avg_quality_score >= 4.5:
                quality_grade = "Excellent"
                quality_msg = "Comments closely match persona and context."
            elif avg_quality_score >= 4.0:
                quality_grade = "Good"
                quality_msg = "Generally strong quality with minor gaps."
            elif avg_quality_score >= 3.0:
                quality_grade = "Fair"
                quality_msg = "Acceptable but could be more contextual."
            else:
                quality_grade = "Poor"
                quality_msg = "Low quality comments; improve prompts or logic."

            print(f"Quality Score: {avg_quality_score:.2f} / 5.0")
            print(f"Quality Grade: {quality_grade}")
            print(f"Comment: {quality_msg}")
        else:
            avg_scores = None

        if judge_results:
            print("\n--- Average Quality Scores ---")
            print(avg_scores)

    like_count = int(df[(df["success"] == True) & (df["action"] == "like")].shape[0]) if not df.empty else 0
    comment_count = int(df[(df["success"] == True) & (df["action"] == "comment")].shape[0]) if not df.empty else 0
    like_rate = compute_rates(like_count, total_steps)
    comment_rate = compute_rates(comment_count, total_steps)

    per_persona_actual = {}
    if not df.empty:
        for persona_id, group in df.groupby("persona_id"):
            persona_total_steps = len(group)
            persona_like_count = int(group[(group["success"] == True) & (group["action"] == "like")].shape[0])
            persona_comment_count = int(group[(group["success"] == True) & (group["action"] == "comment")].shape[0])
            per_persona_actual[persona_id] = {
                "totalSteps": persona_total_steps,
                "likeCount": persona_like_count,
                "commentCount": persona_comment_count,
                "likeRate": compute_rates(persona_like_count, persona_total_steps),
                "commentRate": compute_rates(persona_comment_count, persona_total_steps),
            }

    expected = (expected_payload or {}).get("expected") if expected_payload else None
    expected_per_persona = (expected_payload or {}).get("perPersona") if expected_payload else None
    weights = (expected_payload or {}).get("weights") if expected_payload else None

    expected_like = float(expected.get("likeCount", like_count)) if expected else like_count
    expected_comment = float(expected.get("commentCount", comment_count)) if expected else comment_count
    expected_like_rate = float(expected.get("likeRate", like_rate)) if expected else like_rate
    expected_comment_rate = float(expected.get("commentRate", comment_rate)) if expected else comment_rate

    metrics = {
        "likeCount": metric(expected_like, like_count),
        "commentCount": metric(expected_comment, comment_count),
        "likeRate": metric(expected_like_rate, like_rate),
        "commentRate": metric(expected_comment_rate, comment_rate),
    }
    metrics["overallSimilarity"] = weighted_similarity(metrics, weights)

    per_persona_metrics = {}
    if per_persona_actual:
        for persona_id, actual_values in per_persona_actual.items():
            persona_expected = expected_per_persona.get(persona_id, {}) if expected_per_persona else {}
            persona_metrics = {
                "likeCount": metric(float(persona_expected.get("likeCount", actual_values["likeCount"])), actual_values["likeCount"]),
                "commentCount": metric(float(persona_expected.get("commentCount", actual_values["commentCount"])), actual_values["commentCount"]),
                "likeRate": metric(float(persona_expected.get("likeRate", actual_values["likeRate"])), actual_values["likeRate"]),
                "commentRate": metric(float(persona_expected.get("commentRate", actual_values["commentRate"])), actual_values["commentRate"]),
            }
            per_persona_metrics[persona_id] = persona_metrics

    evaluation_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "evaluationId": evaluation_id,
        "simulationId": simulation_id,
        "runId": run_id,
        "createdAt": iso_now(),
        "input": {
            "expectedPath": str(Path(args.expected_path).expanduser())
            if args.expected_path
            else "not-provided",
        },
        "actual": {
            "totals": {
                "totalSteps": total_steps,
                "totalAgents": total_agents,
                "engagementCount": engagement_count,
                "engagementRate": engagement_rate,
                "marketingEngagementCount": marketing_engagement_count,
                "marketingEngagementRate": marketing_engagement_rate,
                "likeCount": like_count,
                "commentCount": comment_count,
                "likeRate": like_rate,
                "commentRate": comment_rate,
                "qualityAverage": avg_quality_score,
                "qualityGrade": quality_grade,
            },
            "perPersona": per_persona_actual,
        },
        "metrics": metrics,
    }

    if expected_payload:
        evaluation_payload["input"].update(
            {
                "expected": expected_payload.get("expected"),
                "perPersona": expected_payload.get("perPersona"),
                "weights": expected_payload.get("weights"),
            }
        )

    if per_persona_metrics:
        evaluation_payload["perPersona"] = per_persona_metrics

    shared_path = SHARED_RESULTS_DIR / f"{evaluation_id}.json"
    write_json(shared_path, evaluation_payload)

    dashboard_result_path = DASHBOARD_RESULTS_DIR / f"{evaluation_id}.json"
    write_json(dashboard_result_path, evaluation_payload)
    write_json(DASHBOARD_LATEST_PATH, evaluation_payload)

    print("\n=== Evaluation Output ===")
    print(f"Shared: {shared_path}")
    print(f"Dashboard: {dashboard_result_path}")
    print(f"Dashboard latest: {DASHBOARD_LATEST_PATH}")


if __name__ == "__main__":
    main()
