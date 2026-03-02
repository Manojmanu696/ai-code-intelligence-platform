export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white/80" />
      <div className="text-sm text-white/80">{label}</div>
    </div>
  );
}