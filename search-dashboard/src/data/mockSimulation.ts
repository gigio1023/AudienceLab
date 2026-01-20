import type { SimulationResult } from "@/types/simulation";

export const mockSimulation: SimulationResult = {
  simulationId: "sim_2025_10_03_1442",
  status: "completed",
  progress: 100,
  createdAt: "2025-10-03T14:42:00Z",
  config: {
    post_description: "Eco skincare launch with soft-spoken, urban wellness tone.",
    agent_count: 42
  },
  agents: [
    {
      persona_id: "persona_01",
      persona_name: "Nora / Minimalist Creator",
      reaction: "positive",
      action: "comment",
      comment_text: "Love the calm palette. Feels premium but still approachable.",
      internal_thought: "This feels like a brand that respects routines.",
      reasoning: "Tone and visuals align with slow-living preference."
    },
    {
      persona_id: "persona_02",
      persona_name: "Jae / Ingredient Nerd",
      reaction: "neutral",
      action: "like",
      comment_text: null,
      internal_thought: "Need to see the active ingredients list.",
      reasoning: "Curious but waiting for proof points."
    },
    {
      persona_id: "persona_03",
      persona_name: "Mina / Budget-Conscious",
      reaction: "negative",
      action: "skip",
      comment_text: null,
      internal_thought: "Looks pricey. Not for me right now.",
      reasoning: "Perceived premium pricing triggered skip behavior."
    }
  ],
  metrics: {
    total_agents: 42,
    reactions: {
      positive: 24,
      neutral: 11,
      negative: 7
    },
    actions: {
      like: 26,
      comment: 9,
      skip: 7
    },
    positive_rate: 0.57,
    engagement_rate: 0.83,
    sentiment_score: 0.41
  },
  stigmergy_trace: [
    "Nora praises the calm visual tone and premium feel.",
    "Jae responds with ingredient curiosity but still likes.",
    "Mina flags the premium vibe as price anxiety."
  ]
};
