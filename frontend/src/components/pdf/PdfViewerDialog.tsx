import { useEffect, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { documentFileUrl, fetchText } from "@/api/client";
import type { Citation } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { friendlyMessage, ApiError } from "@/lib/errors";
import ReactMarkdown from "react-markdown";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

interface PdfViewerDialogProps {
  citation: Citation | null;
  docType: "pdf" | "markdown" | null;
  onOpenChange: (open: boolean) => void;
}

export function PdfViewerDialog({ citation, docType, onOpenChange }: PdfViewerDialogProps) {
  const open = citation !== null && docType !== null;
  const [numPages, setNumPages] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [markdownText, setMarkdownText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(citation?.page ?? 1);
    setNumPages(null);
    setMarkdownText(null);
    setError(null);
  }, [citation]);

  useEffect(() => {
    if (open && docType === "markdown" && citation) {
      fetchText(documentFileUrl(citation.document_id))
        .then(setMarkdownText)
        .catch((err) => setError(err instanceof ApiError ? friendlyMessage(err) : "Failed to load file"));
    }
  }, [open, docType, citation]);

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onOpenChange(false)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{citation?.filename}</DialogTitle>
          <DialogDescription>
            {citation?.section ? `${citation.section} — ` : ""}
            {citation?.page ? `Page ${citation.page}` : "Source document"}
          </DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!error && docType === "pdf" && citation && (
          <div className="flex flex-col items-center gap-3">
            <Document
              file={documentFileUrl(citation.document_id)}
              onLoadSuccess={({ numPages: n }) => setNumPages(n)}
              onLoadError={() => setError("Failed to load PDF")}
              loading={<p className="text-sm text-muted-foreground">Loading PDF…</p>}
            >
              <Page pageNumber={page} width={640} />
            </Document>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="icon"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeftIcon />
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page}
                {numPages ? ` / ${numPages}` : ""}
              </span>
              <Button
                variant="outline"
                size="icon"
                disabled={numPages !== null && page >= numPages}
                onClick={() => setPage((p) => (numPages ? Math.min(numPages, p + 1) : p + 1))}
              >
                <ChevronRightIcon />
              </Button>
            </div>
          </div>
        )}

        {!error && docType === "markdown" && (
          <div className="prose prose-sm max-w-none">
            {markdownText === null ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : (
              <ReactMarkdown>{markdownText}</ReactMarkdown>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
