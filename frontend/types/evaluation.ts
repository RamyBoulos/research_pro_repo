export type Language = "en" | "de";

export interface ResolvedCriterionResult {
  criterion_id: string;
  label: string;
  score_percent: number;
  suggestion: string;
  quote: string | null;
}

export interface ResolvedEvaluationResult {
  output_language: Language;
  transcript: string;
  duration_seconds: number;
  overall_score: number;
  summary: string;
  criteria_met: number;
  total_criteria: number;
  criteria: ResolvedCriterionResult[];
  key_suggestion: string;
}

export interface TranscriptionResponse {
  transcript: string;
  duration_seconds: number;
}
