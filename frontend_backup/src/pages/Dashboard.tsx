import { useMemo, useState } from "react";
import { PageShell } from "../components/layout/PageShell";
import { Loading } from "../components/common/Loading";
import { ErrorState } from "../components/common/ErrorState";
import { ScoreCard } from "../components/cards/ScoreCard";
import { StatCard } from "../components/cards/StatCard";
import { SeverityBreakdown } from "../components/widgets/SeverityBreakdown";
import { TopRefactorTable } from "../components/widgets/TopRefactorTable";
import { HeatmapTable } from "../components/widgets/HeatmapTable";
import { RecurringIssuesTable } from "../components/widgets/RecurringIssuesTable";
import { TrendChart } from "../components/widgets/TrendChart";
import { useScanResults } from "../hooks/useScanResults";
import { useTrend } from "../hooks/useTrend";

export default function Dashboard() {
  // MVP: user pastes scan_id + optional project_key
  const [scanId, setScanId] = useState<string>("");
  const { data, loading, error } = useScanResults(scanId.trim() ? scanId.trim() : null);

  const projectKey = data?.project_key ?? null;
  const trend = useTrend(projectKey);

  const totals = data?.metrics?.totals;
  const score = data?.score?.final_score ?? 0;

  const right = (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <input
        className="w-full sm:w-96 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/20"
        placeholder="Paste scan_id (e.g., 634ef790-...)"
        value={scanId}
        onChange={(e) => setScanId(e.target.value)}
      />
      <div className="text-xs text-white/50">
        Backend: <span className="font-mono">127.0.0.1:8000</span>
      </div>
    </div>
  );

  const subtitle = useMemo(() => {
    if (!data) return "Enter a scan_id to view score, metrics, and trend.";
    return `Scan: ${data.scan_id} • Status: ${data.status}${projectKey ? ` • Project: ${projectKey}` : ""}`;
  }, [data, projectKey]);

  return (
    <PageShell title="Security & Quality Dashboard" subtitle={subtitle} right={right}>
      {!scanId.trim() ? (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-sm text-white/70">
          👋 Paste a <span className="font-mono text-white/90">scan_id</span> to load results.
          <div className="mt-2 text-xs text-white/50">
            Uses <span className="font-mono">GET /scans/&lt;scan_id&gt;/results</span> and
            <span className="font-mono"> GET /projects/&lt;project_key&gt;/trend</span>.
          </div>
        </div>
      ) : null}

      {loading ? <Loading label="Fetching scan results..." /> : null}
      {error ? <ErrorState message={error} /> : null}

      {data ? (
        <div className="mt-6 space-y-6">
          {/* Top cards */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            <ScoreCard score={score} />
            <StatCard label="Total Issues" value={totals?.issues ?? 0} hint="flake8 + bandit unified" />
            <StatCard label="LOC" value={totals?.loc ?? 0} hint="used for density scoring" />
            <StatCard
              label="Tools"
              value={Object.keys(totals?.by_tool || {}).length}
              hint="active analyzers"
            />
          </div>

          {/* Breakdown + tables */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <SeverityBreakdown bySeverity={totals?.by_severity ?? { low: 0, medium: 0, high: 0 }} />
            <div className="lg:col-span-2">
              <TopRefactorTable items={data.metrics.top_refactor_priority} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <HeatmapTable heatmap={data.metrics.heatmap} limit={10} />
            <RecurringIssuesTable items={data.metrics.most_recurring_issues} limit={10} />
          </div>

          {/* Trend */}
          <div className="grid grid-cols-1 gap-4">
            {projectKey ? (
              trend.loading ? (
                <Loading label="Fetching trend..." />
              ) : trend.error ? (
                <ErrorState message={trend.error} />
              ) : (
                <TrendChart points={trend.data || []} />
              )
            ) : (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-white/70">
                📉 Trend is available only when <span className="font-mono">project_key</span> exists for this scan.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}