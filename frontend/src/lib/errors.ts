// Normalizes the two error shapes the backend can return (see docs/API.md):
//   - RagError subclasses: { error: string, type: string }
//   - Pydantic/FastAPI validation failures (422): { detail: [{ msg, loc, type }, ...] }
// plus network-level failures (fetch throwing before a response exists).

export class ApiError extends Error {
  readonly status: number;
  /** RagError class name (e.g. "OllamaUnavailableError"), or "ValidationError" /
   * "NetworkError" for the other two cases. */
  readonly type: string;

  constructor(message: string, status: number, type: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.type = type;
  }
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return new ApiError(response.statusText || "Request failed", response.status, "UnknownError");
  }

  if (isRagErrorBody(body)) {
    return new ApiError(body.error, response.status, body.type);
  }
  if (isValidationErrorBody(body)) {
    const message = body.detail.map((d) => d.msg).join("; ") || "Validation failed";
    return new ApiError(message, response.status, "ValidationError");
  }
  return new ApiError("Request failed", response.status, "UnknownError");
}

function isRagErrorBody(body: unknown): body is { error: string; type: string } {
  return (
    typeof body === "object" &&
    body !== null &&
    typeof (body as Record<string, unknown>).error === "string" &&
    typeof (body as Record<string, unknown>).type === "string"
  );
}

function isValidationErrorBody(body: unknown): body is { detail: { msg: string }[] } {
  return (
    typeof body === "object" &&
    body !== null &&
    Array.isArray((body as Record<string, unknown>).detail)
  );
}

/** Friendly, user-facing message for known RagError types. Falls back to the
 * raw message for anything not worth special-casing. */
export function friendlyMessage(err: ApiError): string {
  switch (err.type) {
    case "OllamaUnavailableError":
    case "OllamaModelNotFoundError":
      return "The generation model is unavailable right now. Check that Ollama is running.";
    case "OllamaGenerationError":
      return "The generation model failed to answer. Try again.";
    case "DocumentNotFoundError":
      return "That document no longer exists.";
    case "UnsupportedFileTypeError":
      return "Only .pdf and .md/.markdown files are supported.";
    case "NetworkError":
      return "Could not reach the backend. Is the server running?";
    default:
      return err.message;
  }
}
