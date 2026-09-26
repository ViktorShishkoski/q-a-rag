import type { Citation, ContextInfo, ScoredChunk } from "@/api/types";
import { SectionLabel } from "@/components/layout/SectionLabel";
import { cn } from "@/lib/utils";

interface RetrievedChunksPanelProps {
  chunks: ScoredChunk[];
  context?: ContextInfo;
  hoveredChunkId: string | null;
  onHoverChunk: (id: string | null) => void;
  onOpen: (citation: Citation) => void;
}

function primaryScore(sc: ScoredChunk): number {
  return sc.rerank_score ?? sc.fused_score ?? sc.dense_score ?? 0;
}

function chunkToCitation(sc: ScoredChunk): Citation {
  const c = sc.chunk;
  return {
    document_id: c.document_id,
    filename: c.filename,
    page: c.page_start,
    section: c.section,
    chunk_id: c.chunk_id,
    quote: c.text,
    char_start: c.char_start,
    char_end: c.char_end,
  };
}

export function RetrievedChunksPanel({
  chunks,
  context,
  hoveredChunkId,
  onHoverChunk,
  onOpen,
}: RetrievedChunksPanelProps) {
  const usedIds = new Set(context?.chunk_ids ?? []);
  const scores = chunks.map(primaryScore);
  const lo = scores.length ? Math.min(...scores) : 0;
  const hi = scores.length ? Math.max(...scores) : 0;
  const barWidth = (score: number) => (hi > lo ? Math.max(4, ((score - lo) / (hi - lo)) * 100) : 100);

  return (
    <aside className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between">
        <SectionLabel>Retrieved</SectionLabel>
        <span className="font-mono text-[10px] text-ink-9">{chunks.length}</span>
      </div>

      {chunks.length === 0 && (
        <p className="font-mono text-[10.5px] text-ink-7">no chunks retrieved</p>
      )}

      {chunks.map((sc) => {
        const on = hoveredChunkId === sc.chunk.chunk_id;
        const used = usedIds.has(sc.chunk.chunk_id);
        const score = primaryScore(sc);
        const loc = [
          sc.chunk.page_start ? `p. ${sc.chunk.page_start}` : null,
          `c/${sc.chunk.chunk_index}`,
        ]
          .filter(Boolean)
          .join(" · ");

        return (
          <button
            type="button"
            key={sc.chunk.chunk_id}
            onMouseEnter={() => onHoverChunk(sc.chunk.chunk_id)}
            onMouseLeave={() => onHoverChunk(null)}
            onFocus={() => onHoverChunk(sc.chunk.chunk_id)}
            onBlur={() => onHoverChunk(null)}
            onClick={() => onOpen(chunkToCitation(sc))}
            title={context ? (used ? "Sent to the model" : "Retrieved but not in context") : undefined}
            className={cn(
              "rounded-[10px] border px-[13px] py-3 text-left transition-colors duration-100",
              on
                ? "border-accent-border-strong bg-[#f6fbfb] shadow-lift"
                : "border-line bg-surface hover:border-line-hover",
              !used && context && "opacity-60",
            )}
          >
            <div className="mb-[7px] flex items-center justify-between gap-2.5">
              <span
                className={cn(
                  "min-w-[18px] rounded-[4px] px-[5px] py-px text-center font-mono text-[10.5px]",
                  on ? "bg-accent-brand text-white" : "bg-accent-tint text-accent-brand",
                )}
              >
                {sc.rank}
              </span>
              <span className="font-mono text-[10.5px] text-ink-7">{loc}</span>
            </div>
            <div className="line-clamp-4 text-[12.5px] leading-[1.55] text-ink-4">
              {sc.chunk.text}
            </div>
            <div className="mt-[9px] flex items-center gap-2">
              <div className="h-[3px] flex-1 overflow-hidden rounded-[2px] bg-line-3">
                <div
                  style={{ width: `${barWidth(score)}%` }}
                  className={cn("h-full", on ? "bg-accent-brand" : "bg-accent-muted")}
                />
              </div>
              <span className="font-mono text-[10.5px] text-ink-6 tabular-nums">
                {score.toFixed(2)}
              </span>
            </div>
          </button>
        );
      })}
    </aside>
  );
}
