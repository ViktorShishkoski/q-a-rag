import type { Document } from "@/api/types";
import { cn } from "@/lib/utils";

interface QueryFormProps {
  query: string;
  onQueryChange: (value: string) => void;
  topK: number;
  onTopKChange: (value: number) => void;
  rerank: boolean;
  onRerankChange: (value: boolean) => void;
  scopeAll: boolean;
  onScopeAllChange: (value: boolean) => void;
  selectedDoc: Document | null;
  busy: boolean;
  onSubmit: () => void;
}

const TOP_K_MIN = 1;
const TOP_K_MAX = 20;

export function QueryForm({
  query,
  onQueryChange,
  topK,
  onTopKChange,
  rerank,
  onRerankChange,
  scopeAll,
  onScopeAllChange,
  selectedDoc,
  busy,
  onSubmit,
}: QueryFormProps) {
  const scoped = !scopeAll && selectedDoc !== null;

  return (
    <section className="rounded-xl border border-line bg-surface shadow-card">
      <textarea
        rows={2}
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder="Ask a question about your documents…"
        className="w-full resize-none border-0 bg-transparent px-5 pt-4 pb-1 text-[16px] leading-[1.55] tracking-[-0.005em] text-ink outline-none"
      />

      <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-3 border-t border-line-4 py-3 pr-4 pl-5">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] tracking-[0.03em] text-ink-6">top k</span>
            <div className="flex items-center overflow-hidden rounded-[7px] border border-line-2 bg-surface-2">
              <button
                type="button"
                aria-label="Decrease top k"
                onClick={() => onTopKChange(Math.max(TOP_K_MIN, topK - 1))}
                className="h-[26px] w-6 text-[14px] leading-none text-ink-5 transition-colors hover:bg-line-3"
              >
                −
              </button>
              <span className="min-w-6 text-center font-mono text-[12px] text-ink-3 tabular-nums">
                {topK}
              </span>
              <button
                type="button"
                aria-label="Increase top k"
                onClick={() => onTopKChange(Math.min(TOP_K_MAX, topK + 1))}
                className="h-[26px] w-6 text-[14px] leading-none text-ink-5 transition-colors hover:bg-line-3"
              >
                +
              </button>
            </div>
          </div>

          <button
            type="button"
            aria-pressed={rerank}
            onClick={() => onRerankChange(!rerank)}
            className={cn(
              "flex items-center gap-[7px] rounded-[7px] border px-[9px] py-[5px] transition-colors",
              rerank
                ? "border-accent-border bg-accent-surface text-accent-brand"
                : "border-line-2 bg-surface-2 text-ink-5",
            )}
          >
            <span
              className={cn(
                "h-[11px] w-[11px] rounded-[3px] border",
                rerank
                  ? "border-accent-brand bg-accent-brand shadow-[inset_0_0_0_2px_#f2f8f9]"
                  : "border-line-dashed",
              )}
            />
            <span className="font-mono text-[11px] tracking-[0.03em]">rerank</span>
          </button>

          <button
            type="button"
            disabled={selectedDoc === null}
            aria-pressed={scoped}
            onClick={() => onScopeAllChange(!scopeAll)}
            className="rounded-[7px] border border-line-2 bg-surface-2 px-[9px] py-[5px] font-mono text-[11px] tracking-[0.03em] text-ink-5 transition-colors hover:border-line-hover disabled:opacity-50 disabled:hover:border-line-2"
          >
            {scoped ? "this document only" : "all documents"}
          </button>
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={busy}
          className={cn(
            "flex items-center gap-2 rounded-lg px-4 py-[9px] text-[13.5px] font-semibold text-white shadow-btn transition-colors",
            busy ? "cursor-wait bg-accent-busy" : "bg-accent-brand hover:bg-accent-hover",
          )}
        >
          {busy && (
            <span className="h-1.5 w-1.5 rounded-full bg-current animate-[pulseDot_1s_ease-in-out_infinite]" />
          )}
          <span>{busy ? "Asking" : "Ask"}</span>
          <span className="font-mono text-[10.5px] opacity-60">⏎</span>
        </button>
      </div>
    </section>
  );
}
