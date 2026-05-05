import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from '../../core/http/api.service';
import { MatterOut } from '../../models/matter.model';
import { PaginatedResponse } from '../../models/pagination.model';

@Injectable({ providedIn: 'root' })
export class MatterService {
  constructor(private readonly api: ApiService) {}

  get(id: string): Observable<MatterOut> {
    return this.api.get<MatterOut>(`/matters/${id}`);
  }

  listByClient(clientId: string): Observable<PaginatedResponse<MatterOut>> {
    return this.api.get<MatterOut[]>('/matters/', { client_id: clientId }).pipe(
      map((items) => ({
        items,
        total: items.length,
        limit: items.length,
        offset: 0,
      }))
    );
  }

  create(data: Partial<MatterOut>): Observable<MatterOut> {
    return this.api.post<MatterOut>('/matters/', data);
  }

  update(id: string, data: Partial<MatterOut>): Observable<MatterOut> {
    return this.api.put<MatterOut>(`/matters/${id}`, data);
  }
}
