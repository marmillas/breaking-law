# Design: legal-platform-foundation

## Enfoque técnico

Backend monolito modular FastAPI + `PostgreSQL` + object storage + vector index. HTTP síncrono para CRUD/autorización. Jobs asíncronos para ingestión documental, RAG, correo, exportación. Diseño sigue requisitos multi-tenant, trazabilidad legal, aprobación humana & búsqueda híbrida.

## Contextos acotados

- `identity_access`: `LawFirm`, `User`, `Membership`, `Role`, OAuth, sesiones.
- `crm_matters`: `Client`, `Matter`, participantes, plazos.
- `documents`: `Document`, `DocumentVersion`, `DocumentAcl`, anotaciones, export.
- `knowledge_ai`: chunks, embeddings, citations, policy checks, LLM router.
- `communications`: conexiones email, `EmailMessage`, adjuntos, inferencias.
- `workflows`: `PendingAction`, approvals, reminders, calendar sync.
- `audit`: `AuditEvent`, lineage, retention.

V1: ∀ fila tenant-scoped → filtro por `law_firm_id` antes consulta.
V2: ∀ salida IA legal → citas verificables | fallback explícito.
V3: acción externa → requiere `PendingAction.status=approved`.

## Estructura FastAPI

```text
src/breaking-law/
  main.py
  api/routers/{auth,users,documents,search,emails,actions,editor,audit}.py
  domain/{identity_access,crm_matters,documents,knowledge_ai,communications,workflows,audit}/
  services/{storage,rag,llm,email,export,calendar,observability}.py
  infra/{db,object_store,queue,vector_store,secrets}.py
  schemas/{request,response,event}.py
```

Router fino → service → domain/infra. Patrones actuales `routers/*.py` preservan entrada FastAPI; cambio mueve lógica fuera handlers.

## Decisiones clave

| Decisión | Opciones | Elección | Rationale |
|---|---|---|---|
| Persistencia core | Postgres | `PostgreSQL` + RLS lógica app | joins fuertes, auditoría, filtros tenant |
| Binarios | DB blobs \| object storage | object storage + metadata DB | costo menor, URLs firmadas, versionado |
| Búsqueda vectorial | pgvector \| engine externo | `pgvector` inicial | menos moving parts; misma frontera tenant |
| Jobs | sync \| cola | cola asíncrona | OCR, embeddings, export, email polling largos |
| Editor | HTML libre \| JSON estructurado | JSON blocks + HTML render | diff, validación, export más estable |
| Guardrails | prompt-only \| policy engine | policy engine + citations | prompt solo ≠ suficiente |

## Flujo datos

```text
upload/email → object storage
             → metadata DB
             → parse/OCR job
             → chunk + embed
             → BM25 tsvector + pgvector
query/editor/email intent
             → hybrid retrieval
             → LLM router
             → policy/citation validator
             → response | PendingAction | export
             → AuditEvent
```

## Almacenamiento documental

- `Document` guarda `law_firm_id`, `matter_id`, `owner_user_id`, clasificación, confidencialidad.
- `DocumentVersion` guarda `storage_key`, `sha256`, MIME, parser status.
- `DocumentAcl` guarda grants por rol, usuario, matter.
- Descarga/vista previa vía URL firmada corta + verificación ACL servidor.
- Confidencial → excluido de índices compartidos; solo índices tenant-local.

## RAG + búsqueda híbrida

- Ingestión: parse PDF/DOCX/TXT, OCR opcional, chunking por encabezados/párrafos, embeddings por versión.
- Índices: `tsvector` BM25 para exactitud legal + `pgvector` para semántica.
- Rank final: `0.45*bm25 + 0.45*vector + 0.10*recency/acl/matter`.
- Citas guardan `document_version_id`, offsets, snippet, score.

api: POST /documents/upload → 202 {document_id:string,job_id:string}
api: POST /search/query → 200 {hits:[{document_id:string,snippet:string,score:number}],citations:[...]}

## Router LLM + anti-alucinación

- Clasificador estima tipo tarea, páginas, tokens, riesgo regulatorio.
- Router: simple → modelo económico; revisión/redacción extensa → premium.
- Respuesta legal ! incluir citas recuperadas. Validador bloquea claims sin evidencia, fuentes contradictorias, citas fuera tenant.
- Fallback: `"verificación externa necesaria"` + fuentes sugeridas.

api: POST /ai/answer → 200 {answer:string,citations:[...],model:string,confidence:number}

## AuthN/AuthZ, perfil, email

- OAuth 2.0/OIDC Google & Microsoft. `User` global; `Membership` por bufete con roles `owner|lawyer|paralegal|assistant`.
- AuthZ por RBAC + ACL documental + scope por matter.
- `UserPreference`: idioma, zona horaria, proveedor email preferido, defaults LLM, notificaciones.
- `EmailConnection`: provider, mailbox scope, refresh token ref, sync cursor, consent state.

## Ingesta email + inbox IA

- Poll/webhook proveedor → `EmailMessage` + adjuntos.
- Pipeline infiere matter, cliente, urgencia, intención, fechas, acciones propuestas.
- `PendingAction` score = urgencia legal + deadline proximity + client priority + confidence.
- Aprobar → ejecuta integración calendario/reminder/export. Rechazar → feedback router.

api: POST /actions/{id}/approve → 200 {status:"approved",side_effects:[...]}
api: POST /actions/{id}/reject → 200 {status:"rejected"}

## Editor, export, integraciones

- Editor web guarda `EditorDraft` JSON blocks ligado a `DocumentVersion`.
- Export service renderiza DOCX/PDF desde plantilla estable; PDF firmado ? fase 2.
- Integraciones: Google Calendar/Microsoft Graph para reuniones, recordatorios, disponibilidad.

## Auditoría & operación

- `AuditEvent`: actor, tenant, recurso, input hash, output hash, model, citations, decision, timestamp.
- Secrets ∈ secret manager; tokens OAuth cifrados por KMS.
- Observabilidad: request IDs, job IDs, métricas por modelo/costo/latencia, alertas por fallos ingestión.
- Cost controls: presupuestos por tenant, cache embeddings, límite premium por policy.
- Privacidad: minimización PII, redacción en logs, retention por tenant, borrado verificable.

## Cambios archivo

| Archivo | Acción | Descripción |
|---|---|---|
| `docs/design/legal-platform-foundation.md` | Create | diseño técnico base |
| `src/breaking-law/main.py` | Modify | registrar routers modulares |
| `src/breaking-law/api/routers/*.py` | Create | superficies HTTP por contexto |
| `src/breaking-law/domain/**` | Create | entidades, policies, services |
| `src/breaking-law/infra/**` | Create | DB, storage, queue, vector |

## Testing, rollout, dudas

- Unit: scoring, ACL, router LLM, citation validator.
- Integration: OAuth callback, upload→index, hybrid search, approve action→calendar.
- E2E: lawyer login, upload, ask AI, approve reminder, export.
- Rollout: feature flags por contexto; ingestión email & premium routing detrás flags.
- Dudas: proveedor cola (`Celery`/`RQ`), motor OCR, firma PDF regulatoria por país.
