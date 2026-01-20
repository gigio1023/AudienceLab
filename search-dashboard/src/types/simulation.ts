export interface SimulationResult {
  simulationId: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  createdAt: string;
  config: {
    post_description: string;
    agent_count: number;
  };
  agents: AgentResult[];
  metrics: {
    total_agents: number;
    reactions: {
      positive: number;
      neutral: number;
      negative: number;
    };
    actions: {
      like: number;
      comment: number;
      skip: number;
    };
    positive_rate: number;
    engagement_rate: number;
    sentiment_score: number;
  };
  stigmergy_trace: string[];
}

export interface AgentResult {
  persona_id: string;
  persona_name: string;
  reaction: "positive" | "neutral" | "negative";
  action: "like" | "comment" | "skip";
  comment_text: string | null;
  internal_thought: string;
  reasoning: string;
}
