# Specification: Legal AI Platform Foundation MVP

**Change Reference**: `legal-ai-platform-foundation`  
**Proposal Topic**: `sdd/legal-ai-platform-foundation/proposal`  
**Spec Version**: 1.0.0  
**Status**: Draft for Implementation  

---

## 1. Executive Summary

This specification defines the MVP foundation for a legal AI platform built on FastAPI that enables law firms to draft, review, and version legal documents with AI assistance while maintaining strict anti-hallucination safeguards, security, confidentiality, auditability, and role-based access control.

The platform addresses critical constraints unique to legal practice:
- **Zero tolerance for fabricated jurisprudence** - AI must cite verifiable sources
- **Multi-tenant isolation** - Law firms cannot access each other's data
- **Complete auditability** - Every action must be traceable for legal compliance
- **Human-in-the-loop** - Lawyers must approve AI-suggested actions

---

## 2. System Overview

### 2.1 Architecture Layers

1. **Ingestion Layer**: Email sync, document upload, parsing (PDF/DOCX/TXT), OCR
2. **Storage/Search Layer**: PostgreSQL (relational), Object Storage (blobs), pgvector (semantic search)
3. **LLM/Prompting Layer**: Multi-model routing, legal guardrails, citation validation
4. **Frontend/Delivery Layer**: Web app, action inbox, editor, export engine, OAuth

### 2.2 Bounded Contexts

- `identity_access`: Law firms, users, memberships, roles, OAuth, sessions
- `crm_matters`: Clients, matters, participants, deadlines
- `documents`: Documents, versions, ACLs, annotations, export
- `knowledge_ai`: Chunks, embeddings, citations, policy checks, LLM router
- `communications`: Email connections, messages, attachments, inferences
- `workflows`: Pending actions, approvals, reminders, calendar sync
- `audit`: Audit events, lineage, retention policies

---

## 3. Requirements

### 3.1 Document Drafting, Review, and Versioning

#### REQ-DOC-001: Document Upload
**ID**: REQ-DOC-001  
**Priority**: MUST  
**Description**: The system SHALL accept document uploads in PDF, DOCX, and TXT formats via web interface.  
**Acceptance Criteria**:
- User can upload file up to 50MB
- System extracts metadata (filename, size, MIME type, upload timestamp)
- System assigns unique document ID
- System returns 202 Accepted with job ID for async processing
- Upload requires authentication and valid matter association (or draft status)

#### REQ-DOC-002: Document Versioning
**ID**: REQ-DOC-002  
**Priority**: MUST  
**Description**: The system SHALL maintain complete version history for each document with immutable audit trail.  
**Acceptance Criteria**:
- Each edit creates new `DocumentVersion` with incrementing version number
- Version stores: storage key, SHA-256 hash, MIME type, created_at, created_by
- Previous versions remain accessible to users with document access
- System prevents deletion of versions (soft delete only via retention policy)

#### REQ-DOC-003: Document Parsing and Text Extraction
**ID**: REQ-DOC-003  
**Priority**: MUST  
**Description**: The system SHALL extract text content from uploaded documents asynchronously.  
**Acceptance Criteria**:
- PDF: Extract text via PDF parser; if scanned, trigger OCR job
- DOCX: Extract text preserving paragraph structure
- TXT: Direct ingestion
- System updates `DocumentVersion.parser_status` to `pending` → `processing` → `completed` | `failed`
- Extracted text stored separately from blob, linked to version

#### REQ-DOC-004: Web-Based Document Editor
**ID**: REQ-DOC-004  
**Priority**: MUST  
**Description**: The system SHALL provide a web-based editor for creating and editing legal documents using structured JSON blocks.  
**Acceptance Criteria**:
- Editor renders document as editable blocks (paragraph, heading, list, citation)
- System auto-saves drafts every 30 seconds to `EditorDraft` table
- Draft linked to `DocumentVersion` or creates new version on save
- Editor supports citation insertion with validation against retrieved sources

#### REQ-DOC-005: Document Export
**ID**: REQ-DOC-005  
**Priority**: MUST  
**Description**: The system SHALL export documents to DOCX and PDF formats.  
**Acceptance Criteria**:
- Export generates file from latest `DocumentVersion` or specific version
- DOCX: Preserves formatting, styles, embedded metadata
- PDF: Generates print-ready PDF with optional digital signature (phase 2)
- Export job returns download URL with short-lived signed token (5 min expiry)

---

### 3.2 Client and Matter Organization

#### REQ-CRM-001: Client Management
**ID**: REQ-CRM-001  
**Priority**: MUST  
**Description**: The system SHALL allow law firms to create and manage client records.  
**Acceptance Criteria**:
- Client record contains: name, type (individual/organization), contact info, tax ID (optional), notes
- Client scoped to `law_firm_id` - not visible to other firms
- Soft delete with retention policy
- Audit log entry for create/update/delete

#### REQ-CRM-002: Matter Management
**ID**: REQ-CRM-002  
**Priority**: MUST  
**Description**: The system SHALL allow creation of matters (cases) linked to clients.  
**Acceptance Criteria**:
- Matter contains: case number, title, description, client_id, status (active/closed), opening date, closing date (optional)
- Matter scoped to `law_firm_id`
- Documents, deadlines, communications linkable to matter
- Matter closure requires confirmation and optional summary

#### REQ-CRM-003: Matter Participants
**ID**: REQ-CRM-003  
**Priority**: SHOULD  
**Description**: The system SHALL track participants (lawyers, paralegals, external parties) associated with a matter.  
**Acceptance Criteria**:
- Participant record: user_id (internal) or contact info (external), role (lead lawyer, supporting, opposing counsel, etc.)
- Internal participants must have membership in law firm
- External participants stored as contact records

---

### 3.3 Time Tracking and Justification

#### REQ-TIME-001: Time Entry
**ID**: REQ-TIME-001  
**Priority**: MUST  
**Description**: The system SHALL allow lawyers to record time entries linked to matters.  
**Acceptance Criteria**:
- Time entry contains: matter_id, user_id, date, duration (minutes), activity type, description, billable flag
- Timer feature: start/stop tracking with auto-calculation of duration
- Manual entry allowed with edit history
- Entries scoped to user's law firm via matter association

#### REQ-TIME-002: Time Entry Justification
**ID**: REQ-TIME-002  
**Priority**: MUST  
**Description**: The system SHALL generate time justification reports by aggregating entries and linking to work products.  
**Acceptance Criteria**:
- Report includes: date range, total hours, breakdown by matter, activity type
- Each entry shows description and linked documents/actions
- Export to PDF/DOCX for client billing
- Filter by matter, date range, billable status

#### REQ-TIME-003: AI-Assisted Time Entry (MVP Limited)
**ID**: REQ-TIME-003  
**Priority**: SHOULD  
**Description**: The system SHALL suggest time entries based on email activity and document edits (MVP: manual trigger).  
**Acceptance Criteria**:
- User can request "suggest time entries from last 24h"
- System analyzes user's sent emails, edited documents, calendar events
- Suggestion includes: matter (inferred), duration estimate, activity description
- User must approve before entry created
- Rejected suggestions logged for model improvement

---

### 3.4 Deadline Management

#### REQ-DEADLINE-001: Deadline Creation
**ID**: REQ-DEADLINE-001  
**Priority**: MUST  
**Description**: The system SHALL allow creation of deadlines linked to matters with configurable reminders.  
**Acceptance Criteria**:
- Deadline contains: title, description, matter_id, due_date, due_time (optional), priority (high/medium/low), status (pending/completed/missed)
- Manual creation via UI
- AI-suggested deadlines from email/document analysis (requires approval)
- Reminder configuration: 1 day before, 1 hour before, custom

#### REQ-DEADLINE-002: Deadline Notifications
**ID**: REQ-DEADLINE-002  
**Priority**: MUST  
**Description**: The system SHALL notify responsible users of upcoming and overdue deadlines.  
**Acceptance Criteria**:
- Notification via in-app inbox and email
- Scheduled job runs every 15 minutes to check deadlines
- Notification includes: deadline title, matter, time remaining, link to matter
- Overdue deadlines highlighted in red with escalation

#### REQ-DEADLINE-003: Calendar Integration
**ID**: REQ-DEADLINE-003  
**Priority**: SHOULD  
**Description**: The system SHALL sync deadlines to Google Calendar and Microsoft Calendar.  
**Acceptance Criteria**:
- User connects calendar via OAuth
- Deadline creates calendar event with reminder settings
- Two-way sync: event reschedule updates deadline (with user confirmation)
- Calendar event includes matter link in description

---

### 3.5 AI Trust and Anti-Hallucination Safeguards

#### REQ-AI-001: Citation Requirement
**ID**: REQ-AI-001  
**Priority**: MUST  
**Description**: The system SHALL require all AI-generated legal assertions to include citations to retrieved sources.  
**Acceptance Criteria**:
- LLM response parser extracts citation markers
- Each citation must reference a `document_id` or `chunk_id` from retrieval
- Response without citations flagged as `unverified`
- UI displays `unverified` badge and warning for responses without citations

#### REQ-AI-002: Citation Validation
**ID**: REQ-AI-002  
**Priority**: MUST  
**Description**: The system SHALL validate that citations actually support the claims made in the AI response.  
**Acceptance Criteria**:
- Validator checks that cited chunk contains keywords/entities from claim
- Cross-Reference Embedding similarity > 0.75 between claim and cited snippet
- If validation fails, response marked `needs_review`
- Lawyer can override and mark as `verified` with comment

#### REQ-AI-003: Hallucination Detection Fallback
**ID**: REQ-AI-003  
**Priority**: MUST  
**Description**: The system SHALL respond with explicit fallback when confidence is low or sources insufficient.  
**Acceptance Criteria**:
- If retrieval returns no relevant documents, respond: "No verifiable sources found. External verification required."
- If citation validation fails, respond: "Claims could not be verified against provided sources."
- Fallback response includes suggested search terms or source types

#### REQ-AI-004: LLM Router
**ID**: REQ-AI-004  
**Priority**: MUST  
**Description**: The system SHALL route requests to appropriate LLM based on task complexity and risk.  
**Acceptance Criteria**:
- Classifier analyzes: token count, domain keywords (legal terms), required precision
- Simple tasks (summarization, formatting) → economical model
- Complex tasks (legal analysis, drafting) → premium model (GPT-4, Claude Opus)
- High-risk tasks (court filings, compliance) → premium model + mandatory human review
- Router decision logged with confidence score

#### REQ-AI-005: Source Isolation
**ID**: REQ-AI-005  
**Priority**: MUST  
**Description**: The system SHALL only retrieve sources from the same law firm tenant during RAG.  
**Acceptance Criteria**:
- Retrieval query includes `law_firm_id` filter at database level
- pgvector index scoped by tenant
- Cross-tenant retrieval attempt logged as security event
- System returns empty results rather than leaking data

---

### 3.6 Security, Confidentiality, Auditability, and RBAC

#### REQ-SEC-001: Multi-Tenant Isolation
**ID**: REQ-SEC-001  
**Priority**: MUST  
**Description**: The system SHALL enforce strict isolation between law firm tenants at the data layer.  
**Acceptance Criteria**:
- Every row in multi-tenant tables includes `law_firm_id`
- All queries include `WHERE law_firm_id = :current_firm_id`
- Application-layer enforcement + database constraints
- Attempted cross-tenant access returns 403 Forbidden
- Security event logged with full context

#### REQ-SEC-002: Role-Based Access Control
**ID**: REQ-SEC-002  
**Priority**: MUST  
**Description**: The system SHALL implement RBAC with roles: owner, lawyer, paralegal, assistant.  
**Acceptance Criteria**:
- `owner`: Full access to firm data, can manage members, billing, settings
- `lawyer`: Full access to assigned matters, can create documents, view time entries
- `paralegal`: Limited to assigned matters, can draft documents, track time
- `assistant`: Read-only on assigned matters, can view calendar, deadlines
- Role checked on every API request via middleware

#### REQ-SEC-003: Document ACLs
**ID**: REQ-SEC-003  
**Priority**: MUST  
**Description**: The system SHALL enforce document-level access control lists in addition to RBAC.  
**Acceptance Criteria**:
- Document has `owner_user_id` and optional `matter_id`
- `DocumentAcl` table grants access to specific users or roles
- Matter association grants access to all matter participants
- Confidential documents require explicit grant even for firm members
- ACL check on every document read/write/delete

#### REQ-SEC-004: Audit Logging
**ID**: REQ-SEC-004  
**Priority**: MUST  
**Description**: The system SHALL log all user actions, AI operations, and system events to immutable audit log.  
**Acceptance Criteria**:
- AuditEvent contains: timestamp, actor_user_id, law_firm_id, resource_type, resource_id, action, input_hash, output_hash, metadata
- AI events include: model used, prompt_hash, response_hash, citations, validation_result
- Logs written synchronously before response returned
- Audit log immutable (append-only, no delete/update)
- Retention policy configurable per firm (default: 7 years)

#### REQ-SEC-005: OAuth 2.0 Authentication
**ID**: REQ-SEC-005  
**Priority**: MUST  
**Description**: The system SHALL authenticate users via OAuth 2.0 with Google and Microsoft.  
**Acceptance Criteria**:
- User clicks "Sign in with Google/Microsoft"
- System redirects to provider with PKCE flow
- Provider returns authorization code
- System exchanges code for tokens, stores refresh token encrypted
- User profile created/updated from provider claims
- Session token issued (JWT or server-side session)

#### REQ-SEC-006: Token Encryption
**ID**: REQ-SEC-006  
**Priority**: MUST  
**Description**: The system SHALL encrypt OAuth refresh tokens and API keys at rest.  
**Acceptance Criteria**:
- Encryption via KMS (cloud provider managed keys)
- Tokens stored as ciphertext in database
- Decryption only in memory during token refresh
- Encryption key access logged

#### REQ-SEC-007: Confidentiality Marking
**ID**: REQ-SEC-007  
**Priority**: MUST  
**Description**: The system SHALL allow marking documents as confidential, applying stricter access controls.  
**Acceptance Criteria**:
- Confidential flag on Document
- Confidential documents excluded from shared indices (RAG, search)
- Access requires explicit grant via `DocumentAcl`
- UI displays confidentiality warning
- Download/view logged with higher severity

#### REQ-SEC-008: Data Retention and Deletion
**ID**: REQ-SEC-008  
**Priority**: MUST  
**Description**: The system SHALL support configurable retention policies and verifiable deletion.  
**Acceptance Criteria**:
- Retention policy per firm: 1 year, 3 years, 7 years, indefinite
- Expired documents soft-deleted (marked, excluded from queries)
- Hard deletion via scheduled job after grace period
- Deletion logged with hash of deleted data for verification
- "Right to be forgotten" request triggers deletion workflow

---

## 4. Data Model (Core Entities)

### 4.1 Identity and Access

```
LawFirm
  - id: UUID (PK)
  - name: string
  - created_at: timestamp
  - settings: JSONB

User
  - id: UUID (PK)
  - email: string (unique)
  - display_name: string
  - created_at: timestamp

Membership
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - user_id: UUID (FK)
  - role: enum(owner, lawyer, paralegal, assistant)
  - joined_at: timestamp

DocumentAcl
  - id: UUID (PK)
  - document_id: UUID (FK)
  - user_id: UUID (FK, nullable)
  - role_id: enum (nullable)
  - permission: enum(read, write, admin)
  - granted_by: UUID (FK User)
  - granted_at: timestamp
```

### 4.2 CRM

```
Client
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - name: string
  - type: enum(individual, organization)
  - email: string
  - phone: string
  - tax_id: string (nullable)
  - created_at: timestamp

Matter
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - client_id: UUID (FK)
  - case_number: string
  - title: string
  - description: text
  - status: enum(active, closed)
  - opened_at: date
  - closed_at: date (nullable)
  - created_by: UUID (FK User)

MatterParticipant
  - id: UUID (PK)
  - matter_id: UUID (FK)
  - user_id: UUID (FK, nullable)
  - external_contact_id: UUID (FK, nullable)
  - role: string
```

### 4.3 Documents

```
Document
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - matter_id: UUID (FK, nullable)
  - owner_user_id: UUID (FK)
  - title: string
  - classification: string (nullable)
  - is_confidential: boolean
  - created_at: timestamp
  - updated_at: timestamp

DocumentVersion
  - id: UUID (PK)
  - document_id: UUID (FK)
  - version_number: integer
  - storage_key: string
  - sha256_hash: string
  - mime_type: string
  - size_bytes: integer
  - parser_status: enum(pending, processing, completed, failed)
  - created_at: timestamp
  - created_by: UUID (FK)

EditorDraft
  - id: UUID (PK)
  - document_version_id: UUID (FK)
  - content_json: JSONB
  - last_saved_at: timestamp
  - user_id: UUID (FK)
```

### 4.4 Knowledge and AI

```
DocumentChunk
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - document_version_id: UUID (FK)
  - chunk_index: integer
  - content: text
  - embedding: vector (pgvector)
  - metadata: JSONB

InferenceLog
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - user_id: UUID (FK)
  - model_name: string
  - task_type: string
  - prompt_hash: string
  - response_hash: string
  - citations: JSONB
  - validation_status: enum(valid, invalid, needs_review, unverified)
  - created_at: timestamp
```

### 4.5 Workflows and Actions

```
PendingAction
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - matter_id: UUID (FK, nullable)
  - user_id: UUID (FK)
  - action_type: enum(meeting, reminder, appointment, deadline, call, email)
  - title: string
  - description: text
  - urgency_score: integer (0-100)
  - status: enum(pending, approved, rejected)
  - source_email_id: UUID (FK, nullable)
  - proposed_at: timestamp
  - approved_at: timestamp (nullable)
  - approved_by: UUID (FK, nullable)

Deadline
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - matter_id: UUID (FK)
  - created_by: UUID (FK)
  - assigned_to: UUID (FK, nullable)
  - title: string
  - description: text
  - due_date: date
  - due_time: time (nullable)
  - priority: enum(high, medium, low)
  - status: enum(pending, completed, missed)
  - reminder_config: JSONB
  - created_at: timestamp

TimeEntry
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - matter_id: UUID (FK)
  - user_id: UUID (FK)
  - date: date
  - duration_minutes: integer
  - activity_type: string
  - description: text
  - is_billable: boolean
  - created_at: timestamp
  - updated_at: timestamp
```

### 4.6 Audit

```
AuditEvent
  - id: UUID (PK)
  - law_firm_id: UUID (FK)
  - actor_user_id: UUID (FK)
  - resource_type: string
  - resource_id: UUID
  - action: string
  - input_hash: string (nullable)
  - output_hash: string (nullable)
  - metadata: JSONB
  - timestamp: timestamp
```

---

## 5. API Surface (Key Endpoints)

### 5.1 Documents

```
POST   /api/v1/documents/upload          → 202 { document_id, job_id }
GET    /api/v1/documents/:id             → 200 { Document, versions: [] }
GET    /api/v1/documents/:id/versions/:versionId/download → 200 { signed_url }
POST   /api/v1/documents/:id/versions    → 201 { DocumentVersion }
GET    /api/v1/documents/:id/export?format=docx|pdf → 202 { job_id }
```

### 5.2 Search

```
POST   /api/v1/search/query              → 200 { hits: [], citations: [] }
GET    /api/v1/search/similar/:id        → 200 { hits: [] }
```

### 5.3 AI

```
POST   /api/v1/ai/answer                 → 200 { answer, citations, model, confidence }
POST   /api/v1/ai/classify               → 200 { task_type, complexity, recommended_model }
```

### 5.4 Actions

```
GET    /api/v1/actions                   → 200 { PendingAction[] }
POST   /api/v1/actions/:id/approve       → 200 { status: "approved", side_effects: [] }
POST   /api/v1/actions/:id/reject        → 200 { status: "rejected" }
```

### 5.5 Time Tracking

```
POST   /api/v1/time-entries              → 201 { TimeEntry }
GET    /api/v1/time-entries              → 200 { TimeEntry[] }
POST   /api/v1/time-entries/suggest      → 200 { suggestions: [] }
GET    /api/v1/time-entries/report       → 200 { report_data }
```

### 5.6 Deadlines

```
POST   /api/v1/deadlines                 → 201 { Deadline }
GET    /api/v1/deadlines                 → 200 { Deadline[] }
PATCH  /api/v1/deadlines/:id             → 200 { Deadline }
```

### 5.7 Audit

```
GET    /api/v1/audit/events              → 200 { AuditEvent[] }
GET    /api/v1/audit/events/:resourceType/:resourceId → 200 { AuditEvent[] }
```

---

## 6. Validation Rules

### 6.1 Document Validation
- Document title: 1-200 characters, no special chars `<>"/\|?*`
- File size: max 50MB
- MIME type: must match allowed list (application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain)

### 6.2 Citation Validation
- Citation must reference existing document_id or chunk_id
- Citation must pass similarity threshold (>0.75)
- Citation must be from same law_firm_id

### 6.3 Deadline Validation
- Due date cannot be in the past (unless creating overdue reminder)
- Priority must be high/medium/low
- Assigned user must be member of law firm

### 6.4 Time Entry Validation
- Duration: 1-1440 minutes (24h max per entry)
- Date cannot be in the future
- Matter must exist and be active

---

## 7. Error Handling

### 7.1 Standard Error Response
```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document with ID 'uuid' not found",
    "details": {
      "document_id": "uuid"
    }
  }
}
```

### 7.2 Error Codes
- `UNAUTHORIZED`: Invalid or missing authentication
- `FORBIDDEN`: User lacks permission for resource
- `NOT_FOUND`: Resource does not exist
- `VALIDATION_ERROR`: Input validation failed
- `TENANT_ISOLATION_VIOLATION`: Cross-tenant access attempt
- `CITATION_VALIDATION_FAILED`: AI citation could not be verified
- `QUOTA_EXCEEDED`: Rate limit or storage quota exceeded

---

## 8. Performance Requirements

- Document upload to processing start: < 2 seconds
- Search query response (95th percentile): < 500ms
- AI response time (simple tasks): < 5 seconds
- AI response time (complex tasks): < 30 seconds
- Concurrent users supported: 100 per firm
- Document retrieval: < 1 second for files < 10MB

---

## 9. Compliance and Legal Requirements

### 9.1 Data Residency
- All data stored in region specified by law firm (e.g., EU, US-ARIZONA)
- Cross-region replication disabled by default

### 9.2 Attorney-Client Privilege
- System must not use client data for model training
- Explicit opt-in required for any analytics beyond operational needs

### 9.3 Record Retention
- Default retention: 7 years (adjustable per jurisdiction)
- Legal hold: prevent deletion during active litigation

---

## 10. Open Questions and Assumptions

### 10.1 Assumptions
- Law firms have at least basic technical literacy
- Firms have existing OAuth-enabled email (Google Workspace or Microsoft 365)
- Legal guardrails are more important than automation speed

### 10.2 Open Questions
1. **Digital Signature**: Which e-signature provider for PDF signing? (DocuSign, Adobe Sign, or country-specific?)
2. **OCR Engine**: Tesseract (open source) vs cloud OCR (AWS Textract, Google Vision)?
3. **Queue Backend**: Celery + Redis vs RQ vs Dramatiq?
4. **Jurisdiction-Specific Rules**: How to handle varying legal requirements by country/state?

---

## 11. Out of Scope (MVP)

- Court filing automation (phase 2)
- Client portal for secure communication (phase 2)
- Billing and invoicing (phase 2)
- Advanced analytics dashboard (phase 2)
- Mobile app (phase 2)
- Multi-language support beyond English/Spanish (phase 2)

---

## 12. Success Metrics

- **Accuracy**: >95% citation validation pass rate
- **Trust**: <1% hallucination rate on legal assertions
- **Performance**: 99% of searches return in <1s
- **Adoption**: 80% of lawyers use AI suggestions weekly
- **Security**: Zero cross-tenant data leaks

---

## 13. Related Artifacts

- Proposal: `sdd/legal-ai-platform-foundation/proposal`
- Design: `docs/design/legal-platform-foundation.md`
- Existing Spec: `docs/spec/legal-platform-foundation.md` (to be updated)

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-03 | SDD Spec Phase | Initial specification for MVP foundation |
