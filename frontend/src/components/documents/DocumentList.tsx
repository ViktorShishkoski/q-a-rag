import { useState } from "react";
import { ListTreeIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { useDeleteDocument, useDocuments } from "@/api/queries";
import { DocumentOutline } from "@/components/documents/DocumentOutline";
import { SectionLabel } from "@/components/layout/SectionLabel";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, friendlyMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

interface DocumentListProps {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function DocumentList({ selectedId, onSelect }: DocumentListProps) {
  const { data, isLoading } = useDocuments();
  const deleteDocument = useDeleteDocument();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function handleDelete(documentId: string, filename: string) {
    deleteDocument.mutate(documentId, {
      onSuccess: () => {
        toast.success(`${filename} deleted`);
        if (selectedId === documentId) onSelect(null);
        if (expandedId === documentId) setExpandedId(null);
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? friendlyMessage(err) : "Delete failed");
      },
    });
  }

  const documents = data?.documents ?? [];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <SectionLabel>Indexed</SectionLabel>
        <span className="font-mono text-[10px] text-ink-9">{documents.length}</span>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-[52px] w-full rounded-[9px]" />
          <Skeleton className="h-[52px] w-full rounded-[9px]" />
        </div>
      ) : documents.length === 0 ? (
        <p className="font-mono text-[10.5px] leading-[1.6] text-ink-7">
          no documents indexed yet
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {documents.map((doc) => {
            const selected = selectedId === doc.document_id;
            const expanded = expandedId === doc.document_id;
            return (
              <li key={doc.document_id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(selected ? null : doc.document_id)}
                  aria-pressed={selected}
                  className={cn(
                    "w-full rounded-[9px] border px-[11px] py-2.5 text-left transition-colors duration-150",
                    selected
                      ? "border-accent-border bg-[#f4f9fa]"
                      : "border-line-3 bg-surface-3 hover:border-line-hover-2 hover:bg-surface",
                  )}
                >
                  <div className="flex items-start gap-[9px]">
                    <span
                      className={cn(
                        "mt-[5px] h-1.5 w-1.5 shrink-0 rounded-[2px]",
                        selected ? "bg-accent-hover" : "bg-[#d3cec5]",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate pr-10 text-[12.5px] leading-[1.4] font-medium text-ink-3">
                        {doc.filename}
                      </div>
                      <div className="mt-[5px] flex items-center gap-2 font-mono text-[10.5px] text-ink-7">
                        <span className="rounded-[3px] border border-line-2 px-[5px] py-px uppercase tracking-[0.04em]">
                          {doc.doc_type}
                        </span>
                        {doc.chunk_count !== null && <span>{doc.chunk_count} chunks</span>}
                        {doc.page_count !== null && <span>{doc.page_count} pp</span>}
                      </div>
                    </div>
                  </div>
                </button>

                <div className="absolute top-2 right-2 flex items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                  <button
                    type="button"
                    aria-label={expanded ? "Hide outline" : "Show outline"}
                    aria-expanded={expanded}
                    onClick={() => setExpandedId(expanded ? null : doc.document_id)}
                    className={cn(
                      "flex size-6 items-center justify-center rounded-[6px] text-ink-6 transition-colors hover:bg-line-3",
                      expanded && "bg-line-3 text-ink-3",
                    )}
                  >
                    <ListTreeIcon className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${doc.filename}`}
                    disabled={deleteDocument.isPending}
                    onClick={() => handleDelete(doc.document_id, doc.filename)}
                    className="flex size-6 items-center justify-center rounded-[6px] text-ink-6 transition-colors hover:bg-line-3 hover:text-destructive disabled:opacity-40"
                  >
                    <Trash2Icon className="size-3.5" />
                  </button>
                </div>

                {expanded && (
                  <div className="mt-1.5">
                    <DocumentOutline documentId={doc.document_id} open={expanded} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
