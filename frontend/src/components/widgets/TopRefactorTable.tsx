import type { RefactorPriorityItem } from "../../types/scan";

export function TopRefactorTable({ items }: { items: RefactorPriorityItem[] }) {
  const top = (items || []).slice(0, 5);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Top Refactor Priority</div>
        <div className="text-xs text-white/50">Top 5</div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-white/50">
            <tr>
              <th className="py-2 pr-4">File</th>
              <th className="py-2 pr-4">Risk</th>
              <th className="py-2 pr-4">High</th>
              <th className="py-2 pr-4">Med</th>
              <th className="py-2 pr-4">Low</th>
              <th className="py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {top.map((it) => (
              <tr key={it.file} className="border-t border-white/10">
                <td className="py-2 pr-4 font-mono text-xs text-white/80">{it.file}</td>
                <td className="py-2 pr-4">{it.risk_score.toFixed(2)}</td>
                <td className="py-2 pr-4">{it.high}</td>
                <td className="py-2 pr-4">{it.medium}</td>
                <td className="py-2 pr-4">{it.low}</td>
                <td className="py-2">{it.total}</td>
              </tr>
            ))}
            {top.length === 0 ? (
              <tr className="border-t border-white/10">
                <td className="py-3 text-white/60" colSpan={6}>
                  No refactor candidates found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}