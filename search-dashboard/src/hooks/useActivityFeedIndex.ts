import { useEffect, useState } from "react";

import type { ActivityFeedIndex } from "@/types/activity";

type FeedIndexStatus = "loading" | "ready" | "error";

type Options = {
  intervalMs?: number;
};

export function useActivityFeedIndex(options: Options = {}) {
  const intervalMs = options.intervalMs ?? 5000;
  const [index, setIndex] = useState<ActivityFeedIndex | null>(null);
  const [status, setStatus] = useState<FeedIndexStatus>("loading");

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const response = await fetch(`/simulation/index.json?t=${Date.now()}`, {
          cache: "no-store"
        });

        if (!response.ok) {
          throw new Error(`Index ${response.status}`);
        }

        const data = (await response.json()) as ActivityFeedIndex;
        if (!Array.isArray(data.files)) {
          throw new Error("Invalid index");
        }

        if (!isMounted) return;
        setIndex({
          updated_at: data.updated_at ?? new Date().toISOString(),
          files: data.files
        });
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
      if (timerId) clearInterval(timerId);
    };
  }, [intervalMs]);

  return { index, status };
}
