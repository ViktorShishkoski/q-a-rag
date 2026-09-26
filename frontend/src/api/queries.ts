import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, postForm } from "@/api/client";
import type {
  DeleteDocumentResponse,
  DocumentListResponse,
  HealthResponse,
  IngestResponse,
  OutlineResponse,
  QueryRequest,
  QueryResponse,
} from "@/api/types";

const documentsKey = ["documents"] as const;

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/health"),
    refetchInterval: 15_000,
    retry: false,
  });
}

export function useDocuments() {
  return useQuery({
    queryKey: documentsKey,
    queryFn: () => apiFetch<DocumentListResponse>("/documents"),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return postForm<IngestResponse>("/documents", form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useOutline(documentId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["outline", documentId],
    queryFn: () =>
      apiFetch<OutlineResponse>(`/documents/${encodeURIComponent(documentId as string)}/outline`),
    enabled: enabled && documentId !== null,
    staleTime: 5 * 60_000,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch<DeleteDocumentResponse>(`/documents/${encodeURIComponent(documentId)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useAskQuestion() {
  return useMutation({
    mutationFn: (request: QueryRequest) =>
      apiFetch<QueryResponse>("/query", {
        method: "POST",
        body: JSON.stringify(request),
      }),
  });
}
