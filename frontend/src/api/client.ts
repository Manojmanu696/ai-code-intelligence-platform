// frontend/src/api/client.ts

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE?.toString()?.trim() ||
  "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`
    );
  }

  // Some endpoints may return empty body
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    // @ts-ignore
    return (await res.text()) as T;
  }

  return (await res.json()) as T;
}

export type CreateScanResponse = { scan_id: string; status?: string };

export type ScanStatusResponse = {
  scan_id: string;
  status: string;
  raw?: any;
  normalized?: any;
  metrics?: any;
  score?: any;
  unified_issues?: any;
};

export type ScanResultsResponse = {
  scan_id: string;
  status: string;
  raw?: any;
  normalized?: any;
  metrics?: any;
  score?: any;
  unified_issues?: any;
  ai?: any;
};

export async function createScan(project_name: string) {
  return request<CreateScanResponse>(`/scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_name }),
  });
}

export async function pasteCode(
  scan_id: string,
  filename: string,
  content: string
) {
  return request<{ status: string }>(`/scans/${scan_id}/paste`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, content }),
  });
}

export async function startScan(scan_id: string) {
  return request<{ status: string }>(`/scans/${scan_id}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    throw new Error(
      `${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`
    );
  }

  return (await res.json()) as { status: string };
}