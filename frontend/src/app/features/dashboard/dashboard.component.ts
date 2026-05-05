import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { finalize, catchError, of } from 'rxjs';

import { ApiService } from '../../core/http/api.service';
import { DocumentOut } from '../../models/document.model';
import { Deadline } from '../../models/deadline.model';
import { NotificationOut } from '../../models/notification.model';
import { ReportOut } from '../../models/time-entry.model';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { SkeletonLoaderComponent } from '../../shared/components/skeleton-loader/skeleton-loader.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { DateEsPipe } from '../../shared/pipes/date-es.pipe';
import { NumberEsPipe } from '../../shared/pipes/number-es.pipe';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    StatusBadgeComponent,
    SkeletonLoaderComponent,
    EmptyStateComponent,
    DateEsPipe,
    NumberEsPipe,
    ScrollRevealDirective,
  ],
  template: `
    <div class="dashboard-container">
      <h1 class="dashboard-title">Inicio</h1>

      <div class="dashboard-grid">
        <!-- Documentos recientes -->
        <div class="dashboard-card" appScrollReveal>
          <p-card>
            <ng-template pTemplate="title">
              <div class="card-header">
                <h2 class="card-title">Documentos recientes</h2>
                <a routerLink="/documents" class="card-link">Ver todos</a>
              </div>
            </ng-template>

            @if (loading()['documents']) {
              <app-skeleton-loader variant="card" [count]="3"></app-skeleton-loader>
            } @else if (errors()['documents']) {
              <div class="card-error">
                <i class="pi pi-exclamation-circle"></i>
                <span>{{ errors()['documents'] }}</span>
                <button class="retry-btn" (click)="loadRecentDocuments()">Reintentar</button>
              </div>
            } @else if (recentDocuments().length === 0) {
              <app-empty-state
                icon="pi pi-folder-open"
                title="Sin documentos"
                message="Subí tu primer documento"
                actionLabel="Subir documento"
                (action)="navigateTo('/documents/upload')"
              ></app-empty-state>
            } @else {
              <ul class="item-list">
                @for (doc of recentDocuments(); track doc.id) {
                  <li class="list-item">
                    <a [routerLink]="['/documents', doc.id]" class="item-title">
                      {{ doc.title }}
                    </a>
                    <div class="item-meta">
                      <app-status-badge [status]="docStatus(doc)"></app-status-badge>
                      <span class="item-date">{{ doc.created_at | dateEs:'short' }}</span>
                    </div>
                  </li>
                }
              </ul>
            }
          </p-card>
        </div>

        <!-- Próximos vencimientos -->
        <div class="dashboard-card" appScrollReveal>
          <p-card>
            <ng-template pTemplate="title">
              <div class="card-header">
                <h2 class="card-title">Próximos vencimientos</h2>
                <a routerLink="/calendar" class="card-link">Ver calendario</a>
              </div>
            </ng-template>

            @if (loading()['deadlines']) {
              <app-skeleton-loader variant="card" [count]="3"></app-skeleton-loader>
            } @else if (errors()['deadlines']) {
              <div class="card-error">
                <i class="pi pi-exclamation-circle"></i>
                <span>{{ errors()['deadlines'] }}</span>
                <button class="retry-btn" (click)="loadUpcomingDeadlines()">Reintentar</button>
              </div>
            } @else if (upcomingDeadlines().length === 0) {
              <app-empty-state
                icon="pi pi-calendar"
                title="Sin vencimientos próximos"
                message="No tenés vencimientos en los próximos 7 días."
              ></app-empty-state>
            } @else {
              <ul class="item-list">
                @for (dl of upcomingDeadlines(); track dl.id) {
                  <li class="list-item">
                    <span class="item-title">{{ dl.title }}</span>
                    <div class="item-meta">
                      @if (dl.matter_id) {
                        <span class="item-matter">{{ dl.matter_id }}</span>
                      }
                      <span class="item-date">{{ dl.due_date | dateEs:'short' }}</span>
                      <app-status-badge [status]="deadlineStatus(dl.due_date)"></app-status-badge>
                    </div>
                  </li>
                }
              </ul>
            }
          </p-card>
        </div>

        <!-- Resumen de tiempo -->
        <div class="dashboard-card" appScrollReveal>
          <p-card>
            <ng-template pTemplate="title">
              <div class="card-header">
                <h2 class="card-title">Resumen de tiempo</h2>
                <a routerLink="/time/tracker" class="card-link">Registrar tiempo</a>
              </div>
            </ng-template>

            @if (loading()['time']) {
              <app-skeleton-loader variant="card" [count]="2"></app-skeleton-loader>
            } @else if (errors()['time']) {
              <div class="card-error">
                <i class="pi pi-exclamation-circle"></i>
                <span>{{ errors()['time'] }}</span>
                <button class="retry-btn" (click)="loadTimeSummary()">Reintentar</button>
              </div>
            } @else if (!timeSummary()) {
              <app-empty-state
                icon="pi pi-clock"
                title="Sin datos de tiempo"
                message="Empezá a registrar tu tiempo."
                actionLabel="Registrar tiempo"
                (action)="navigateTo('/time/tracker')"
              ></app-empty-state>
            } @else {
              <div class="time-stats">
                <div class="time-stat">
                  <span class="stat-label">Horas esta semana</span>
                  <span class="stat-value">{{ timeSummary()!.total_hours | numberEs:1 }}h</span>
                </div>
                <div class="time-stat">
                  <span class="stat-label">Horas facturables</span>
                  <span class="stat-value">{{ timeSummary()!.billable_hours | numberEs:1 }}h</span>
                </div>
              </div>
            }
          </p-card>
        </div>

        <!-- Notificaciones urgentes -->
        <div class="dashboard-card" appScrollReveal>
          <p-card>
            <ng-template pTemplate="title">
              <div class="card-header">
                <h2 class="card-title">Notificaciones urgentes</h2>
                <a routerLink="/notifications" class="card-link">Ver todas</a>
              </div>
            </ng-template>

            @if (loading()['notifications']) {
              <app-skeleton-loader variant="card" [count]="3"></app-skeleton-loader>
            } @else if (errors()['notifications']) {
              <div class="card-error">
                <i class="pi pi-exclamation-circle"></i>
                <span>{{ errors()['notifications'] }}</span>
                <button class="retry-btn" (click)="loadNotifications()">Reintentar</button>
              </div>
            } @else if (urgentNotifications().length === 0) {
              <app-empty-state
                icon="pi pi-bell"
                title="Sin notificaciones"
                message="No tenés notificaciones urgentes."
              ></app-empty-state>
            } @else {
              <ul class="item-list">
                @for (notif of urgentNotifications(); track notif.id) {
                  <li class="list-item notification-item">
                    <i class="pi" [class]="notificationIcon(notif)"></i>
                    <div class="notification-content">
                      <span class="item-title">{{ notif.title }}</span>
                      <span class="item-message">{{ notif.message }}</span>
                      <span class="item-date">{{ notif.created_at | dateEs:'short' }}</span>
                    </div>
                  </li>
                }
              </ul>
            }
          </p-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      padding: 1.5rem;
    }

    .dashboard-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0 0 1.5rem 0;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }

    @media (min-width: 768px) {
      .dashboard-grid {
        grid-template-columns: 1fr 1fr;
      }
    }

    .dashboard-card ::ng-deep .p-card {
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
      height: 100%;
    }

    .dashboard-card ::ng-deep .p-card-body {
      padding: 1.25rem;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }

    .card-title {
      font-family: var(--font-heading);
      font-size: 1.125rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
    }

    .card-link {
      color: var(--color-gold);
      font-size: 0.875rem;
      font-weight: 500;
      text-decoration: none;
      white-space: nowrap;
      transition: color var(--transition-fast);
    }

    .card-link:hover {
      color: var(--color-gold-dark);
      text-decoration: underline;
    }

    .item-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.875rem;
    }

    .list-item {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
      padding: 0.625rem 0;
      border-bottom: 1px solid var(--color-sepia-dark);
    }

    .list-item:last-child {
      border-bottom: none;
    }

    .item-title {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
      font-size: 0.9375rem;
      line-height: 1.4;
    }

    .item-title:hover {
      color: var(--color-gold);
      text-decoration: underline;
    }

    .item-meta {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .item-date {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
    }

    .item-matter {
      font-size: 0.8125rem;
      color: var(--color-review);
      font-weight: 500;
    }

    .notification-item {
      flex-direction: row;
      align-items: flex-start;
      gap: 0.75rem;
    }

    .notification-item > i {
      font-size: 1.125rem;
      color: var(--color-gold);
      margin-top: 0.125rem;
      flex-shrink: 0;
    }

    .notification-content {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      min-width: 0;
    }

    .item-message {
      font-size: 0.875rem;
      color: var(--color-text-secondary);
      line-height: 1.4;
    }

    .card-error {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.625rem;
      padding: 1.5rem;
      text-align: center;
      color: var(--color-critical);
    }

    .card-error i {
      font-size: 1.5rem;
    }

    .retry-btn {
      padding: 0.375rem 1rem;
      background-color: transparent;
      color: var(--color-gold);
      border: 1px solid var(--color-gold);
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: all var(--transition-fast);
    }

    .retry-btn:hover {
      background-color: var(--color-gold);
      color: #ffffff;
    }

    .time-stats {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      padding: 0.5rem 0;
    }

    .time-stat {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.875rem 1rem;
      background-color: var(--color-sepia-light);
      border-radius: 6px;
      border: 1px solid var(--color-sepia-dark);
    }

    .stat-label {
      font-size: 0.9375rem;
      color: var(--color-text-secondary);
      font-weight: 500;
    }

    .stat-value {
      font-family: var(--font-heading);
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--color-text);
    }
  `],
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly recentDocuments = signal<DocumentOut[]>([]);
  readonly upcomingDeadlines = signal<Deadline[]>([]);
  readonly timeSummary = signal<ReportOut | null>(null);
  readonly urgentNotifications = signal<NotificationOut[]>([]);

  readonly loading = signal<Record<string, boolean>>({
    documents: false,
    deadlines: false,
    time: false,
    notifications: false,
  });

  readonly errors = signal<Record<string, string | null>>({
    documents: null,
    deadlines: null,
    time: null,
    notifications: null,
  });

  ngOnInit(): void {
    this.loadRecentDocuments();
    this.loadUpcomingDeadlines();
    this.loadTimeSummary();
    this.loadNotifications();
  }

  loadRecentDocuments(): void {
    this.setLoading('documents', true);
    this.setError('documents', null);

    this.api.get<DocumentOut[]>('documents/', { limit: 5 }).pipe(
      finalize(() => this.setLoading('documents', false)),
      catchError((err) => {
        this.setError('documents', err.error?.detail ?? 'No se pudieron cargar los documentos.');
        return of([]);
      })
    ).subscribe((docs) => {
      this.recentDocuments.set(docs);
    });
  }

  loadUpcomingDeadlines(): void {
    this.setLoading('deadlines', true);
    this.setError('deadlines', null);

    this.api.get<Deadline[]>('deadlines/upcoming', { days: 7 }).pipe(
      finalize(() => this.setLoading('deadlines', false)),
      catchError((err) => {
        this.setError('deadlines', err.error?.detail ?? 'No se pudieron cargar los vencimientos.');
        return of([]);
      })
    ).subscribe((deadlines) => {
      this.upcomingDeadlines.set(deadlines);
    });
  }

  loadTimeSummary(): void {
    this.setLoading('time', true);
    this.setError('time', null);

    this.api.get<ReportOut>('time/report').pipe(
      finalize(() => this.setLoading('time', false)),
      catchError((err) => {
        this.setError('time', err.error?.detail ?? 'No se pudieron cargar las horas.');
        return of(null);
      })
    ).subscribe((report) => {
      this.timeSummary.set(report);
    });
  }

  loadNotifications(): void {
    this.setLoading('notifications', true);
    this.setError('notifications', null);

    this.api.get<NotificationOut[]>('notifications/urgent', { limit: 5 }).pipe(
      finalize(() => this.setLoading('notifications', false)),
      catchError((err) => {
        this.setError('notifications', err.error?.detail ?? 'No se pudieron cargar las notificaciones.');
        return of([]);
      })
    ).subscribe((notifications) => {
      this.urgentNotifications.set(notifications);
    });
  }

  docStatus(doc: DocumentOut): string {
    const version = doc.versions?.[doc.versions.length - 1];
    if (!version) return 'pending';
    const status = version.parser_status;
    if (status === 'ready') return 'ready';
    if (status === 'processing') return 'review';
    if (status === 'failed') return 'critical';
    return 'pending';
  }

  deadlineStatus(dueDate: string): string {
    const due = new Date(dueDate);
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    if (due < now) return 'critical';
    return 'pending';
  }

  notificationIcon(notif: NotificationOut): string {
    const p = notif.priority?.toLowerCase();
    if (p === 'critical' || p === 'high') return 'pi pi-exclamation-circle';
    if (notif.deadline_id) return 'pi pi-calendar';
    return 'pi pi-bell';
  }

  navigateTo(path: string): void {
    // Navigation is handled by routerLink in the template;
    // this method is a fallback for programmatic navigation if needed.
  }

  private setLoading(key: string, value: boolean): void {
    this.loading.update((state) => ({ ...state, [key]: value }));
  }

  private setError(key: string, value: string | null): void {
    this.errors.update((state) => ({ ...state, [key]: value }));
  }
}
