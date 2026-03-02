export type Severity = "low" | "medium" | "high";

export type UnifiedIssue = {
  tool: "flake8" | "bandit" | string;
  rule_id: string;
  category: string;
  severity: Severity;
  confidence?: number | null;
  file: string;        // relative path
  line: number;
  message: string;
};

export type MetricsTotals = {
  issues: number;
  by_tool: Record<string, number>;
  by_severity: Record<Severity, number>;
  loc: number;
};

export type RefactorPriorityItem = {
  file: string;
  risk_score: number;
  low: number;
  medium: number;
  high: number;
  total: number;
};

export type Metrics = {
  metrics_version: string;
  totals: MetricsTotals;
  top_refactor_priority: RefactorPriorityItem[];
  heatmap: Record<string, { low: number; medium: number; high: number }>;
  most_recurring_issues: { rule_id: string; tool: string; count: number }[];
};

export type Score = {
  final_score: number;
  penalty: number;
  weights: Record<string, number>;
  breakdown: Record<string, number>;
  method: string;
  loc: number;
  density_per_kloc: number;
  penalty_breakdown: Record<string, number>;
};

export type ScanResultsResponse = {
  scan_id: string;
  status: string;
  project_key?: string | null;
  unified_issues: UnifiedIssue[];
  metrics: Metrics;
  score: Score;
};

export type TrendPoint = {
  ts: string; // ISO timestamp
  project_key: string;
  scan_id: string;
  loc: number;
  issues: number;
  by_severity: Record<Severity, number>;
  final_score: number;
};