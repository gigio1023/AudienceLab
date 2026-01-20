import { useEffect, useState } from "react";

import type { SimulationResult } from "@/types/simulation";

type SimulationFeedStatus = "loading" | "ready" | "error";

type Options = {
  intervalMs?: number;
};

export function useSimulationResult(simulationId: string, options: Options = {}) {
  const intervalMs = options.intervalMs ?? 2000;
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [status, setStatus] = useState<SimulationFeedStatus>("loading");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const response = await fetch(`/simulation/${simulationId}.json?t=${Date.now()}`, {
          cache: "no-store"
        });

        if (!response.ok) {
          throw new Error(`Simulation feed ${response.status}`);
        }

        const data = (await response.json()) as SimulationResult;
        if (!isMounted) return;
        setResult(data);
        setLastUpdated(new Date().toISOString());
        setStatus(data.status === "failed" ? "error" : "ready");
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
  }, [simulationId, intervalMs]);

  return { result, status, lastUpdated };
}
