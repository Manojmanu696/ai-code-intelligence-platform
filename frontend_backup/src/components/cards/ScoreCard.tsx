function scoreBadge(score: number) {
  if (score >= 90) return "Excellent ✅";
  if (score >= 75) return "Good 👍";
  if (score >= 60) return "Needs Work ⚠️";
  return "High Risk 🚨";
}

export function ScoreCard({ score }: { score: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="text-sm text-white/60">Final Score</div>
        <div className="text-xs text-white/60">{scoreBadge(score)}</div>
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <div className="text-4xl font-semibold tracking-tight">{Math.round(score)}</div>
        <div className="text-sm text-white/60">/ 100</div>
      </div>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-white/70"
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>

      <div className="mt-2 text-xs text-white/50">
        Density-based penalty scoring (clamped 0–100).
      </div>
    </div>
  );
}