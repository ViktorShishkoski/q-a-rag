interface TimingBadgeProps {
  timingMs: Record<string, number>;
}

/** The latency read-out in the answer-card header — a single mono figure in
 * seconds (backend reports `retrieval_ms` + `generation_ms`, no total). */
export function TimingBadge({ timingMs }: TimingBadgeProps) {
  const total = Object.values(timingMs).reduce((a, b) => a + b, 0);
  if (total <= 0) return null;
  return <span className="tabular-nums">{(total / 1000).toFixed(2)}s</span>;
}
