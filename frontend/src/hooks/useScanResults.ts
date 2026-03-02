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
      .then((d) => {
        if (!alive) return;
        setData(d);
      })
      .catch((e: unknown) => {
        if (!alive) return;
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [scanId]);

  return { data, loading, error };
}
