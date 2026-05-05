import { Injectable } from '@angular/core';
import { HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, filter, map } from 'rxjs';
import { ApiService } from '../../core/http/api.service';
import {
  DocumentOut,
  DocumentVersion,
  UploadResponse,
  DraftOut,
} from '../../models/document.model';
import { PaginatedResponse } from '../../models/pagination.model';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  constructor(private readonly api: ApiService) {}

  list(params?: {
    limit?: number;
    offset?: number;
    matter_id?: string;
    status?: string;
    document_type?: string;
    client_id?: string;
    date_from?: string;
    date_to?: string;
  }): Observable<PaginatedResponse<DocumentOut>> {
    return this.api.get<PaginatedResponse<DocumentOut>>('/documents/', params);
  }

  get(id: string): Observable<DocumentOut> {
    return this.api.get<DocumentOut>(`/documents/${id}`);
  }

  upload(
    file: File,
    metadata: {
      title: string;
      matter_id?: string;
      classification?: string;
      is_confidential?: boolean;
    }
  ): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', metadata.title);
    if (metadata.matter_id) formData.append('matter_id', metadata.matter_id);
    if (metadata.classification) formData.append('classification', metadata.classification);
    if (metadata.is_confidential !== undefined) formData.append('is_confidential', String(metadata.is_confidential));
    return this.api.upload<UploadResponse>('/documents/upload', formData);
  }

  delete(id: string): Observable<void> {
    return this.api.delete<void>(`/documents/${id}`);
  }

  search(query: string): Observable<unknown> {
    return this.api.post('/search', { query });
  }

  getVersions(id: string): Observable<DocumentVersion[]> {
    return this.api.get<DocumentVersion[]>(`/documents/${id}/versions`);
  }

  download(id: string): Observable<Blob> {
    return this.api.download(`/documents/${id}/download`);
  }

  getDrafts(): Observable<DraftOut[]> {
    return this.api.get<DraftOut[]>('/editor/drafts');
  }

  getDraft(id: string): Observable<DraftOut> {
    return this.api.get<DraftOut>(`/editor/drafts/${id}`);
  }

  saveDraft(id: string, content: unknown): Observable<DraftOut> {
    return this.api.put<DraftOut>(`/editor/drafts/${id}`, { content });
  }

  queryRag(query: string): Observable<unknown> {
    return this.api.post('/rag/query', { query });
  }
}

export function isUploadProgressEvent(event: HttpEvent<unknown>): event is HttpEvent<UploadResponse> & { type: HttpEventType.UploadProgress; loaded: number; total?: number } {
  return event.type === HttpEventType.UploadProgress;
}

export function isUploadResponseEvent(event: HttpEvent<unknown>): event is HttpEvent<UploadResponse> & { type: HttpEventType.Response; body: UploadResponse } {
  return event.type === HttpEventType.Response;
}
