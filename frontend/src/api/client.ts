// frontend/src/api/client.ts

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE?.toString()?.trim() ||
  "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }

  return (await res.json()) as T;
}

export type IssueSeverity = "low" | "medium" | "high" | string;

export type UnifiedIssue = {
  tool?: string;
  rule_id?: string;
  severity?: IssueSeverity;
  confidence?: number | string | null;
  file?: string;
  line?: number | null;
  message?: string;
  category?: string;
};

export type EnrichedIssue = UnifiedIssue & {
  explanation?: string;
  fix?: string;
  risk?: string;
  impact?: string;
  priority_score?: number;
  priority?: string;
};

export type AISummary = {
  generated_at?: string;
  scan_id?: string;
  final_score?: number | null;
  penalty?: number | null;
  summary?: {
    issues_total?: number;
    loc?: number;
    by_severity?: Record<string, number>;
    bandit_findings?: number;
    risk_level?: string | null;
    security_overview?: string;
    quality_overview?: string;
    priority_action?: string;
  };
  top_risky_issues?: EnrichedIssue[];
  issues_enriched?: EnrichedIssue[];
  recommendations?: string[];
  note?: string;
};

export type CreateScanResponse = {
  scan_id: string;
  status?: string;
};

export type ScanStatusResponse = {
  scan_id: string;
  status: string;
  raw?: any;
  normalized?: any;
  metrics?: any;
  score?: any;
  unified_issues?: UnifiedIssue[];
};

export type ScanResultsResponse = {
  scan_id: string;
  status: string;
  project_key?: string | null;
  project_name?: string | null;
  raw?: any;
  normalized?: any;
  metrics?: any;
  score?: {
    final_score?: number;
    penalty?: number;
    risk_level?: string;
    risk?: string;
    [key: string]: any;
  };
  unified_issues?: UnifiedIssue[];
  ai?: {
    exists?: boolean;
    summary?: AISummary | null;
  };
};

export async function createScan(project_name?: string) {
  if (project_name && project_name.trim()) {
    return request<CreateScanResponse>("/scans", {
      method: "POST",
      body: JSON.stringify({ project_name }),
    });
  }

  return request<CreateScanResponse>("/scans", {
    method: "POST",
  });
}

export async function pasteCode(scan_id: string, filename: string, content: string) {
  return request<{ status: string }>(`/scans/${scan_id}/paste`, {
    method: "POST",
    body: JSON.stringify({ filename, content }),
  });
}

export async function startScan(scan_id: string) {
  return request<{ status: string }>(`/scans/${scan_id}/start`, {
    method: "POST",
  });
}

export async function getStatus(scan_id: string) {
  return request<ScanStatusResponse>(`/scans/${scan_id}/status`, {
    method: "GET",
  });
}

export async function getResults(scan_id: string) {
  return request<ScanResultsResponse>(`/scans/${scan_id}/results`, {
    method: "GET",
  });
}

export async function uploadZip(scan_id: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/scans/${scan_id}/upload_zip`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }

  return (await res.json()) as { status: string };
}