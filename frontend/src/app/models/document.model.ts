export interface DocumentVersion {
  id: string;
  version_number: number;
  storage_key: string;
  sha256_hash: string;
  mime_type: string;
  size_bytes: number;
  parser_status: DocumentParserStatus;
  created_at: string;
  created_by: string;
}

export type DocumentParserStatus =
  | 'pending'
  | 'ready'
  | 'failed'
  | 'processing';

export interface DocumentOut {
  id: string;
  law_firm_id: string;
  matter_id: string | null;
  owner_user_id: string;
  title: string;
  classification: string | null;
  is_confidential: boolean;
  created_at: string;
  updated_at: string;
  versions: DocumentVersion[];
}

export interface UploadResponse {
  document_id: string;
  version_id: string;
  version_number: number;
  message: string;
}

export interface SignedUrlResponse {
  download_url: string;
  expires_in_seconds: number;
}

export interface ProcessResponse {
  version_id: string;
  parser_status: string;
  message: string;
}

export interface ParseJobResponse {
  id: string;
  version_id: string;
  status: string;
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExportRequest {
  version_id: string;
  draft: Record<string, unknown>;
  branding?: Record<string, unknown>;
}

export interface ExportResponse {
  job_id: string;
  version_id: string;
  status: string;
  message: string;
}

export interface ExportStatusResponse {
  id: string;
  version_id: string;
  status: string;
  docx_url: string | null;
  pdf_url: string | null;
  warning: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ACLOut {
  id: string;
  document_id: string;
  user_id: string | null;
  role: string | null;
  access_level: string;
  created_at: string;
}

export interface ACLGrantRequest {
  user_id?: string;
  role?: string;
  access_level: string;
}

export interface CreateDraftRequest {
  title: string;
  matter_id?: string;
}

export interface AutosaveRequest {
  content: unknown[];
}

export interface InsertCitationRequest {
  citation_block: Record<string, unknown>;
}

export interface DraftOut {
  id: string;
  law_firm_id: string;
  document_id: string | null;
  user_id: string;
  matter_id: string | null;
  title: string;
  content: unknown[] | null;
  status: string;
  last_autosaved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface EditorDocumentOut {
  id: string;
  law_firm_id: string;
  matter_id: string | null;
  owner_user_id: string;
  title: string;
  classification: string | null;
  is_confidential: boolean;
  created_at: string;
  updated_at: string;
}

export interface RetentionPolicyRequest {
  policy: string;
}

export interface RetentionStatusOut {
  document_id: string;
  retention_policy: string | null;
  deletion_date: string | null;
  deleted_at: string | null;
}

export interface ScheduleDeletionRequest {
  deletion_date: string;
}

export interface MessageOut {
  message: string;
}
