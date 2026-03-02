export function HeatmapTable({
  heatmap,
  limit = 10,
}: {
  heatmap: Record<string, { low: number; medium: number; high: number }>;
  limit?: number;
}) {
  const rows = Object.entries(heatmap || [])
    .map(([file, s]) => ({ file, ...s, total: s.low + s.medium + s.high }))
    .sort((a, b) => b.total - a.total)
    .slice(0, limit);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Risk Heatmap</div>
        <div className="text-xs text-white/50">Top {limit} files</div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-white/50">
            <tr>
              <th className="py-2 pr-4">File</th>
              <th className="py-2 pr-4">High</th>
              <th className="py-2 pr-4">Med</th>
              <th className="py-2 pr-4">Low</th>
              <th className="py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.file} className="border-t border-white/10">
                <td className="py-2 pr-4 font-mono text-xs text-white/80">{r.file}</td>
                <td className="py-2 pr-4">{r.high}</td>
                <td className="py-2 pr-4">{r.medium}</td>
                <td className="py-2 pr-4">{r.low}</td>
                <td className="py-2">{r.total}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr className="border-t border-white/10">
                <td className="py-3 text-white/60" colSpan={5}>
                  No heatmap data found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}