export interface ReportMeta {
  id: string;
  filename: string;
  title: string | null;
  page_count: number;
  char_count: number;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface Chart {
  chart_type: 'bar' | 'line' | 'pie';
  title: string;
  unit: string;
  data: ChartPoint[];
}

export interface StructuredSummary {
  core_conclusions: string[];
  key_data: string[];
  main_risks: string[];
  investment_advice: string[];
  points_to_verify: string[];
  disclaimer: string;
  charts: Chart[];
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

export interface CompareReportInput {
  title: string;
  summary: StructuredSummary;
}
