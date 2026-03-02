export const endpoints = {
  scanResults: (scanId: string) =>
    `/scans/${encodeURIComponent(scanId)}/results`,

  trend: (projectKey: string) =>
    `/projects/${encodeURIComponent(projectKey)}/trend`,
};