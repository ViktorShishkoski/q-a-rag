// Mirrors app/generation/prompts.py::CITATION_TAG_PATTERN — the answer text
// returned by POST /query contains literal "[filename p.N]" / "[filename]"
// tags. This turns each tag that resolves to a real Citation into a markdown
// link with a "citation:<index>" href, which AnswerView's custom link
// renderer intercepts instead of navigating.

import type { Citation } from "@/api/types";

const CITATION_TAG_PATTERN = /\[([^[\]]+?)(?:\s+p\.(\d+)(?:-(\d+))?)?\]/g;

export const CITATION_HREF_PREFIX = "citation:";

export function linkifyCitations(answer: string, citations: Citation[]): string {
  return answer.replace(CITATION_TAG_PATTERN, (match, filename: string, page?: string) => {
    const index = citations.findIndex(
      (c) => c.filename === filename.trim() && (page === undefined || String(c.page ?? "") === page),
    );
    if (index === -1) return match;
    return `[${match}](${CITATION_HREF_PREFIX}${index})`;
  });
}

export function citationFromHref(href: string, citations: Citation[]): Citation | undefined {
  if (!href.startsWith(CITATION_HREF_PREFIX)) return undefined;
  const index = Number(href.slice(CITATION_HREF_PREFIX.length));
  return citations[index];
}
