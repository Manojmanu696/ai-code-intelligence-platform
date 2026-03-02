// frontend/src/pages/Dashboard.tsx
import React, { useEffect, useMemo, useState } from "react";

type Mode = "paste" | "upload" | "repo";

type ScanCreateResponse = {
  scan_id: string;
  status?: string;
};

type ScanStatusResponse = {
  scan_id: string;
  status: string;
};

type Metrics = {
  totals?: {
    issues?: number;
    by_tool?: Record<string, number>;
    by_severity?: Record<string, number>;
    loc?: number;
  };
  most_recurring_issues?: Array<{ key: string; count: number }>;
  top_files?: Array<{ file: string; count: number }>;
  heatmap?: Record<string, { low?: number; medium?: number; high?: number }>;
};

type Score = {
  final_score?: number;
  penalty?: number;
  risk_label?: string; // optional (if backend provides)
};

type ScanResultsResponse = {
  scan_id: string;
  status: string;
  raw?: any;
  normalized?: any;
  metrics?: any;
  score?: any;
  unified_issues?: any;
};

type HistoryItem = {
  id: string; // scan_id
  projectName: string;
  mode: Mode;
  filename?: string;
  createdAt: number;
  score?: number; // 0-100
  risk?: "Low Risk" | "Medium Risk" | "High Risk";
  issues?: number;
  loc?: number;
};

const API_BASE_DEFAULT = "http://127.0.0.1:8000";
const LS_KEY = "final_folder_history_v1";

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function fmtAgo(ts: number) {
  const sec = Math.floor((Date.now() - ts) / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  return `${d}d ago`;
}

function riskFromScore(score?: number): "Low Risk" | "Medium Risk" | "High Risk" {
  const s = typeof score === "number" ? score : 0;
  if (s >= 80) return "Low Risk";
  if (s >= 50) return "Medium Risk";
  return "High Risk";
}

function badgeClasses(risk: "Low Risk" | "Medium Risk" | "High Risk") {
  if (risk === "Low Risk") return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (risk === "Medium Risk") return "bg-amber-100 text-amber-800 border-amber-200";
  return "bg-rose-100 text-rose-800 border-rose-200";
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export default function Dashboard() {
  const [apiBase, setApiBase] = useState(API_BASE_DEFAULT);

  const [mode, setMode] = useState<Mode>("paste");

  const [projectName, setProjectName] = useState("My Project");

  // paste mode
  const [filename, setFilename] = useState("main.py");
  const [code, setCode] = useState("");

  // upload mode
  const [zipFile, setZipFile] = useState<File | null>(null);

  // repo mode (placeholder)
  const [repoUrl, setRepoUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");

  // scan state
  const [scanId, setScanId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("IDLE");
  const [isRunning, setIsRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // results
  const [results, setResults] = useState<ScanResultsResponse | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  // history
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Load history on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as HistoryItem[];
      if (Array.isArray(parsed)) setHistory(parsed);
    } catch {
      // ignore
    }
  }, []);

  // Persist history
  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(history.slice(0, 25)));
    } catch {
      // ignore
    }
  }, [history]);

  const latest = useMemo(() => history[0] ?? null, [history]);

  const derived = useMemo(() => {
    const scoreNum = Number(results?.score?.final_score ?? results?.score?.finalScore ?? results?.score?.score ?? results?.score?.value);
    const finalScore = Number.isFinite(scoreNum) ? clamp(scoreNum, 0, 100) : 0;

    const penaltyNum = Number(results?.score?.penalty ?? results?.score?.total_penalty ?? results?.score?.totalPenalty);
    const penalty = Number.isFinite(penaltyNum) ? penaltyNum : 0;

    const issues =
      Number(results?.metrics?.totals?.issues ?? results?.metrics?.issues ?? results?.metrics?.total_issues ?? results?.metrics?.totalIssues) || 0;

    const loc = Number(results?.metrics?.totals?.loc ?? results?.metrics?.loc ?? results?.metrics?.lines_of_code ?? results?.metrics?.linesOfCode) || 0;

    const risk = riskFromScore(finalScore);

    const recurring: Array<{ key: string; count: number }> =
      results?.metrics?.most_recurring_issues ??
      results?.metrics?.mostRecurringIssues ??
      [];

    const topFiles: Array<{ file: string; count: number }> = results?.metrics?.top_files ?? results?.metrics?.topFiles ?? [];

    return { finalScore, penalty, issues, loc, risk, recurring, topFiles };
  }, [results]);

  const statusLine = useMemo(() => {
    const s = status?.toLowerCase?.() ?? "";
    if (isRunning) return "Running…";
    if (s.includes("done") || s.includes("ok")) return "Done ✅";
    if (s.includes("error")) return "Error ❌";
    if (scanId) return "Ready ✅";
    return "Idle";
  }, [status, isRunning, scanId]);

  async function createScan(): Promise<string> {
    const resp = await api<ScanCreateResponse>(`${apiBase}/scans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_name: projectName }),
    });
    return resp.scan_id;
  }

  async function pasteCode(id: string) {
    await api(`${apiBase}/scans/${id}/paste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, content: code }),
    });
  }

  async function uploadZip(id: string) {
    if (!zipFile) throw new Error("Please choose a .zip file first.");
    const fd = new FormData();
    fd.append("file", zipFile);

    const res = await fetch(`${apiBase}/scans/${id}/upload_zip`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
    }
    await res.json().catch(() => ({}));
  }

  async function ingestGithub(id: string) {
    if (!repoUrl.trim()) throw new Error("Please enter a repo link.");
    // backend contract may vary; keep it simple and safe
    await api(`${apiBase}/scans/${id}/github`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repo_url: repoUrl.trim(),
        token: githubToken.trim() || undefined,
      }),
    });
  }

  async function startScan(id: string) {
    await api(`${apiBase}/scans/${id}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  }

  async function pollStatus(id: string) {
    const st = await api<ScanStatusResponse>(`${apiBase}/scans/${id}/status`);
    setStatus(st.status || "UNKNOWN");
    return st.status || "UNKNOWN";
  }

  async function fetchResults(id: string) {
    const r = await api<ScanResultsResponse>(`${apiBase}/scans/${id}/results`);
    setResults(r);
    return r;
  }

  function upsertHistory(item: HistoryItem) {
    setHistory((prev) => {
      const next = [item, ...prev.filter((x) => x.id !== item.id)];
      return next.slice(0, 25);
    });
  }

  async function runScan() {
    setErrorMsg(null);
    setIsRunning(true);
    setStatus("RUNNING");

    try {
      // 1) create scan
      const id = await createScan();
      setScanId(id);

      // 2) provide input depending on mode
      if (mode === "paste") {
        if (!code.trim()) throw new Error("Paste some code first.");
        await pasteCode(id);
      } else if (mode === "upload") {
        await uploadZip(id);
      } else {
        await ingestGithub(id);
      }

      // 3) start
      await startScan(id);

      // 4) poll status for up to ~30s (simple)
      const startedAt = Date.now();
      let s = "RUNNING";
      while (Date.now() - startedAt < 30000) {
        await new Promise((r) => setTimeout(r, 700));
        s = await pollStatus(id);
        const low = s.toLowerCase();
        if (low.includes("done") || low.includes("ok") || low.includes("error")) break;
      }

      // 5) fetch results
      const r = await fetchResults(id);

      // 6) history item
      const scoreNum = Number(r?.score?.final_score ?? r?.score?.finalScore ?? r?.score?.score ?? r?.score?.value);
      const finalScore = Number.isFinite(scoreNum) ? clamp(scoreNum, 0, 100) : 0;

      const issues =
        Number(r?.metrics?.totals?.issues ?? r?.metrics?.issues ?? r?.metrics?.total_issues ?? r?.metrics?.totalIssues) || 0;

      const loc = Number(r?.metrics?.totals?.loc ?? r?.metrics?.loc ?? r?.metrics?.lines_of_code ?? r?.metrics?.linesOfCode) || 0;

      const item: HistoryItem = {
        id,
        projectName: projectName.trim() || "My Project",
        mode,
        filename: mode === "paste" ? filename : undefined,
        createdAt: Date.now(),
        score: finalScore,
        risk: riskFromScore(finalScore),
        issues,
        loc,
      };
      upsertHistory(item);

      setStatus("DONE");
    } catch (e: any) {
      setStatus("ERROR");
      setErrorMsg(e?.message || "Something went wrong.");
    } finally {
      setIsRunning(false);
    }
  }

  async function refreshFromLatest() {
    setErrorMsg(null);
    try {
      const id = latest?.id || scanId;
      if (!id) throw new Error("No scan to refresh yet.");
      setScanId(id);
      await pollStatus(id);
      await fetchResults(id);
    } catch (e: any) {
      setErrorMsg(e?.message || "Refresh failed.");
    }
  }

  function clearHistory() {
    setHistory([]);
    setResults(null);
    setScanId(null);
    setStatus("IDLE");
    setErrorMsg(null);
  }

  function loadHistoryItem(item: HistoryItem) {
    setScanId(item.id);
    setErrorMsg(null);
    refreshFromLatest();
  }

  return (
    <div className="relative min-h-screen px-6 pt-10 pb-24">
      {/* Header */}
      <header className="pt-10 pb-6 text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900">
          Security &amp; Quality Dashboard
        </h1>
        <div className="mt-3 text-xs text-slate-500">
          API:{" "}
          <input
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            className="ml-2 w-[240px] rounded-lg border border-white/50 bg-white/50 px-2 py-1 outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
      </header>

      {/* Top cards row */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Card */}
        <div className="lg:col-span-2 rounded-3xl bg-white/45 border border-white/40 shadow-sm p-6">
          {/* Project row */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex-1">
              <label className="block text-sm font-semibold text-slate-700 mb-2">Project name</label>
              <input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="w-full rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                placeholder="My Project"
              />
            </div>

            <button
              onClick={runScan}
              disabled={isRunning}
              className="rounded-2xl bg-slate-900 text-white px-6 py-3 font-semibold shadow hover:opacity-95 disabled:opacity-60"
            >
              {isRunning ? "Running…" : "Run scan"}
            </button>
          </div>

          {/* Mode tabs */}
          <div className="mt-5 flex gap-2">
            <button
              onClick={() => setMode("paste")}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                mode === "paste"
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white/55 text-slate-700 border-white/40 hover:bg-white/70"
              }`}
            >
              Paste code
            </button>
            <button
              onClick={() => setMode("upload")}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                mode === "upload"
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white/55 text-slate-700 border-white/40 hover:bg-white/70"
              }`}
            >
              Upload files
            </button>
            <button
              onClick={() => setMode("repo")}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${
                mode === "repo"
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white/55 text-slate-700 border-white/40 hover:bg-white/70"
              }`}
            >
              Repo link
            </button>
          </div>

          {/* Mode content */}
          <div className="mt-5">
            {mode === "paste" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Virtual filename</label>
                  <input
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    className="w-full rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                    placeholder="main.py"
                  />
                  <div className="mt-2 text-xs text-slate-500">Stored in backend for scanning.</div>

                  <div className="mt-6 text-sm text-slate-700">
                    <span className="font-semibold">Status:</span> {statusLine}
                  </div>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Code</label>
                  <textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="w-full min-h-[200px] rounded-2xl border border-white/50 bg-white/60 px-4 py-3 font-mono text-sm outline-none focus:ring-2 focus:ring-sky-200"
                    placeholder="Paste your code here..."
                  />
                </div>
              </div>
            )}

            {mode === "upload" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Upload Project (.zip)</label>

                  <input
                    id="zip-upload"
                    type="file"
                    accept=".zip"
                    onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />

                  <label
                    htmlFor="zip-upload"
                    className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-white/60 hover:bg-white/80 transition cursor-pointer py-10 px-6 text-center"
                  >
                    <div className="text-3xl mb-3">📦</div>
                    <div className="text-sm font-semibold text-slate-800">Click to upload ZIP file</div>
                    <div className="text-xs text-slate-500 mt-1">Only .zip files supported</div>
                  </label>

                  {zipFile && (
                    <div className="mt-4 flex items-center justify-between bg-white/70 border border-white/50 rounded-xl px-4 py-3 text-sm">
                      <span className="font-medium text-slate-800 truncate">{zipFile.name}</span>
                      <button onClick={() => setZipFile(null)} className="text-xs text-rose-600 hover:underline">
                        Remove
                      </button>
                    </div>
                  )}

                  <div className="mt-5 text-sm text-slate-700">
                    <span className="font-semibold">Status:</span> {statusLine}
                  </div>
                </div>

                <div className="rounded-2xl bg-white/40 border border-white/40 p-5 text-sm text-slate-600">
                  Upload your project as a zip.
                  <div className="mt-2 text-xs text-slate-500">
                    Recommended: remove <code>node_modules</code>, <code>.venv</code>, <code>dist</code>, <code>build</code> before zipping.
                  </div>
                </div>
              </div>
            )}

            {mode === "repo" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Repository URL</label>
                  <input
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    className="w-full rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                    placeholder="https://github.com/user/repo"
                  />

                  <label className="block text-sm font-semibold text-slate-700 mt-4 mb-2">GitHub Token (optional)</label>
                  <input
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    className="w-full rounded-2xl border border-white/50 bg-white/60 px-4 py-3 outline-none focus:ring-2 focus:ring-sky-200"
                    placeholder="ghp_..."
                  />

                  <div className="mt-5 text-sm text-slate-700">
                    <span className="font-semibold">Status:</span> {statusLine}
                  </div>
                </div>

                <div className="rounded-2xl bg-white/40 border border-white/40 p-5 text-sm text-slate-600">
                  Repo ingestion is optional. If your backend github endpoint differs, tell me the request body it expects and I’ll match it.
                </div>
              </div>
            )}
          </div>

          {/* Errors */}
          {errorMsg && (
            <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {errorMsg}
            </div>
          )}
        </div>

        {/* History card */}
        <div className="rounded-3xl bg-white/45 border border-white/40 shadow-sm p-6">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xl font-extrabold text-slate-900">History</div>
              <div className="text-xs text-slate-500 mt-1">Saved locally in this browser.</div>
            </div>
            <button onClick={clearHistory} className="text-sm font-semibold text-slate-600 hover:underline">
              Clear
            </button>
          </div>

          <div className="mt-4 space-y-3 max-h-[360px] overflow-auto pr-1">
            {history.length === 0 && (
              <div className="rounded-2xl bg-white/55 border border-white/40 p-4 text-sm text-slate-600">
                No history yet. Run your first scan ✨
              </div>
            )}

            {history.map((h) => (
              <button
                key={h.id}
                onClick={() => loadHistoryItem(h)}
                className="w-full text-left rounded-2xl bg-white/55 border border-white/40 p-4 hover:bg-white/70 transition"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="font-bold text-slate-900 truncate">{h.projectName}</div>
                  <div className="font-extrabold text-slate-900">
                    {(h.score ?? 0).toFixed(2)}/100
                  </div>
                </div>

                <div className="mt-1 text-xs text-slate-600">
                  {h.mode === "paste" ? `Paste • ${h.filename ?? "file"}` : h.mode === "upload" ? "Upload ZIP" : "Repo"}
                  {" • "}
                  {h.issues ?? 0} issue{(h.issues ?? 0) === 1 ? "" : "s"}
                  {" • "}
                  LOC {h.loc ?? 0}
                  {" • "}
                  {fmtAgo(h.createdAt)}
                </div>

                <div className="mt-2 flex items-center justify-between">
                  <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border ${badgeClasses(h.risk ?? "High Risk")}`}>
                    {h.risk ?? "High Risk"}
                  </span>

                  <span className="text-[11px] text-slate-500 truncate max-w-[200px]">
                    ID: {h.id.slice(0, 8)}…{h.id.slice(-4)}
                  </span>
                </div>
              </button>
            ))}
          </div>

          <button
            onClick={refreshFromLatest}
            className="mt-4 w-full rounded-2xl bg-white/70 border border-white/50 px-4 py-3 font-semibold text-slate-800 hover:bg-white/85 transition"
          >
            Refresh results
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="max-w-6xl mx-auto mt-6 rounded-3xl bg-white/45 border border-white/40 shadow-sm p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-2xl font-extrabold text-slate-900">Latest results</div>
            <div className="text-xs text-slate-500 mt-1">
              Your score &amp; metrics appear here after a scan{latest ? ` (Last updated: ${fmtAgo(latest.createdAt)})` : ""}.
            </div>
          </div>

          <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border ${badgeClasses(derived.risk)}`}>
            {derived.risk}
          </span>
        </div>

        {/* Score tiles */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="text-[11px] tracking-wide font-bold text-slate-500">FINAL SCORE</div>
            <div className="mt-2 text-3xl font-extrabold text-slate-900">
              {derived.finalScore.toFixed(2)}
              <span className="text-base font-bold text-slate-500">/100</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">Density-based scoring (0–100).</div>
          </div>

          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="text-[11px] tracking-wide font-bold text-slate-500">TOTAL ISSUES</div>
            <div className="mt-2 text-3xl font-extrabold text-slate-900">{derived.issues}</div>
            <div className="mt-1 text-xs text-slate-500">All tools combined.</div>
          </div>

          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="text-[11px] tracking-wide font-bold text-slate-500">PENALTY</div>
            <div className="mt-2 text-3xl font-extrabold text-slate-900">{derived.penalty.toFixed(2)}</div>
            <div className="mt-1 text-xs text-slate-500">Score reduction.</div>
          </div>

          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="text-[11px] tracking-wide font-bold text-slate-500">LOC</div>
            <div className="mt-2 text-3xl font-extrabold text-slate-900">{derived.loc}</div>
            <div className="mt-1 text-xs text-slate-500">Lines of code.</div>
          </div>
        </div>

        {/* Extra tiles */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="font-extrabold text-slate-900">Most recurring issues</div>
            <div className="mt-3 space-y-2">
              {derived.recurring?.length ? (
                derived.recurring.slice(0, 5).map((x) => (
                  <div key={x.key} className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-slate-800">{x.key}</span>
                    <span className="text-slate-600">{x.count}</span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-600">No recurring issues yet.</div>
              )}
            </div>
          </div>

          <div className="rounded-2xl bg-white/55 border border-white/40 p-5">
            <div className="font-extrabold text-slate-900">Top files</div>
            <div className="mt-3 space-y-2">
              {derived.topFiles?.length ? (
                derived.topFiles.slice(0, 5).map((x) => (
                  <div key={x.file} className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-slate-800 truncate">{x.file}</span>
                    <span className="text-slate-600">{x.count}</span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-600">No file breakdown yet.</div>
              )}
            </div>
          </div>
        </div>

        {/* Raw JSON */}
        <button
          onClick={() => setShowRaw((v) => !v)}
          className="mt-5 text-sm font-bold text-slate-700 hover:underline"
        >
          {showRaw ? "▼" : "▶"} Raw results JSON (debug)
        </button>

        {showRaw && (
          <pre className="mt-3 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 text-slate-100 p-4 text-xs">
{JSON.stringify(results, null, 2)}
          </pre>
        )}
      </div>

      <footer className="mt-10 text-center text-xs text-slate-500">
        Final Folder • AI-Powered Code Intelligence &amp; Review Platform
      </footer>
    </div>
  );
}