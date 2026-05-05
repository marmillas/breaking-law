"""
Re-export all models for backward compatibility.

Existing code can continue to use::

    from breaking_law.infra.models import Document, User, Base, ...
"""

from breaking_law.infra.models.base import Base, _utc_now

from breaking_law.infra.models.documents import (
    AccessLevel,
    Document,
    DocumentACL,
    DocumentChunk,
    DocumentExportJob,
    DocumentParseJob,
    DocumentVersion,
    EditorDraft,
    EditorDraftStatus,
    ParserStatus,
)

from breaking_law.infra.models.identity import (
    EmailConnection,
    LawFirm,
    RefreshToken,
    User,
)

from breaking_law.infra.models.crm import (
    Client,
    DeadlinePriority,
    Matter,
    Notification,
)

from breaking_law.infra.models.timekeeping import (
    Deadline,
    DeadlineStatus,
    TimeEntry,
    TimeEntryStatus,
)

from breaking_law.infra.models.audit import AuditEvent
