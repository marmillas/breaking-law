import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { signal } from '@angular/core';
import { ApiService } from '../../core/http/api.service';
import { TimeEntry, ReportOut } from '../../models/time-entry.model';
import { PaginatedResponse } from '../../models/pagination.model';

@Injectable({ providedIn: 'root' })
export class TimeService {
  constructor(private readonly api: ApiService) {}

  // Timer state (shared across app via singleton service)
  readonly runningEntry = signal<RunningTimer | null>(null);
  readonly elapsed = signal<string>('00:00:00');
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  // API methods
  startTimer(clientId: string, matterId: string, description: string): Observable<TimeEntry> {
    return this.api.post<TimeEntry>('/time/start', { client_id: clientId, matter_id: matterId, description });
  }

  stopTimer(entryId: string): Observable<TimeEntry> {
    return this.api.post<TimeEntry>(`/time/${entryId}/stop`, {});
  }

  getEntries(params?: {
    matter_id?: string;
    client_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Observable<PaginatedResponse<TimeEntry>> {
    return this.api.get<TimeEntry[]>('/time/entries', params).pipe(
      map((items) => ({
        items,
        total: items.length,
        limit: params?.limit ?? 100,
        offset: params?.offset ?? 0,
      }))
    );
  }

  getReport(period: 'week' | 'month' = 'week'): Observable<ReportOut> {
    const now = new Date();
    let startDate: string;
    let endDate: string;

    if (period === 'week') {
      const dayOfWeek = now.getDay();
      const diffToMonday = (dayOfWeek + 6) % 7;
      const monday = new Date(now);
      monday.setDate(now.getDate() - diffToMonday);
      monday.setHours(0, 0, 0, 0);
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      sunday.setHours(23, 59, 59, 999);
      startDate = monday.toISOString();
      endDate = sunday.toISOString();
    } else {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      startDate = firstDay.toISOString();
      endDate = lastDay.toISOString();
    }

    return this.api.get<ReportOut>('/time/report', { start_date: startDate, end_date: endDate });
  }

  // Timer management
  startLocalTimer(entry: RunningTimer): void {
    this.runningEntry.set(entry);
    const startTime = Date.now();
    this.elapsed.set('00:00:00');
    this.timerInterval = setInterval(() => {
      const diff = Date.now() - startTime;
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      this.elapsed.set(
        `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
      );
    }, 1000);
  }

  stopLocalTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    this.runningEntry.set(null);
    this.elapsed.set('00:00:00');
  }
}

export interface RunningTimer {
  entryId: string;
  clientName: string;
  matterReference: string;
  description: string;
}

export interface TimeReport {
  total_hours: number;
  billable_hours: number;
  entries_count: number;
}
