export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
      <div className="text-sm font-semibold text-red-200">Something went wrong</div>
      <div className="mt-1 text-sm text-red-200/80">{message}</div>
    </div>
  );
}