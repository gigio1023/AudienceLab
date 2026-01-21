export interface SimulationOutput {
  simulationId: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  createdAt: string;
  updatedAt: string;
  config: {
    goal: string;
    budget: number;
    duration: number;
    targetPersona: string;
    parameters?: {
      agentCount?: number;
      messageTone?: string;
      heroEnabled?: boolean;
      crowdCount?: number;
      postContext?: string;
      dryRun?: boolean;
      runId?: string;
    };
  };
  result?: {
    metrics: SimulationMetrics;
    confidenceLevel: "low" | "medium" | "high";
    agentLogs: unknown[];
    personaTraces: PersonaTrace[];
  };
}

export interface SimulationMetrics {
  reach: number;
  engagement: number;
  conversionEstimate: number;
  roas: number;
}

export interface PersonaTrace {
  personaId?: string;
  agentId?: string;
  decision?: {
    like?: boolean;
    comment?: string | null;
    follow?: boolean;
    sentiment?: "positive" | "neutral" | "negative";
    reasoning?: string;
  };
  actionResult?: {
    method?: string;
    status?: string;
  };
  postContext?: string;
}
