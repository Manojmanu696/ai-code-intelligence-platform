import type { Severity } from "../../types/scan";

export function SeverityBreakdown({
  bySeverity,
}: {
  bySeverity: Record<Severity, number>;
}) {
  const rows: { key: Severity; label: string }[] = [
    { key: "high", label: "High" },
    { key: "medium", label: "Medium" },
    { key: "low", label: "Low" },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="text-sm font-semibold">Severity Breakdown</div>
      <div className="mt-4 space-y-3">
        {rows.map((r) => (
          <div key={r.key} className="flex items-center justify-between">
            <div className="text-sm text-white/70">{r.label}</div>
            <div className="text-sm font-semibold">{bySeverity[r.key] ?? 0}</div>
          </div>
        ))}
      </div>
    </div>
  );
}