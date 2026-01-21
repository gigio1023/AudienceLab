export type AgentActivityEvent = {
  id: string;
  agent_id: string;
  action: string;
  timestamp: string;
  source: string;
  target?: string | null;
  content?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type RawActivityRecord = Record<string, unknown>;

export type ActivityFeedIndex = {
  updated_at: string;
  files: string[];
};
