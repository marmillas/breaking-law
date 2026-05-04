# Data Model

## Entities
- **User**: ID, email, OAuth provider, config, subscription.
- **Document**: ID, owner (User), metadata, storage link, embeddings.
- **WorkflowConfig**: Email source, LLM selection.
- **InferenceLog**: AI executions, guardrail checks, results.
- **PendingAction**: ID, type (meeting|reminder|appointment), urgency_score, status (pending|approved|rejected), owner (User), source_email.
