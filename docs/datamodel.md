# Data Models

## Core Entities

### Document
- id: string
- title: string
- content: string
- document_type: string
- created_at: datetime
- updated_at: datetime
- owner_id: string

### Client
- id: string
- name: string
- email: string
- phone: string
- created_at: datetime
- updated_at: datetime

### Matter
- id: string
- title: string
- description: string
- client_id: string
- status: string
- created_at: datetime
- updated_at: datetime

## Relationships

- Client 1 → N Matter
- Matter 1 → N Document
- Client 1 → N Document (through Matter)