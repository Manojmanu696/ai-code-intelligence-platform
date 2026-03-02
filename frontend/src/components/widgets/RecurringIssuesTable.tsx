export function RecurringIssuesTable({
  items,
  limit = 10,
}: {
  items: { rule_id: string; tool: string; count: number }[];
  limit?: number;
}) {
  const rows = (items || []).slice(0, limit);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Most Recurring Issues</div>
        <div className="text-xs text-white/50">Top {limit}</div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-white/50">
            <tr>
              <th className="py-2 pr-4">Rule</th>
              <th className="py-2 pr-4">Tool</th>
              <th className="py-2">Count</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.tool}:${r.rule_id}`} className="border-t border-white/10">
                <td className="py-2 pr-4 font-mono text-xs text-white/80">{r.rule_id}</td>
                <td className="py-2 pr-4">{r.tool}</td>
                <td className="py-2">{r.count}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr className="border-t border-white/10">
                <td className="py-3 text-white/60" colSpan={3}>
                  No recurring issues found.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}