import { useEffect, useMemo, useState } from "react";

import type { ActivityFeedIndex } from "@/types/activity";

type FeedIndexStatus = "loading" | "ready" | "error";

type Options = {
  intervalMs?: number;
};

export function useActivityFeedIndex(options: Options = {}) {
  const intervalMs = options.intervalMs ?? 5000;
  const [index, setIndex] = useState<ActivityFeedIndex | null>(null);
  const [status, setStatus] = useState<FeedIndexStatus>("loading");
  const staticFiles = useMemo(() => {
    const files = Object.keys(
      import.meta.glob("/simulation/*.jsonl", { eager: true })
    ).map(path => path.replace("/simulation/", ""));
    return files;
  }, []);

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        if (!staticFiles.length) {
          throw new Error("No local feeds");
        }

        if (!isMounted) return;
        setIndex({
          updated_at: new Date().toISOString(),
          files: staticFiles
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
  }, [intervalMs, staticFiles]);

  return { index, status };
}
