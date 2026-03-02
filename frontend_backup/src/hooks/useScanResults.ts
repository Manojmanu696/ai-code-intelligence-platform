import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { endpoints } from "../api/endpoints";
import type { ScanResultsResponse } from "../types/scan";

export function useScanResults(scanId: string | null) {
  const [data, setData] = useState<ScanResultsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;

    let alive = true;
    setLoading(true);
    setError(null);

    apiGet<ScanResultsResponse>(endpoints.scanResults(scanId))
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));

    return () => {
      alive = false;
    };
  }, [scanId]);

  return { data, loading, error };
}