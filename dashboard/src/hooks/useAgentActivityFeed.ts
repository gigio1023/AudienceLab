import { useEffect, useState } from "react";

import { ActivityInterface } from "@/lib/activityInterface";
import type { AgentActivityEvent, RawActivityRecord } from "@/types/activity";

type FeedStatus = "loading" | "ready" | "error";

type Options = {
  intervalMs?: number;
  maxLines?: number;
  limit?: number;
};

const DEFAULT_MAX_LINES = 200;
const DEFAULT_LIMIT = 100;

const parseJsonLines = (text: string) =>
  text
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean);

export function useAgentActivityFeed(files: string[], options: Options = {}) {
  const intervalMs = options.intervalMs ?? 2000;
  const maxLines = options.maxLines ?? DEFAULT_MAX_LINES;
  const limit = options.limit ?? DEFAULT_LIMIT;

  const [events, setEvents] = useState<AgentActivityEvent[]>([]);
  const [status, setStatus] = useState<FeedStatus>("loading");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    if (!files.length) {
      setEvents([]);
      setStatus("error");
      return;
    }

    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const responses = await Promise.all(
          files.map(file =>
            fetch(`/simulation/${file}?t=${Date.now()}`, {
              cache: "no-store"
            })
          )
        );

        const texts = await Promise.all(
          responses.map(async response => {
            if (!response.ok) {
              throw new Error(`Feed ${response.status}`);
            }
            return response.text();
          })
        );

        const collected: AgentActivityEvent[] = [];
        texts.forEach((text, fileIndex) => {
          const lines = parseJsonLines(text);
          const tail = lines.slice(-maxLines);
          tail.forEach((line, lineIndex) => {
            try {
              const record = JSON.parse(line) as RawActivityRecord;
              const fallbackId = `${files[fileIndex]}:${lineIndex}`;
              collected.push(ActivityInterface.normalize(record, files[fileIndex], fallbackId));
            } catch {
              // Skip malformed lines
            }
          });
        });

        const sorted = collected
          .map(event => ({ ...event, _ts: Date.parse(event.timestamp) || 0 }))
          .sort((a, b) => b._ts - a._ts)
          .slice(0, limit)
          .map(({ _ts, ...event }) => event);

        if (!isMounted) return;
        setEvents(sorted);
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
      if (timerId) clearInterval(timerId);
    };
  }, [files, intervalMs, maxLines, limit]);

  return { events, status, lastUpdated };
}
