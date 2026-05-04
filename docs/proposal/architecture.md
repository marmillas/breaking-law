# Architecture

4 layers:

1. **Ingestion Layer**
   - Sync configured emails.
   - Upload & parse docs.
2. **Storage/Search Layer**
   - Relational DB: users, profiles, metadata.
   - Blob Storage: physical files.
   - Vector DB: search/RAG.
3. **LLM/Prompting Layer**
   - Multi-model gateway.
   - Guardrails: ! Strict legal output validation.
   - Inference Engine: Extract urgency & actions ← emails.
4. **Frontend/Delivery Layer**
   - Web App: docs & config.
   - Action Inbox: Pending tasks UI.
   - In-Browser Editor.
   - Export Engine.
   - OAuth.
