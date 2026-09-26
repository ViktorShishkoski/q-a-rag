// The one deep module for all HTTP: every component/hook goes through
// apiFetch/postForm instead of calling fetch() directly. Base URL is left
// relative — the Vite dev proxy and the production static mount both serve
// the frontend from the same origin as the API, so no host/CORS config is
// needed here (see docs/ARCHITECTURE.md's UI serving model).

import { ApiError, toApiError } from "@/lib/errors";

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

async function withNetworkErrors<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("Could not reach the backend", 0, "NetworkError");
  }
}

export function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return withNetworkErrors(async () => {
    const response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    return handle<T>(response);
  });
}

export function postForm<T>(path: string, form: FormData): Promise<T> {
  return withNetworkErrors(async () => {
    const response = await fetch(path, { method: "POST", body: form });
    return handle<T>(response);
  });
}

/** URL for the raw source file (PDF or Markdown) — passed directly as a
 * `src`/`file` prop, never fetched through apiFetch (not JSON). */
export function documentFileUrl(documentId: string): string {
  return `/documents/${encodeURIComponent(documentId)}/file`;
}

export async function fetchText(path: string): Promise<string> {
  return withNetworkErrors(async () => {
    const response = await fetch(path);
    if (!response.ok) throw await toApiError(response);
    return response.text();
  });
}
