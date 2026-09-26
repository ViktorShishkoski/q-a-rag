import { useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

import type { Citation, QueryResponse } from "@/api/types";
import { TimingBadge } from "@/components/chat/TimingBadge";
import { SectionLabel } from "@/components/layout/SectionLabel";
import { CITATION_HREF_PREFIX, citationFromHref, linkifyCitations } from "@/lib/citations";
import { cn } from "@/lib/utils";

// `linkifyCitations` marks resolved tags with a `citation:<index>` href; react-
// markdown's default URL sanitiser would strip that non-standard scheme to "",
// so let it through untouched and sanitise everything else as usual.
function urlTransform(url: string): string {
  return url.startsWith(CITATION_HREF_PREFIX) ? url : defaultUrlTransform(url);
}

interface AnswerViewProps {
  result: QueryResponse;
  hoveredChunkId: string | null;
  onHoverChunk: (id: string | null) => void;
  onCitationClick: (citation: Citation) => void;
  onRegenerate: () => void;
}

// Display fallback: the model sometimes emits a `[filename p.N]` tag that the
// backend could not verify into a Citation (so `citations` has no match and
// `linkifyCitations` leaves the tag as literal text). Rather than dump the full
// filename into the prose, collapse any such leftover tag to a compact page ref.
// The look-behind / look-ahead keep it clear of tags `linkifyCitations` already
// turned into `[...](citation:N)` links.
const UNRESOLVED_TAG =
  /(?<!\[)\[[^[\]]{1,220}?\.(?:pdf|md|markdown|txt|docx)(?:\s*,?\s*pp?\.\s*(\d+(?:\s*[-–]\s*\d+)?))?\](?!\()/gi;

function collapseUnresolvedTags(markdown: string): string {
  return markdown.replace(UNRESOLVED_TAG, (_match, page?: string) =>
    page ? `[p.${page.replace(/\s+/g, "")}]` : "[source]",
  );
}

const PILL_BTN =
  "rounded-[7px] border border-line bg-surface px-2.5 py-[5px] text-[12px] text-ink-5 transition-colors hover:border-line-hover";
const FEEDBACK_BTN =
  "flex size-7 items-center justify-center rounded-[7px] border border-line bg-surface text-[12px] text-ink-6 transition-colors hover:border-line-hover";

export function AnswerView({
  result,
  hoveredChunkId,
  onHoverChunk,
  onCitationClick,
  onRegenerate,
}: AnswerViewProps) {
  const [copied, setCopied] = useState(false);
  const markdown = collapseUnresolvedTags(linkifyCitations(result.answer, result.citations));

  function copy() {
    void navigator.clipboard?.writeText(result.answer).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <article className="rounded-xl border border-line bg-surface px-[26px] py-6 shadow-card">
      <div className="mb-3.5 flex items-center justify-between gap-4">
        <SectionLabel>Answer</SectionLabel>
        <div className="flex items-center gap-3 font-mono text-[10.5px] text-ink-8">
          <TimingBadge timingMs={result.timing_ms} />
          <span className="truncate">{result.model}</span>
        </div>
      </div>

      <div className="text-pretty text-[15.5px] leading-[1.68] text-ink-2 [&_code]:font-mono [&_code]:text-[0.92em] [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5 [&>*+*]:mt-3.5">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          urlTransform={urlTransform}
          components={{
            a: ({ href, children }) => {
              const citation = href ? citationFromHref(href, result.citations) : undefined;
              if (!citation) return <a href={href}>{children}</a>;
              const n = result.citations.indexOf(citation) + 1;
              const on = hoveredChunkId === citation.chunk_id;
              return (
                <sup
                  role="button"
                  tabIndex={0}
                  onMouseEnter={() => onHoverChunk(citation.chunk_id)}
                  onMouseLeave={() => onHoverChunk(null)}
                  onFocus={() => onHoverChunk(citation.chunk_id)}
                  onBlur={() => onHoverChunk(null)}
                  onClick={() => onCitationClick(citation)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onCitationClick(citation);
                    }
                  }}
                  className={cn(
                    "ml-0.5 inline-block min-w-[15px] cursor-pointer rounded-[3px] px-[3px] py-px text-center align-super font-mono text-[9.5px] leading-[13px] no-underline transition-colors duration-100",
                    on ? "bg-accent-brand text-white" : "bg-accent-tint text-accent-brand",
                  )}
                >
                  {n}
                </sup>
              );
            },
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>

      <div className="mt-[22px] flex items-center gap-2 border-t border-line-4 pt-4">
        <button type="button" className={PILL_BTN} onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
        <button type="button" className={PILL_BTN} onClick={onRegenerate}>
          Regenerate
        </button>
        <div className="ml-auto flex gap-1.5">
          <button
            type="button"
            aria-label="Helpful"
            className={FEEDBACK_BTN}
            onClick={() => toast.success("Thanks for the feedback")}
          >
            ↑
          </button>
          <button
            type="button"
            aria-label="Not helpful"
            className={FEEDBACK_BTN}
            onClick={() => toast("Thanks for the feedback")}
          >
            ↓
          </button>
        </div>
      </div>
    </article>
  );
}
