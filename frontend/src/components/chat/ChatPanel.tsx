import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useAskQuestion } from "@/api/queries";
import type { Citation, Document, QueryResponse } from "@/api/types";
import { AnswerView } from "@/components/chat/AnswerView";
import { QueryForm } from "@/components/chat/QueryForm";
import { RetrievedChunksPanel } from "@/components/chat/RetrievedChunksPanel";
import { PdfViewerDialog } from "@/components/pdf/PdfViewerDialog";
import { ApiError, friendlyMessage } from "@/lib/errors";

interface ChatPanelProps {
  selectedDoc: Document | null;
}

const SUGGESTIONS = [
  "Summarise the key points.",
  "What does this document conclude?",
  "List the main sections and what they cover.",
];

// The API answers in one response, so the stage is inferred from elapsed time:
// retrieval (and the optional rerank) take about a second; the rest is the LLM.
function stageLabel(elapsedS: number, rerank: boolean): string {
  if (elapsedS < 1) return "searching index…";
  if (rerank && elapsedS < 2) return "reranking candidates…";
  return "drafting answer…";
}

function docTypeFromFilename(filename: string): "pdf" | "markdown" {
  return filename.toLowerCase().endsWith(".pdf") ? "pdf" : "markdown";
}

function LoadingCard({ elapsedS, rerank }: { elapsedS: number; rerank: boolean }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-[22px] shadow-card">
      <div className="mb-4 flex items-center justify-between font-mono text-[11px] tracking-[0.04em]">
        <span className="text-accent-brand">{stageLabel(elapsedS, rerank)}</span>
        <span className="text-ink-8 tabular-nums">{elapsedS}s</span>
      </div>
      <div className="flex flex-col gap-2.5">
        {["92%", "78%", "55%"].map((w) => (
          <div
            key={w}
            style={{ width: w }}
            className="h-[11px] rounded-[3px] bg-[linear-gradient(90deg,#f1eee9_0%,#e6e2db_50%,#f1eee9_100%)] bg-[length:320px_100%] animate-shimmer"
          />
        ))}
      </div>
    </section>
  );
}

export function ChatPanel({ selectedDoc }: ChatPanelProps) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [rerank, setRerank] = useState(true);
  const [scopeAll, setScopeAll] = useState(true);
  const [elapsedS, setElapsedS] = useState(0);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [hoveredChunkId, setHoveredChunkId] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const askQuestion = useAskQuestion();
  const busy = askQuestion.isPending;

  useEffect(() => {
    if (!busy) return;
    const startedAt = Date.now();
    const id = window.setInterval(() => {
      setElapsedS(Math.floor((Date.now() - startedAt) / 1000));
    }, 250);
    return () => window.clearInterval(id);
  }, [busy]);

  function submit() {
    const question = query.trim();
    if (!question || busy) return;
    setElapsedS(0);
    const scoped = !scopeAll && selectedDoc !== null;
    askQuestion.mutate(
      {
        question,
        top_k: topK,
        rerank,
        filters: scoped ? { document_ids: [selectedDoc.document_id] } : null,
      },
      {
        onSuccess: (data) => {
          setResult(data);
          setHoveredChunkId(null);
        },
        onError: (err) => {
          toast.error(
            err instanceof ApiError ? friendlyMessage(err) : "Failed to get an answer",
          );
        },
      },
    );
  }

  return (
    <div className="flex flex-col gap-4 min-[1100px]:min-h-0 min-[1100px]:flex-1">
      <QueryForm
        query={query}
        onQueryChange={setQuery}
        topK={topK}
        onTopKChange={setTopK}
        rerank={rerank}
        onRerankChange={setRerank}
        scopeAll={scopeAll}
        onScopeAllChange={setScopeAll}
        selectedDoc={selectedDoc}
        busy={busy}
        onSubmit={submit}
      />

      {!busy && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-8">
            try
          </span>
          {SUGGESTIONS.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => setQuery(text)}
              className="rounded-full border border-line bg-surface px-[11px] py-1.5 text-[12.5px] text-ink-4 transition-colors duration-150 hover:border-[oklch(0.7_0.06_205)] hover:text-accent-hover"
            >
              {text}
            </button>
          ))}
        </div>
      )}

      {busy && <LoadingCard elapsedS={elapsedS} rerank={rerank} />}

      {/* Desktop: fills the remaining height; answer and sources scroll on their own. */}
      {!busy && result && (
        <section className="grid grid-cols-1 items-start gap-5 min-[1100px]:min-h-0 min-[1100px]:flex-1 min-[1100px]:grid-cols-[minmax(0,1fr)_340px] min-[1100px]:grid-rows-[minmax(0,1fr)]">
          <div className="min-[1100px]:max-h-full min-[1100px]:overflow-y-auto">
            <AnswerView
              result={result}
              hoveredChunkId={hoveredChunkId}
              onHoverChunk={setHoveredChunkId}
              onCitationClick={setActiveCitation}
              onRegenerate={submit}
            />
          </div>
          <div className="min-[1100px]:max-h-full min-[1100px]:overflow-y-auto min-[1100px]:pr-1">
            <RetrievedChunksPanel
              chunks={result.retrieved_chunks}
              context={result.context}
              hoveredChunkId={hoveredChunkId}
              onHoverChunk={setHoveredChunkId}
              onOpen={setActiveCitation}
            />
          </div>
        </section>
      )}

      <PdfViewerDialog
        citation={activeCitation}
        docType={activeCitation ? docTypeFromFilename(activeCitation.filename) : null}
        onOpenChange={(open) => !open && setActiveCitation(null)}
      />
    </div>
  );
}
