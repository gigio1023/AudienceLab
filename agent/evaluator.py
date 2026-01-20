from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


@dataclass
class EvaluationPaths:
    expected_path: Path
    run_dir: Path
    output_path: Path


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
    tmp_path.replace(path)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_agent_dir() -> Path:
    return Path(__file__).resolve().parent


def load_expected(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload


def resolve_run_dir(
    run_id: str | None,
    run_dir: str | None,
    simulation_file: str | None,
) -> Path:
    agent_dir = get_agent_dir()
    outputs_dir = agent_dir / "outputs"

    if run_dir:
        return Path(run_dir).expanduser().resolve()
    if run_id:
        return outputs_dir / run_id
    if simulation_file:
        sim_path = Path(simulation_file).expanduser().resolve()
        if sim_path.exists():
            run_id_from_sim = extract_run_id_from_simulation(sim_path)
            if run_id_from_sim:
                return outputs_dir / run_id_from_sim
    return latest_run_dir(outputs_dir)


def latest_run_dir(outputs_dir: Path) -> Path:
    if not outputs_dir.exists():
        raise FileNotFoundError(f"Outputs dir not found: {outputs_dir}")
    candidates = [path for path in outputs_dir.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError("No run directories found under agent/outputs")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def extract_run_id_from_simulation(sim_path: Path) -> str | None:
    with sim_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    params = payload.get("config", {}).get("parameters", {})
    run_id = params.get("runId")
    if isinstance(run_id, str) and run_id:
        return run_id

    agent_logs = payload.get("result", {}).get("agentLogs") or []
    for entry in agent_logs:
        detail = entry.get("detail", {}) if isinstance(entry, dict) else {}
        output_path = detail.get("outputPath")
        if isinstance(output_path, str) and output_path:
            parts = Path(output_path).parts
            if "outputs" in parts:
                idx = parts.index("outputs")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    return None


def read_actions_from_run_dir(run_dir: Path) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    jsonl_paths = list(run_dir.glob("*/actions.jsonl"))
    if not jsonl_paths:
        raise FileNotFoundError(f"No actions.jsonl found under {run_dir}")

    for jsonl_path in jsonl_paths:
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return actions


def compute_actual_metrics(actions: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "totalActs": 0,
        "likeCount": 0,
        "commentCount": 0,
        "likeRate": 0.0,
        "commentRate": 0.0,
        "engagementCount": 0,
    }
    per_persona: dict[str, dict[str, Any]] = {}

    for action in actions:
        action_block = action.get("action", {})
        if action_block.get("type") != "act" or action_block.get("status") != "ok":
            continue

        totals["totalActs"] += 1

        persona_id = action.get("agent", {}).get("personaId") or "unknown"
        if persona_id not in per_persona:
            per_persona[persona_id] = {
                "totalActs": 0,
                "likeCount": 0,
                "commentCount": 0,
                "likeRate": 0.0,
                "commentRate": 0.0,
                "engagementCount": 0,
            }

        output = action_block.get("output", {})
        result = output.get("result", {}) if isinstance(output, dict) else {}
        liked = bool(result.get("liked"))
        commented = bool(result.get("commented"))

        totals["likeCount"] += 1 if liked else 0
        totals["commentCount"] += 1 if commented else 0

        persona_totals = per_persona[persona_id]
        persona_totals["totalActs"] += 1
        persona_totals["likeCount"] += 1 if liked else 0
        persona_totals["commentCount"] += 1 if commented else 0

    totals["engagementCount"] = totals["likeCount"] + totals["commentCount"]
    if totals["totalActs"] > 0:
        totals["likeRate"] = totals["likeCount"] / totals["totalActs"]
        totals["commentRate"] = totals["commentCount"] / totals["totalActs"]

    for persona_totals in per_persona.values():
        persona_totals["engagementCount"] = (
            persona_totals["likeCount"] + persona_totals["commentCount"]
        )
        if persona_totals["totalActs"] > 0:
            persona_totals["likeRate"] = (
                persona_totals["likeCount"] / persona_totals["totalActs"]
            )
            persona_totals["commentRate"] = (
                persona_totals["commentCount"] / persona_totals["totalActs"]
            )

    return {"totals": totals, "perPersona": per_persona}


def similarity_count(expected: float, actual: float) -> dict[str, Any]:
    abs_error = abs(actual - expected)
    denom = expected if expected > 0 else 1.0
    relative_error = abs_error / denom
    similarity = max(0.0, 1.0 - relative_error)
    return {
        "expected": expected,
        "actual": actual,
        "absError": abs_error,
        "relativeError": relative_error,
        "similarity": similarity,
    }


def similarity_rate(expected: float, actual: float) -> dict[str, Any]:
    abs_error = abs(actual - expected)
    similarity = max(0.0, 1.0 - abs_error)
    return {
        "expected": expected,
        "actual": actual,
        "absError": abs_error,
        "relativeError": abs_error,
        "similarity": similarity,
    }


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {key: value / total for key, value in weights.items()}


def compute_similarity_block(
    expected: dict[str, Any],
    actual: dict[str, Any],
    weights: dict[str, float],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    active_weights: dict[str, float] = {}

    if "likeCount" in expected:
        metrics["likeCount"] = similarity_count(
            float(expected["likeCount"]), float(actual.get("likeCount", 0))
        )
        active_weights["likeCount"] = weights.get("likeCount", 0.0)

    if "commentCount" in expected:
        metrics["commentCount"] = similarity_count(
            float(expected["commentCount"]), float(actual.get("commentCount", 0))
        )
        active_weights["commentCount"] = weights.get("commentCount", 0.0)

    if "likeRate" in expected:
        metrics["likeRate"] = similarity_rate(
            float(expected["likeRate"]), float(actual.get("likeRate", 0.0))
        )
        active_weights["likeRate"] = weights.get("likeRate", 0.0)

    if "commentRate" in expected:
        metrics["commentRate"] = similarity_rate(
            float(expected["commentRate"]), float(actual.get("commentRate", 0.0))
        )
        active_weights["commentRate"] = weights.get("commentRate", 0.0)

    normalized = normalize_weights(active_weights)
    if not normalized or sum(normalized.values()) == 0:
        overall = None
    else:
        overall = 0.0
        for key, weight in normalized.items():
            overall += metrics[key]["similarity"] * weight

    metrics["overallSimilarity"] = overall
    return metrics


def evaluate_actions(
    expected_payload: dict[str, Any],
    actual_payload: dict[str, Any],
) -> dict[str, Any]:
    expected = expected_payload.get("expected", {}) if isinstance(expected_payload, dict) else {}
    weights = expected_payload.get("weights", {}) if isinstance(expected_payload, dict) else {}
    if not weights:
        weights = {
            "likeCount": 0.5,
            "commentCount": 0.5,
            "likeRate": 0.0,
            "commentRate": 0.0,
        }

    metrics = compute_similarity_block(expected, actual_payload["totals"], weights)

    per_persona_expected = expected_payload.get("perPersona", {})
    per_persona_metrics: dict[str, Any] = {}
    if isinstance(per_persona_expected, dict) and per_persona_expected:
        for persona_id, expected_persona in per_persona_expected.items():
            if not isinstance(expected_persona, dict):
                continue
            actual_persona = actual_payload["perPersona"].get(persona_id, {})
            persona_weights = dict(weights)
            persona_weight_override = expected_persona.get("weights")
            if isinstance(persona_weight_override, dict):
                persona_weights.update(persona_weight_override)
            per_persona_metrics[persona_id] = compute_similarity_block(
                expected_persona,
                actual_persona,
                persona_weights,
            )

    return {
        "metrics": metrics,
        "perPersona": per_persona_metrics,
    }


def sanitize_filename(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-")
    return safe or str(uuid.uuid4())


def resolve_paths(
    expected_path: str,
    run_id: str | None,
    run_dir: str | None,
    simulation_file: str | None,
    output_path: str | None,
    expected_payload: dict[str, Any] | None,
) -> EvaluationPaths:
    repo_root = get_repo_root()
    expected = Path(expected_path).expanduser().resolve()
    resolved_run_dir = resolve_run_dir(run_id, run_dir, simulation_file)

    if output_path:
        output = Path(output_path).expanduser().resolve()
    else:
        output_dir = repo_root / "shared" / "evaluation" / "results"
        ensure_dir(output_dir)
        evaluation_id = None
        if expected_payload:
            value = expected_payload.get("evaluationId")
            if isinstance(value, str) and value.strip():
                evaluation_id = sanitize_filename(value)
        if not evaluation_id:
            evaluation_id = str(uuid.uuid4())
        output = output_dir / f"{evaluation_id}.json"

    return EvaluationPaths(expected_path=expected, run_dir=resolved_run_dir, output_path=output)


def build_evaluation_result(
    expected_payload: dict[str, Any],
    actual: dict[str, Any],
    similarity: dict[str, Any],
    paths: EvaluationPaths,
) -> dict[str, Any]:
    evaluation_id = expected_payload.get("evaluationId") or paths.output_path.stem
    simulation_id = expected_payload.get("simulationId")
    run_id = expected_payload.get("runId") or paths.run_dir.name

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "evaluationId": str(evaluation_id),
        "simulationId": simulation_id,
        "runId": run_id,
        "createdAt": iso_now(),
        "input": {
            "expectedPath": str(paths.expected_path),
            "expected": expected_payload.get("expected", {}),
            "perPersona": expected_payload.get("perPersona", {}),
            "weights": expected_payload.get("weights", {}),
        },
        "actual": actual,
        "metrics": similarity.get("metrics", {}),
        "perPersona": similarity.get("perPersona", {}),
    }

    return result


def evaluate_run(
    expected_path: str,
    run_id: str | None = None,
    run_dir: str | None = None,
    simulation_file: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    expected_payload = load_expected(Path(expected_path).expanduser().resolve())
    paths = resolve_paths(
        expected_path,
        run_id,
        run_dir,
        simulation_file,
        output_path,
        expected_payload,
    )

    actions = read_actions_from_run_dir(paths.run_dir)
    actual = compute_actual_metrics(actions)
    similarity = evaluate_actions(expected_payload, actual)

    result = build_evaluation_result(expected_payload, actual, similarity, paths)
    write_json_atomic(paths.output_path, result)
    return result
