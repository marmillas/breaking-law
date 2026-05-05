import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from '../../core/http/api.service';
import { ClientOut } from '../../models/client.model';
import { PaginatedResponse } from '../../models/pagination.model';

@Injectable({ providedIn: 'root' })
export class ClientService {
  constructor(private readonly api: ApiService) {}

  list(params?: { search?: string; limit?: number; offset?: number }): Observable<PaginatedResponse<ClientOut>> {
    return this.api.get<ClientOut[]>('/clients/', params).pipe(
      map((items) => ({
        items,
        total: items.length,
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0,
      }))
    );
  }

  get(id: string): Observable<ClientOut> {
    return this.api.get<ClientOut>(`/clients/${id}`);
  }

  create(data: Partial<ClientOut>): Observable<ClientOut> {
    return this.api.post<ClientOut>('/clients/', data);
  }

  update(id: string, data: Partial<ClientOut>): Observable<ClientOut> {
    return this.api.put<ClientOut>(`/clients/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete<void>(`/clients/${id}`);
  }
}
