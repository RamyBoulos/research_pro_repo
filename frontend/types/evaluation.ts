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

export interface CriterionResult {
  criterion_id: string;
  label: Record<Language, string>;
  score_percent: number;
  suggestion: Record<Language, string>;
  quote: Record<Language, string> | null;
}

export interface EvaluationResult {
  transcript: string;
  duration_seconds: number;
  overall_score: number;
  summary: Record<Language, string>;
  criteria_met: number;
  total_criteria: number;
  criteria: CriterionResult[];
  key_suggestion: Record<Language, string>;
}

export type EvaluationLanguageBundle = Record<Language, ResolvedEvaluationResult>;

export interface CoachingMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CoachingSessionSummary {
  language: Language;
  learner_needs: string[];
  main_weaknesses: string[];
  explained_criteria: string[];
  rewrite_examples_given: string[];
  current_focus: string | null;
  open_questions: string[];
}

export interface ResolvedCoachingCitation {
  source: string;
  section: string | null;
  quote: string | null;
  rationale: string | null;
}

export interface ResolvedCoachingResponse {
  output_language: Language;
  answer: string;
  citations: ResolvedCoachingCitation[];
  updated_session_summary: CoachingSessionSummary;
}

export interface TranscriptionResponse {
  transcript: string;
  duration_seconds: number;
}
