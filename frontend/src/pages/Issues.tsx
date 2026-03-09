import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

type UnifiedIssue = {
  tool?: string;
  rule_id?: string;
  severity?: "low" | "medium" | "high" | string;
  confidence?: number | string | null;
  file?: string;
  line?: number | null;
  message?: string;
  category?: string;
};

type EnrichedIssue = UnifiedIssue & {
  explanation?: string;
  fix?: string;
  risk?: string;
  impact?: string;
  priority_score?: number;
  priority?: string;
};

type AISummary = {
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

type ScanResultsResponse = {
  scan_id: string;
  status: string;
  unified_issues?: UnifiedIssue[];
  normalized?: any;
  metrics?: any;
  score?: {
    final_score?: number;
    penalty?: number;
    risk_level?: string;
    risk?: string;
    [key: string]: any;
  };
  ai?: {
    exists?: boolean;
    summary?: AISummary | null;
  };
};

const API_BASE_DEFAULT = "http://127.0.0.1:8000";
const LS_LAST_SCAN = "ff_last_scan_id";

function sevLabel(s?: string) {
  const x = (s || "").toLowerCase();
  if (x === "high") return "HIGH";
  if (x === "medium" || x === "med") return "MED";
  return "LOW";
}

function cleanPath(p?: string) {
  if (!p) return "";
  return p.replace(/^input\//, "").replace(/\\/g, "/");
}

function cleanText(value?: string) {
  if (!value) return "";
  return value.replace(/input\//g, "");
}

function normalizeLine(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim()) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function normalizeConfidence(v: unknown): number | string | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim()) return v.trim();
  return null;
}

function normalizeScoreValue(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim()) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function deriveRiskLevelFromScore(scoreValue: unknown): string | null {
  const score = normalizeScoreValue(scoreValue);
  if (score === null) return null;
  if (score >= 80) return "Low Risk";
  if (score >= 50) return "Medium Risk";
  return "High Risk";
}

function normalizeIssue(x: any): EnrichedIssue {
  return {
    tool: x?.tool,
    rule_id: x?.rule_id || x?.code,
    severity: x?.severity,
    confidence: normalizeConfidence(x?.confidence),
    file: cleanPath(x?.file),
    line: normalizeLine(x?.line ?? x?.line_number),
    message: x?.message || x?.text,
    category: x?.category,
    explanation: cleanText(x?.explanation),
    fix: cleanText(x?.fix),
    risk: cleanText(x?.risk),
    impact: cleanText(x?.impact),
    priority_score:
      typeof x?.priority_score === "number" ? x.priority_score : undefined,
    priority: x?.priority,
  };
}

function mergeIssues(base: EnrichedIssue[], enriched: EnrichedIssue[]) {
  const map = new Map<string, EnrichedIssue>();

  const keyOf = (x: EnrichedIssue) =>
    [
      (x.tool || "").toLowerCase(),
      (x.rule_id || "").toUpperCase(),
      (x.file || "").toLowerCase(),
      x.line ?? "",
      (x.message || "").toLowerCase(),
    ].join("|");

  for (const item of base) {
    map.set(keyOf(item), { ...item });
  }

  for (const item of enriched) {
    const key = keyOf(item);
    const existing = map.get(key);
    if (!existing) {
      map.set(key, { ...item });
      continue;
    }

    map.set(key, {
      ...existing,
      ...item,
      explanation: item.explanation || existing.explanation,
      fix: item.fix || existing.fix,
      risk: item.risk || existing.risk,
      impact: item.impact || existing.impact,
      priority: item.priority || existing.priority,
      priority_score:
        typeof item.priority_score === "number"
          ? item.priority_score
          : existing.priority_score,
    });
  }

  return Array.from(map.values());
}

function sortIssues(items: EnrichedIssue[]) {
  const sevRank = (s?: string) => {
    const v = (s || "").toLowerCase();
    if (v === "high") return 3;
    if (v === "medium") return 2;
    return 1;
  };

  const toolRank = (t?: string) => {
    const v = (t || "").toLowerCase();
    if (v === "bandit") return 2;
    if (v === "flake8") return 1;
    return 0;
  };

  return [...items].sort((a, b) => {
    const aPriority =
      typeof a.priority_score === "number" ? a.priority_score : -1;
    const bPriority =
      typeof b.priority_score === "number" ? b.priority_score : -1;

    if (bPriority !== aPriority) return bPriority - aPriority;
    if (sevRank(b.severity) !== sevRank(a.severity)) {
      return sevRank(b.severity) - sevRank(a.severity);
    }
    if (toolRank(b.tool) !== toolRank(a.tool)) {
      return toolRank(b.tool) - toolRank(a.tool);
    }

    const aFile = a.file || "";
    const bFile = b.file || "";
    if (aFile !== bFile) return aFile.localeCompare(bFile);

    return (a.line || 0) - (b.line || 0);
  });
}

function badgeClassForSeverity(severity?: string) {
  const s = (severity || "").toLowerCase();
  if (s === "high") {
    return "bg-red-100 text-red-700 border border-red-200";
  }
  if (s === "medium") {
    return "bg-amber-100 text-amber-700 border border-amber-200";
  }
  return "bg-emerald-100 text-emerald-700 border border-emerald-200";
}

function badgeClassForTool(tool?: string) {
  const t = (tool || "").toLowerCase();
  if (t === "bandit") {
    return "bg-violet-100 text-violet-700 border border-violet-200";
  }
  if (t === "flake8") {
    return "bg-sky-100 text-sky-700 border border-sky-200";
  }
  return "bg-slate-100 text-slate-700 border border-slate-200";
}

export default function Issues() {
  const [searchParams] = useSearchParams();
  const scanIdFromUrl = (searchParams.get("scan_id") || "").trim();

  const [apiBase, setApiBase] = useState(API_BASE_DEFAULT);
  const [scanId, setScanId] = useState("");
  const [loading, setLoading] = useState(false);
  const [issues, setIssues] = useState<EnrichedIssue[]>([]);
  const [selected, setSelected] = useState<EnrichedIssue | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [foundAt, setFoundAt] = useState<
    | "NOT_LOADED"
    | "ai_enriched"
    | "merged"
    | "unified_issues"
    | "normalized_fallback"
    | "NOT_FOUND"
  >("NOT_LOADED");

  const [severityFilter, setSeverityFilter] = useState("all");
  const [toolFilter, setToolFilter] = useState("all");
  const [query, setQuery] = useState("");

  const [aiSummary, setAiSummary] = useState<AISummary | null>(null);
  const [scoreRiskLevel, setScoreRiskLevel] = useState<string | null>(null);
  const [scoreFinalScore, setScoreFinalScore] = useState<number | null>(null);

  async function load(idArg?: string) {
    const id = (idArg || scanId).trim();

    if (!id) {
      setErrorMsg("No Scan ID provided.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSelected(null);
    setAiSummary(null);
    setScoreRiskLevel(null);
    setScoreFinalScore(null);

    try {
      const res = await fetch(`${apiBase}/scans/${id}/results`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

      const data = (await res.json()) as ScanResultsResponse;

      const unified = Array.isArray(data.unified_issues)
        ? data.unified_issues.map(normalizeIssue)
        : [];

      const aiEnriched = Array.isArray(data.ai?.summary?.issues_enriched)
        ? data.ai!.summary!.issues_enriched!.map(normalizeIssue)
        : [];

      const fl = Array.isArray(data.normalized?.flake8?.issues)
        ? data.normalized.flake8.issues
        : [];
      const bd = Array.isArray(data.normalized?.bandit?.issues)
        ? data.normalized.bandit.issues
        : [];
      const fallbackNormalized = [...fl, ...bd].map(normalizeIssue);

      let finalIssues: EnrichedIssue[] = [];
      let source:
        | "NOT_LOADED"
        | "ai_enriched"
        | "merged"
        | "unified_issues"
        | "normalized_fallback"
        | "NOT_FOUND" = "NOT_FOUND";

      if (aiEnriched.length > 0 && unified.length > 0) {
        finalIssues = sortIssues(mergeIssues(unified, aiEnriched));
        source = "merged";
      } else if (aiEnriched.length > 0) {
        finalIssues = sortIssues(aiEnriched);
        source = "ai_enriched";
      } else if (unified.length > 0) {
        finalIssues = sortIssues(unified);
        source = "unified_issues";
      } else if (fallbackNormalized.length > 0) {
        finalIssues = sortIssues(fallbackNormalized);
        source = "normalized_fallback";
      }

      setIssues(finalIssues);
      setFoundAt(source);

      const summary = data.ai?.summary
        ? {
            ...data.ai.summary,
            final_score: normalizeScoreValue(data.ai.summary.final_score),
            penalty: normalizeScoreValue(data.ai.summary.penalty),
            summary: data.ai.summary.summary
              ? {
                  ...data.ai.summary.summary,
                  security_overview: cleanText(
                    data.ai.summary.summary.security_overview
                  ),
                  quality_overview: cleanText(
                    data.ai.summary.summary.quality_overview
                  ),
                  priority_action: cleanText(
                    data.ai.summary.summary.priority_action
                  ),
                }
              : undefined,
            recommendations: Array.isArray(data.ai.summary.recommendations)
              ? data.ai.summary.recommendations.map((x) => cleanText(x))
              : [],
          }
        : null;

      setAiSummary(summary);
      setScoreRiskLevel(data.score?.risk_level || data.score?.risk || null);
      setScoreFinalScore(normalizeScoreValue(data.score?.final_score));

      if (finalIssues.length > 0) {
        setSelected(finalIssues[0]);
      }

      localStorage.setItem(LS_LAST_SCAN, id);
      setScanId(id);
    } catch (e: any) {
      setErrorMsg(e?.message || "Failed to load scan results.");
      setIssues([]);
      setAiSummary(null);
      setScoreRiskLevel(null);
      setScoreFinalScore(null);
      setSelected(null);
      setFoundAt("NOT_FOUND");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const last = (localStorage.getItem(LS_LAST_SCAN) || "").trim();
    const effective = scanIdFromUrl || last;
    if (effective) {
      setScanId(effective);
      load(effective);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanIdFromUrl]);

  const filtered = useMemo(() => {
    let arr = issues || [];

    if (severityFilter !== "all") {
      arr = arr.filter(
        (x) => (x.severity || "").toLowerCase() === severityFilter
      );
    }

    if (toolFilter !== "all") {
      arr = arr.filter((x) => (x.tool || "").toLowerCase() === toolFilter);
    }

    if (query.trim()) {
      const q = query.toLowerCase();
      arr = arr.filter((x) => {
        return (
          (x.rule_id || "").toLowerCase().includes(q) ||
          (x.file || "").toLowerCase().includes(q) ||
          (x.message || "").toLowerCase().includes(q) ||
          (x.explanation || "").toLowerCase().includes(q) ||
          (x.fix || "").toLowerCase().includes(q)
        );
      });
    }

    return arr.slice(0, 500);
  }, [issues, severityFilter, toolFilter, query]);

  const toolOptions = useMemo(() => {
    const s = new Set<string>();
    for (const it of issues) {
      if (it.tool) s.add(it.tool.toLowerCase());
    }
    return Array.from(s).sort();
  }, [issues]);

  const summaryRisk =
    aiSummary?.summary?.risk_level ||
    scoreRiskLevel ||
    deriveRiskLevelFromScore(aiSummary?.final_score) ||
    deriveRiskLevelFromScore(scoreFinalScore) ||
    null;

  const recommendations = Array.isArray(aiSummary?.recommendations)
    ? aiSummary!.recommendations!
    : [];

  const topRiskyCount = Array.isArray(aiSummary?.top_risky_issues)
    ? aiSummary!.top_risky_issues!.length
    : 0;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center rounded-2xl border border-white/50 bg-white/70 px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-white"
          >
            ← Back to Dashboard
          </Link>
        </div>

        <div className="mb-6 rounded-3xl border border-white/60 bg-white/70 p-5 shadow-sm backdrop-blur">
          <h1 className="text-2xl font-bold tracking-tight">All Issues</h1>

          <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-600">
                API:
                <input
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  className="ml-2 w-[240px] rounded-lg border border-white/50 bg-white/50 px-2 py-1 outline-none focus:ring-2 focus:ring-sky-200"
                />
              </label>
            </div>

            <div className="flex w-full flex-col gap-3 md:flex-row md:items-center">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-semibold text-slate-600">
                  Scan ID
                </label>
                <input
                  value={scanId}
                  onChange={(e) => setScanId(e.target.value)}
                  className="w-full rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="paste scan id…"
                />
              </div>

              <button
                onClick={() => load()}
                disabled={loading}
                className="rounded-2xl bg-slate-900 px-6 py-3 font-semibold text-white shadow hover:opacity-95 disabled:opacity-60"
              >
                {loading ? "Loading…" : "Reload"}
              </button>
            </div>
          </div>

          {errorMsg && (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {errorMsg}
            </div>
          )}

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Source
              </div>
              <div className="mt-2 text-lg font-bold text-slate-900">
                {foundAt}
              </div>
            </div>

            <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Showing
              </div>
              <div className="mt-2 text-lg font-bold text-slate-900">
                {filtered.length}
              </div>
            </div>

            <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                AI Risk Level
              </div>
              <div className="mt-2 text-lg font-bold text-slate-900">
                {summaryRisk || "—"}
              </div>
            </div>

            <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Top Risky Issues
              </div>
              <div className="mt-2 text-lg font-bold text-slate-900">
                {topRiskyCount}
              </div>
            </div>
          </div>

          {aiSummary?.summary?.security_overview ||
          aiSummary?.summary?.quality_overview ? (
            <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-2">
              <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
                <div className="text-sm font-semibold text-slate-700">
                  Security Overview
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {aiSummary?.summary?.security_overview || "—"}
                </p>
              </div>

              <div className="rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
                <div className="text-sm font-semibold text-slate-700">
                  Quality Overview
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {aiSummary?.summary?.quality_overview || "—"}
                </p>
              </div>
            </div>
          ) : null}

          {aiSummary?.summary?.priority_action ? (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
              <div className="text-sm font-semibold text-amber-800">
                Priority Action
              </div>
              <p className="mt-2 text-sm leading-6 text-amber-900">
                {aiSummary.summary.priority_action}
              </p>
            </div>
          ) : null}

          {recommendations.length > 0 ? (
            <div className="mt-4 rounded-2xl border border-white/50 bg-white/70 p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-700">
                Recommendations
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {recommendations.map((item, idx) => (
                  <span
                    key={`${item}-${idx}`}
                    className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="mb-4 flex flex-col gap-3 rounded-3xl border border-white/60 bg-white/70 p-4 shadow-sm backdrop-blur md:flex-row md:items-center md:justify-between">
          <div className="text-sm font-medium text-slate-600">
            Showing {filtered.length} issues (found at: {foundAt})
          </div>

          <div className="flex flex-col gap-3 md:flex-row">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-xl border border-white/50 bg-white/60 px-3 py-2 text-sm font-semibold text-slate-700"
            >
              <option value="all">All severity</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={toolFilter}
              onChange={(e) => setToolFilter(e.target.value)}
              className="rounded-xl border border-white/50 bg-white/60 px-3 py-2 text-sm font-semibold text-slate-700"
            >
              <option value="all">All tools</option>
              {toolOptions.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>

            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-[220px] rounded-xl border border-white/50 bg-white/60 px-3 py-2 text-sm font-semibold text-slate-700"
              placeholder="Search rule/file/message…"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_0.95fr]">
          <div className="overflow-hidden rounded-3xl border border-white/60 bg-white/70 shadow-sm backdrop-blur">
            <div className="border-b border-slate-200 px-4 py-4">
              <div className="grid grid-cols-[110px_90px_110px_1.2fr_80px_2fr] gap-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                <div>Severity</div>
                <div>Tool</div>
                <div>Rule</div>
                <div>File</div>
                <div>Line</div>
                <div>Message</div>
              </div>
            </div>

            <div className="max-h-[70vh] overflow-auto">
              {filtered.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-slate-500">
                  No issues match your filters.
                </div>
              ) : (
                filtered.map((it, idx) => {
                  const isActive =
                    selected &&
                    selected.tool === it.tool &&
                    selected.rule_id === it.rule_id &&
                    selected.file === it.file &&
                    selected.line === it.line &&
                    selected.message === it.message;

                  return (
                    <button
                      key={`${it.tool}-${it.rule_id}-${it.file}-${it.line}-${idx}`}
                      onClick={() => setSelected(it)}
                      className={`grid w-full grid-cols-[110px_90px_110px_1.2fr_80px_2fr] gap-3 border-b border-slate-100 px-4 py-4 text-left transition hover:bg-slate-50 ${
                        isActive ? "bg-sky-50" : "bg-transparent"
                      }`}
                    >
                      <div>
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${badgeClassForSeverity(
                            it.severity
                          )}`}
                        >
                          {sevLabel(it.severity)}
                        </span>
                      </div>

                      <div>
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${badgeClassForTool(
                            it.tool
                          )}`}
                        >
                          {it.tool || "—"}
                        </span>
                      </div>

                      <div className="truncate text-sm font-semibold text-slate-800">
                        {it.rule_id || "—"}
                      </div>

                      <div className="truncate text-sm text-slate-700">
                        {cleanPath(it.file) || "—"}
                      </div>

                      <div className="text-sm text-slate-700">
                        {it.line ?? "-"}
                      </div>

                      <div className="truncate text-sm text-slate-700">
                        {it.message || "—"}
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            <div className="border-t border-slate-200 px-4 py-3 text-xs font-medium text-slate-500">
              Showing up to 500 issues (pagination next ✅)
            </div>
          </div>

          <div className="rounded-3xl border border-white/60 bg-white/70 p-5 shadow-sm backdrop-blur">
            <h2 className="text-lg font-bold text-slate-900">Issue details</h2>
            <p className="mt-1 text-sm text-slate-500">
              Click a row to see full details.
            </p>

            {!selected ? (
              <div className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                No issue selected yet.
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Severity
                    </div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">
                      {selected.severity || "—"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Tool
                    </div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">
                      {selected.tool || "—"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Rule
                    </div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">
                      {selected.rule_id || "—"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Line
                    </div>
                    <div className="mt-2 text-sm font-semibold text-slate-900">
                      {selected.line ?? "-"}
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    File
                  </div>
                  <div className="mt-2 break-all text-sm font-medium text-slate-900">
                    {cleanPath(selected.file) || "—"}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Message
                  </div>
                  <div className="mt-2 text-sm leading-6 text-slate-800">
                    {selected.message || "—"}
                  </div>
                </div>

                {selected.category ? (
                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Category
                    </div>
                    <div className="mt-2 text-sm font-medium text-slate-900">
                      {selected.category}
                    </div>
                  </div>
                ) : null}

                {selected.confidence !== null &&
                selected.confidence !== undefined ? (
                  <div className="rounded-2xl border border-white/50 bg-white/80 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Confidence
                    </div>
                    <div className="mt-2 text-sm font-medium text-slate-900">
                      {String(selected.confidence)}
                    </div>
                  </div>
                ) : null}

                {selected.priority ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                      Priority
                    </div>
                    <div className="mt-2 text-sm font-bold text-amber-900">
                      {selected.priority}
                      {typeof selected.priority_score === "number"
                        ? ` • score ${selected.priority_score}`
                        : ""}
                    </div>
                  </div>
                ) : null}

                {selected.explanation ? (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-sky-700">
                      AI Explanation
                    </div>
                    <div className="mt-2 text-sm leading-6 text-sky-950">
                      {selected.explanation}
                    </div>
                  </div>
                ) : null}

                {selected.risk ? (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-rose-700">
                      Risk
                    </div>
                    <div className="mt-2 text-sm leading-6 text-rose-950">
                      {selected.risk}
                    </div>
                  </div>
                ) : null}

                {selected.impact ? (
                  <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                      Impact
                    </div>
                    <div className="mt-2 text-sm leading-6 text-violet-950">
                      {selected.impact}
                    </div>
                  </div>
                ) : null}

                {selected.fix ? (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                      Suggested Fix
                    </div>
                    <div className="mt-2 text-sm leading-6 text-emerald-950">
                      {selected.fix}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 pb-4 text-center text-xs font-medium text-slate-500">
          Final Folder • AI-Powered Code Intelligence & Review Platform
        </div>
      </div>
    </div>
  );
}