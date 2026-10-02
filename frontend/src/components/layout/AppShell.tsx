import type { ReactNode } from "react";

import { useDocuments, useHealth } from "@/api/queries";
import { cn } from "@/lib/utils";

function StatusPill() {
  const { data, isError } = useHealth();
  const state = isError || !data ? "offline" : data.status === "ok" ? "healthy" : "degraded";
  const dotClass =
    state === "healthy" ? "bg-ok" : state === "degraded" ? "bg-warning" : "bg-destructive";
  const title =
    data && "ollama" in data
      ? `ollama reachable: ${data.ollama.reachable} · model: ${data.ollama.model_available} · qdrant: ${data.qdrant}`
      : undefined;

  return (
    <div
      title={title}
      className="flex items-center gap-[7px] rounded-full border border-accent-pill-border bg-accent-pill-bg py-[5px] pr-[11px] pl-[9px]"
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          dotClass,
          state === "healthy" && "animate-pulse-dot",
        )}
      />
      <span
        className={cn(
          "font-mono text-[11px] tracking-[0.02em]",
          state === "healthy" ? "text-ok-ink" : "text-ink-5",
        )}
      >
        {state}
      </span>
    </div>
  );
}

interface AppShellProps {
  rail: ReactNode;
  children: ReactNode;
}

export function AppShell({ rail, children }: AppShellProps) {
  const { data } = useDocuments();
  const documents = data?.documents ?? [];
  const chunkCount = documents.reduce((n, d) => n + (d.chunk_count ?? 0), 0);

  return (
    <div className="flex min-h-svh flex-col bg-page text-ink min-[1100px]:h-svh min-[1100px]:overflow-hidden">
      <header className="sticky top-0 z-10 flex h-[60px] shrink-0 items-center justify-between gap-6 border-b border-line bg-brand-bar px-7">
        <div className="flex items-baseline gap-3 rounded-[5px] bg-[linear-gradient(180deg,#69D9CF,#F4EAE0)] px-1.5">
          <span className="text-[16px] font-bold tracking-[-0.01em] text-brand-ink">Q&amp;A RAG</span>
          <span className="font-mono text-[11px] tracking-[0.04em] text-brand-ink-2">
            retrieval console
          </span>
        </div>
        <div className="flex items-center gap-[18px]">
          <div className="hidden items-center gap-4 font-mono text-[11px] text-ink-6 sm:flex">
            <span>{documents.length} docs</span>
            <span>{chunkCount} chunks</span>
          </div>
          <StatusPill />
        </div>
      </header>

      {/* Desktop: the shell is exactly one viewport tall; the rail and the main
          column each scroll internally so nothing is pushed below the fold. */}
      <div className="grid flex-1 grid-cols-1 content-start items-start min-[1100px]:min-h-0 min-[1100px]:grid-cols-[300px_minmax(0,1fr)] min-[1100px]:grid-rows-[minmax(0,1fr)] min-[1100px]:items-stretch">
        <aside className="flex flex-col gap-[22px] border-b border-line bg-surface px-5 py-[22px] min-[1100px]:min-h-0 min-[1100px]:overflow-y-auto min-[1100px]:border-r min-[1100px]:border-b-0">
          {rail}
        </aside>
        <main className="flex w-full flex-col bg-main px-[34px] pt-6 pb-10 min-[1100px]:min-h-0 min-[1100px]:overflow-hidden min-[1100px]:pb-6">
          {children}
        </main>
      </div>
    </div>
  );
}
