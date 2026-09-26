import { useId } from "react";
import { toast } from "sonner";

import { useUploadDocument } from "@/api/queries";
import { ApiError, friendlyMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";

const ACCEPTED = [".pdf", ".md", ".markdown"];

export function UploadDropzone() {
  const inputId = useId();
  const upload = useUploadDocument();

  function isSupported(filename: string) {
    return ACCEPTED.some((ext) => filename.toLowerCase().endsWith(ext));
  }

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!isSupported(file.name)) {
      toast.error("Only .pdf and .md/.markdown files are supported.");
      return;
    }
    upload.mutate(file, {
      onSuccess: (res) => {
        toast.success(res.skipped ? `${file.name} was already ingested` : `${file.name} ingested`);
      },
      onError: (err) => {
        toast.error(err instanceof ApiError ? friendlyMessage(err) : "Upload failed");
      },
    });
  }

  return (
    <label
      htmlFor={inputId}
      className={cn(
        "flex cursor-pointer flex-col items-center gap-2 rounded-[10px] border border-dashed border-line-dashed bg-surface-2 px-3.5 py-5 text-center transition-colors duration-150 hover:border-accent-hover hover:bg-[#f4f8f9]",
        upload.isPending && "pointer-events-none opacity-60",
      )}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        handleFiles(e.dataTransfer.files);
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#8c867d"
        strokeWidth="1.6"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M12 16V4" />
        <path d="M7 9l5-5 5 5" />
        <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
      </svg>
      <span className="text-[12.5px] leading-[1.5] text-ink-5">
        {upload.isPending ? (
          "Uploading…"
        ) : (
          <>
            Drop a <strong className="font-semibold text-ink-strong">PDF</strong> or{" "}
            <strong className="font-semibold text-ink-strong">Markdown</strong> file
            <br />
            or click to browse
          </>
        )}
      </span>
      <input
        id={inputId}
        type="file"
        accept={ACCEPTED.join(",")}
        className="hidden"
        disabled={upload.isPending}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </label>
  );
}
