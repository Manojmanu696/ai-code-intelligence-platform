import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { endpoints } from "../api/endpoints";
import type { TrendPoint } from "../types/scan";

export function useTrend(projectKey: string | null) {
  const [data, setData] = useState<TrendPoint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectKey) return;

    let alive = true;
    setLoading(true);
    setError(null);

    apiGet<TrendPoint[]>(endpoints.trend(projectKey))
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));

    return () => {
      alive = false;
    };
  }, [projectKey]);

  return { data, loading, error };
}