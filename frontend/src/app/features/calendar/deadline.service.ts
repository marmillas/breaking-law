import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../core/http/api.service';
import { Deadline } from '../../models/deadline.model';

@Injectable({ providedIn: 'root' })
export class DeadlineService {
  constructor(private readonly api: ApiService) {}

  getDeadlines(params?: {
    start_date?: string;
    end_date?: string;
    matter_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Observable<Deadline[]> {
    return this.api.get<Deadline[]>('/deadlines', params);
  }

  getUpcoming(days: number = 7): Observable<Deadline[]> {
    return this.api.get<Deadline[]>('/deadlines/upcoming', { days });
  }

  getOverdue(): Observable<Deadline[]> {
    return this.api.get<Deadline[]>('/deadlines/overdue');
  }

  acknowledge(id: string): Observable<Deadline> {
    return this.api.post<Deadline>(`/deadlines/${id}/acknowledge`, {});
  }

  complete(id: string): Observable<Deadline> {
    return this.api.post<Deadline>(`/deadlines/${id}/complete`, {});
  }
}
