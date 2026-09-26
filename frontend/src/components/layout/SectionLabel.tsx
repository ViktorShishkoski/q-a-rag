import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SectionLabelProps {
  children: ReactNode;
  className?: string;
}

/** The mono uppercase micro-label above every zone (Corpus / Indexed / Answer /
 * Retrieved). Metrics are fixed by the design handoff. */
export function SectionLabel({ children, className }: SectionLabelProps) {
  return (
    <span
      className={cn(
        "font-mono text-[10px] uppercase tracking-[0.09em] text-ink-7",
        className,
      )}
    >
      {children}
    </span>
  );
}
