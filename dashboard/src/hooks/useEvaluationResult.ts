import { useEffect, useState } from "react";

import type { EvaluationResult } from "@/types/evaluation";

type EvaluationStatus = "loading" | "ready" | "error";

type Options = {
  intervalMs?: number;
};

export function useEvaluationResult(evaluationId: string, options: Options = {}) {
  const intervalMs = options.intervalMs ?? 5000;
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [status, setStatus] = useState<EvaluationStatus>("loading");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const path =
          evaluationId === "latest"
            ? "/evaluation/latest.json"
            : `/evaluation/results/${evaluationId}.json`;
        const response = await fetch(`${path}?t=${Date.now()}`, {
          cache: "no-store"
        });

        if (!response.ok) {
          throw new Error(`Evaluation feed ${response.status}`);
        }

        const data = (await response.json()) as EvaluationResult;
        if (!isMounted) return;
        setResult(data);
        setLastUpdated(new Date().toISOString());
        setStatus("ready");
      } catch {
        if (!isMounted) return;
        setStatus("error");
      }
    };

    poll();
    timerId = setInterval(poll, intervalMs);

    return () => {
      isMounted = false;
      if (timerId) {
        clearInterval(timerId);
      }
    };
  }, [evaluationId, intervalMs]);

  return { result, status, lastUpdated };
}
