import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

type UnifiedIssue = {
  tool?: string;
  rule_id?: string;
  severity?: "low" | "medium" | "high" | string;
  confidence?: number | null;
  file?: string;
  line?: number | null;
  message?: string;
  category?: string;
};

type ScanResultsResponse = {
  scan_id: string;
  status: string;
  unified_issues?: UnifiedIssue[];
  normalized?: any;
  metrics?: any;
  score?: any;
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
  return p.replace(/^input\//, "");
}

export default function Issues() {
  const [searchParams] = useSearchParams();
  const scanIdFromUrl = (searchParams.get("scan_id") || "").trim();

  const [apiBase, setApiBase] = useState(API_BASE_DEFAULT);
  const [scanId, setScanId] = useState("");
  const [loading, setLoading] = useState(false);

  const [issues, setIssues] = useState<UnifiedIssue[]>([]);
  const [foundAt, setFoundAt] = useState<"NOT_LOADED" | "unified_issues" | "normalized_fallback" | "NOT_FOUND">(
    "NOT_LOADED"
  );

  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [toolFilter, setToolFilter] = useState<string>("all");
  const [query, setQuery] = useState<string>("");

  const [selected, setSelected] = useState<UnifiedIssue | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function load(idArg?: string) {
    const id = (idArg || scanId).trim();
    if (!id) {
      setErrorMsg("No Scan ID provided.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSelected(null);

    try {
      const res = await fetch(`${apiBase}/scans/${id}/results`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = (await res.json()) as ScanResultsResponse;

      // ✅ Prefer unified_issues (your backend returns this now)
      if (Array.isArray((data as any).unified_issues)) {
        setIssues((data as any).unified_issues);
        setFoundAt("unified_issues");
      } else {
        // fallback: build from normalized if unified_issues missing
        const fl = data.normalized?.flake8?.issues || [];
        const bd = data.normalized?.bandit?.issues || [];
        const merged = [...fl, ...bd] as any[];

        if (Array.isArray(merged) && merged.length) {
          const mapped: UnifiedIssue[] = merged.map((x) => ({
            tool: x.tool,
            rule_id: x.rule_id || x.code,
            severity: x.severity,
            confidence: x.confidence ?? null,
            file: x.file,
            line: x.line ?? x.line_number ?? null,
            message: x.message || x.text,
            category: x.category,
          }));
          setIssues(mapped);
          setFoundAt("normalized_fallback");
        } else {
          setIssues([]);
          setFoundAt("NOT_FOUND");
        }
      }

      // save last scan for next time
      localStorage.setItem(LS_LAST_SCAN, id);
      setScanId(id);
    } catch (e: any) {
      setErrorMsg(e?.message || "Failed to load scan results.");
      setIssues([]);
      setFoundAt("NOT_FOUND");
    } finally {
      setLoading(false);
    }
  }

  // ✅ AUTO-LOAD on page open:
  // 1) scan_id from URL ?scan_id=...
  // 2) else fallback to last scan saved in localStorage
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
      arr = arr.filter((x) => (x.severity || "").toLowerCase() === severityFilter);
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
          (x.message || "").toLowerCase().includes(q)
        );
      });
    }

    return arr.slice(0, 500);
  }, [issues, severityFilter, toolFilter, query]);

  const toolOptions = useMemo(() => {
    const s = new Set<string>();
    for (const it of issues) if (it.tool) s.add(it.tool.toLowerCase());
    return Array.from(s).sort();
  }, [issues]);

  return (
    <div className="relative min-h-screen px-6 pt-10 pb-24">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <Link to="/" className="text-sm font-bold text-slate-700 hover:underline">
            ← Back to Dashboard
          </Link>

          <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <h1 className="text-4xl font-extrabold text-slate-900">
                All Issues <span className="text-2xl">📋</span>
              </h1>

              <div className="mt-2 text-xs text-slate-500">
                API:{" "}
                <input
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  className="ml-2 w-[240px] rounded-lg border border-white/50 bg-white/50 px-2 py-1 outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
            </div>

            <div className="flex items-end gap-3 w-full md:w-auto">
              <div className="flex-1 md:flex-none">
                <div className="text-xs font-bold text-slate-600 mb-2">Scan ID</div>
                <input
                  value={scanId}
                  onChange={(e) => setScanId(e.target.value)}
                  className="w-full md:w-[520px] rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="paste scan id…"
                />
              </div>

              {/* Keep button as "Reload" (optional) */}
              <button
                onClick={() => load()}
                disabled={loading}
                className="rounded-2xl bg-slate-900 text-white px-6 py-3 font-semibold shadow hover:opacity-95 disabled:opacity-60"
              >
                {loading ? "Loading…" : "Reload"}
              </button>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {errorMsg}
          </div>
        )}

        <div className="rounded-3xl bg-white/45 border border-white/40 shadow-sm p-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="text-sm font-bold text-slate-800">
              Showing {filtered.length} issues{" "}
              <span className="text-slate-500 font-semibold">(found at: {foundAt})</span>
            </div>

            <div className="flex flex-wrap gap-2 items-center">
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
                className="rounded-xl border border-white/50 bg-white/60 px-3 py-2 text-sm font-semibold text-slate-700 w-[220px]"
                placeholder="Search rule/file/message…"
              />
            </div>
          </div>

          <div className="mt-4 overflow-auto rounded-2xl border border-white/40 bg-white/40">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500">
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Tool</th>
                  <th className="py-3 px-4">Rule</th>
                  <th className="py-3 px-4">File</th>
                  <th className="py-3 px-4">Line</th>
                  <th className="py-3 px-4">Message</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-600">
                      No issues match your filters.
                    </td>
                  </tr>
                ) : (
                  filtered.map((it, idx) => (
                    <tr
                      key={`${it.tool}-${it.rule_id}-${it.file}-${it.line}-${idx}`}
                      className="border-t border-white/40 hover:bg-white/60 cursor-pointer"
                      onClick={() => setSelected(it)}
                    >
                      <td className="py-3 px-4 font-extrabold text-slate-800">{sevLabel(it.severity)}</td>
                      <td className="py-3 px-4 font-semibold text-slate-700">{it.tool}</td>
                      <td className="py-3 px-4 font-semibold text-slate-700">{it.rule_id}</td>
                      <td className="py-3 px-4 text-slate-700">{cleanPath(it.file)}</td>
                      <td className="py-3 px-4 text-slate-700">{it.line ?? "-"}</td>
                      <td className="py-3 px-4 text-slate-700">{it.message}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-3 text-xs text-slate-500">
            Showing up to 500 issues (pagination next ✅)
          </div>
        </div>

        <div className="mt-6 rounded-3xl bg-white/45 border border-white/40 shadow-sm p-5">
          <div className="text-xl font-extrabold text-slate-900">Issue details</div>
          <div className="text-sm text-slate-500 mt-1">Click a row to see full details.</div>

          <div className="mt-4 rounded-2xl bg-white/55 border border-white/40 p-4 text-sm">
            {!selected ? (
              <div className="text-slate-600">No issue selected yet.</div>
            ) : (
              <div className="space-y-2">
                <div><span className="font-bold">Severity:</span> {selected.severity}</div>
                <div><span className="font-bold">Tool:</span> {selected.tool}</div>
                <div><span className="font-bold">Rule:</span> {selected.rule_id}</div>
                <div><span className="font-bold">File:</span> {cleanPath(selected.file)}</div>
                <div><span className="font-bold">Line:</span> {selected.line ?? "-"}</div>
                <div><span className="font-bold">Message:</span> {selected.message}</div>
                {selected.category ? <div><span className="font-bold">Category:</span> {selected.category}</div> : null}
                {typeof selected.confidence === "number" ? (
                  <div><span className="font-bold">Confidence:</span> {selected.confidence}</div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <footer className="mt-10 text-center text-xs text-slate-500">
          Final Folder • AI-Powered Code Intelligence &amp; Review Platform
        </footer>
      </div>
    </div>
  );
}