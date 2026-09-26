// Mirrors app/models/{domain,requests,responses}.py — keep in sync by hand,
// there is no shared schema generation between the two.

export type DocType = "pdf" | "markdown";

export interface Document {
  document_id: string;
  filename: string;
  source_path: string;
  doc_type: DocType;
  page_count: number | null;
  ingested_at: string;
  content_hash: string;
  chunk_count: number | null;
}

export interface Chunk {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  filename: string;
  page_start: number | null;
  page_end: number | null;
  section: string | null;
  text: string;
  token_count: number;
  char_start: number;
  char_end: number;
}

export interface ScoredChunk {
  chunk: Chunk;
  dense_score: number | null;
  sparse_score: number | null;
  fused_score: number | null;
  rerank_score: number | null;
  rank: number;
}

export interface Citation {
  document_id: string;
  filename: string;
  page: number | null;
  section: string | null;
  chunk_id: string;
  quote: string;
  // Approximate offsets of the cited chunk in the document's cleaned text —
  // best-effort span highlighting only, not relied on for correctness.
  char_start: number | null;
  char_end: number | null;
}

export interface OutlineNode {
  title: string;
  level: number;
  page: number | null;
  section_path: string;
  children: OutlineNode[];
}

export interface OutlineResponse {
  document_id: string;
  outline: OutlineNode[];
}

export interface Table {
  document_id: string;
  table_index: number;
  page: number | null;
  section: string | null;
  caption: string | null;
  rows: string[][];
}

export interface TablesResponse {
  document_id: string;
  tables: Table[];
}

/** Which retrieved chunks actually reached the model for a /query answer. */
export interface ContextInfo {
  truncated: boolean;
  chunks_used: number;
  chunk_ids: string[];
}

// --- V2 analysis seams (endpoints live, providers NoOp -> implemented:false) ---

export interface ExtractionField {
  name: string;
  description: string;
  example?: string | null;
}

export interface ExtractionSchema {
  fields: ExtractionField[];
}

export interface ExtractedValue {
  field: string;
  value: string | null;
  citations: Citation[];
}

export interface StructuredExtractionResult {
  document_id: string;
  values: ExtractedValue[];
  implemented: boolean;
}

export interface DocumentComparison {
  document_ids: string[];
  question: string | null;
  summary: string;
  citations: Citation[];
  implemented: boolean;
}

export interface DocumentFilter {
  document_ids?: string[] | null;
}

export interface QueryRequest {
  question: string;
  top_k?: number;
  rerank?: boolean | null;
  filters?: DocumentFilter | null;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  retrieved_chunks: ScoredChunk[];
  context: ContextInfo;
  model: string;
  timing_ms: Record<string, number>;
}

export interface IngestResponse {
  document: Document;
  chunks_created: number;
  skipped: boolean;
}

export interface DocumentListResponse {
  documents: Document[];
}

export interface DeleteDocumentResponse {
  document_id: string;
  deleted_chunks: number;
}

export interface OllamaHealth {
  reachable: boolean;
  model_available: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  ollama: OllamaHealth;
  qdrant: boolean;
}
