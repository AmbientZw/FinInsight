export interface ReportMeta {
  id: string;
  filename: string;
  title: string | null;
  page_count: number;
  char_count: number;
}

export interface StructuredSummary {
  core_conclusions: string[];
  key_data: string[];
  main_risks: string[];
  investment_advice: string[];
  points_to_verify: string[];
  disclaimer: string;
}

export interface QAResponse {
  answer: string;
  sources: string[];
  disclaimer: string;
}

export interface EvalDimension {
  dimension: string;
  weight: number;
  score: number;
  reasoning: string;
  evidence: string[];
}
