export interface SearchRequest {
  query: string;
  top_k?: number;
}

export interface SearchResult {
  document_id: string;
  document_title: string;
  chunk_text: string;
  score: number;
  matter_id: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
}

export interface RetrievalRequest {
  query: string;
  top_k?: number;
  min_similarity?: number;
}

export interface RetrievalResult {
  chunk_text: string;
  document_id: string;
  document_title: string;
  matter_id: string | null;
  score: number;
  source_type: string;
}

export interface RetrievalResponse {
  results: RetrievalResult[];
}

export interface RAGQueryRequest {
  query: string;
  task_type?: string;
}

export interface SourceAttribution {
  document_id: string;
  document_title: string;
  chunk_text: string;
  score: number;
}

export interface CitationReport {
  validated: Record<string, unknown>[];
  unverified: string[];
  has_unverified: boolean;
  confidence_score: number;
}

export interface RAGQueryResponse {
  answer: string;
  sources: SourceAttribution[];
  citation_report: CitationReport;
  needs_review: boolean;
  confidence: number;
}

export interface SuggestionsResponse {
  suggestions: string[];
}
