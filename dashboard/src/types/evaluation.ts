export interface EvaluationMetric {
  expected: number;
  actual: number;
  absError: number;
  relativeError: number;
  similarity: number;
}

export interface EvaluationResult {
  schemaVersion: string;
  evaluationId: string;
  simulationId?: string | null;
  runId?: string | null;
  createdAt: string;
  input: {
    expectedPath: string;
    expected?: Record<string, number>;
    perPersona?: Record<string, Record<string, number>>;
    weights?: Record<string, number>;
  };
  actual: {
    totals: Record<string, number | string>;
    perPersona: Record<string, Record<string, number>>;
  };
  metrics?: {
    likeCount?: EvaluationMetric;
    commentCount?: EvaluationMetric;
    likeRate?: EvaluationMetric;
    commentRate?: EvaluationMetric;
    overallSimilarity?: number | null;
  };
  perPersona?: Record<string, {
    likeCount?: EvaluationMetric;
    commentCount?: EvaluationMetric;
    likeRate?: EvaluationMetric;
    commentRate?: EvaluationMetric;
    overallSimilarity?: number | null;
  }>;
}
