import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { finalize, catchError, of, timeout } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CalendarModule } from 'primeng/calendar';
import { DropdownModule } from 'primeng/dropdown';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { TimeService } from '../time.service';
import { ClientService } from '../../clients/client.service';
import { TimeEntry, ReportOut } from '../../../models/time-entry.model';
import { ClientOut } from '../../../models/client.model';
import { PaginatedResponse } from '../../../models/pagination.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';

@Component({
  selector: 'app-time-history',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    ButtonModule,
    CalendarModule,
    DropdownModule,
    TableModule,
    TagModule,
    StatusBadgeComponent,
    EmptyStateComponent,
    SkeletonLoaderComponent,
    DateEsPipe,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Historial de tiempo</h1>
        <button
          pButton
          label="Registrar tiempo"
          icon="pi pi-play"
          class="p-button-warning"
          routerLink="/time/tracker"
        ></button>
      </div>

      <!-- Summary Stats -->
      @if (!loading()) {
        <div class="stats-bar">
          <div class="stat-item">
            <span class="stat-label">Esta semana</span>
            <span class="stat-value">{{ formatHours(summary()?.total_hours) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">Este mes</span>
            <span class="stat-value">{{ formatHours(monthlySummary()?.total_hours) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-label">Facturables</span>
            <span class="stat-value gold">{{ formatHours(summary()?.billable_hours) }}</span>
          </div>
        </div>
      }

      <!-- Filters -->
      <div class="toolbar">
        <form [formGroup]="filterForm" class="toolbar-filters">
          <span class="p-input-icon-left date-field">
            <i class="pi pi-calendar"></i>
            <p-calendar
              formControlName="dateFrom"
              placeholder="Desde"
              [showIcon]="true"
              dateFormat="dd/mm/yy"
              styleClass="w-full"
            ></p-calendar>
          </span>
          <span class="p-input-icon-left date-field">
            <i class="pi pi-calendar"></i>
            <p-calendar
              formControlName="dateTo"
              placeholder="Hasta"
              [showIcon]="true"
              dateFormat="dd/mm/yy"
              styleClass="w-full"
            ></p-calendar>
          </span>
          <p-dropdown
            [options]="clients()"
            formControlName="client"
            optionLabel="name"
            placeholder="Cliente"
            [showClear]="true"
            styleClass="w-full"
          ></p-dropdown>
          <button
            pButton
            type="button"
            icon="pi pi-filter-slash"
            class="p-button-text"
            (click)="clearFilters()"
            title="Limpiar filtros"
          ></button>
        </form>
      </div>

      @if (loading()) {
        <app-skeleton-loader variant="table" [count]="5"></app-skeleton-loader>
      } @else if (error()) {
        <app-empty-state
          icon="pi pi-exclamation-circle"
          title="Error al cargar"
          [message]="error()!"
          actionLabel="Reintentar"
          (action)="loadEntries()"
        ></app-empty-state>
      } @else if (entries().length === 0) {
        <app-empty-state
          icon="pi pi-clock"
          title="Sin registros"
          message="Empezá a registrar tu tiempo"
          actionLabel="Registrar tiempo"
          (action)="goToTracker()"
        ></app-empty-state>
      } @else {
        <div class="table-wrapper">
          <p-table
            [value]="entries()"
            [paginator]="true"
            [rows]="pageSize"
            [totalRecords]="totalRecords()"
            styleClass="p-datatable-striped"
            [scrollable]="true"
            scrollHeight="flex"
          >
          <ng-template pTemplate="header">
            <tr>
              <th>Fecha</th>
              <th>Cliente</th>
              <th>Expediente</th>
              <th>Descripción</th>
              <th>Duración</th>
              <th>Estado</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-entry>
            <tr>
              <td>{{ entry.started_at | dateEs:'short' }}</td>
              <td>
                @if (entry.client_id) {
                  <a [routerLink]="['/clients', entry.client_id]" class="entity-link" (click)="$event.stopPropagation()">
                    {{ clientName(entry.client_id) }}
                  </a>
                } @else {
                  <span class="text-muted">—</span>
                }
              </td>
              <td>
                @if (entry.matter_id) {
                  <a [routerLink]="['/matters', entry.matter_id]" class="entity-link" (click)="$event.stopPropagation()">
                    Ver expediente
                  </a>
                } @else {
                  <span class="text-muted">—</span>
                }
              </td>
              <td>{{ entry.description ?? '—' }}</td>
              <td>{{ formatDuration(entry.duration_minutes) }}</td>
              <td>
                <app-status-badge [status]="statusFor(entry.status)"></app-status-badge>
              </td>
            </tr>
          </ng-template>
          </p-table>
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
    }

    .table-wrapper {
      overflow-x: auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .page-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
    }

    .stats-bar {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      padding: 1rem 1.5rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .stat-label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.025em;
      color: var(--color-text-secondary);
    }

    .stat-value {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--color-text);
    }

    .stat-value.gold {
      color: var(--color-gold);
    }

    .stat-divider {
      width: 1px;
      height: 36px;
      background-color: var(--color-border);
    }

    .toolbar {
      margin-bottom: 1rem;
    }

    .toolbar-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }

    .date-field {
      flex: 1;
      min-width: 180px;
    }

    .entity-link {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
    }

    .entity-link:hover {
      color: var(--color-gold);
      text-decoration: underline;
    }

    .text-muted {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    :host ::ng-deep .p-button-warning {
      background-color: var(--color-gold);
      border-color: var(--color-gold);
      color: var(--color-text);
    }

    :host ::ng-deep .p-button-warning:hover {
      background-color: var(--color-gold-dark);
      border-color: var(--color-gold-dark);
    }

    :host ::ng-deep .p-calendar {
      width: 100%;
    }

    :host ::ng-deep .p-dropdown {
      width: 100%;
      min-width: 200px;
    }
  `],
})
export class TimeHistoryComponent implements OnInit {
  private readonly timeService = inject(TimeService);
  private readonly clientService = inject(ClientService);
  private readonly fb = inject(FormBuilder);

  readonly entries = signal<TimeEntry[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly summary = signal<ReportOut | null>(null);
  readonly monthlySummary = signal<ReportOut | null>(null);
  readonly clients = signal<ClientOut[]>([]);
  readonly totalRecords = signal(0);
  readonly page = signal(0);

  readonly pageSize = 20;

  filterForm: FormGroup = this.fb.group({
    dateFrom: [null],
    dateTo: [null],
    client: [null],
  });

  ngOnInit(): void {
    this.loadClients();
    this.loadEntries();
    this.loadSummary();
    this.loadMonthlySummary();

    this.filterForm.valueChanges.subscribe(() => {
      this.page.set(0);
      this.loadEntries();
    });
  }

  loadClients(): void {
    this.clientService.list({ limit: 1000 }).subscribe({
      next: (res: PaginatedResponse<ClientOut>) => {
        this.clients.set(res.items);
      },
    });
  }

  loadEntries(): void {
    this.loading.set(true);
    this.error.set(null);

    const values = this.filterForm.value;
    const params: Record<string, unknown> = { limit: 1000 };

    if (values.dateFrom) {
      params['start_date'] = new Date(values.dateFrom).toISOString();
    }
    if (values.dateTo) {
      params['end_date'] = new Date(values.dateTo).toISOString();
    }
    if (values.client?.id) {
      params['client_id'] = values.client.id;
    }

    this.timeService
      .getEntries(params)
      .pipe(
        timeout(10000),
        catchError((err) => {
          if (err.name === 'TimeoutError') {
            this.error.set('Esto está tardando más de lo normal. Verificá tu conexión e intentá de nuevo.');
          } else {
            this.error.set('No se pudieron cargar los registros de tiempo.');
          }
          return of({ items: [], total: 0, limit: 0, offset: 0 } as PaginatedResponse<TimeEntry>);
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe({
        next: (res: PaginatedResponse<TimeEntry>) => {
          this.entries.set(res.items);
          this.totalRecords.set(res.items.length);
        },
      });
  }

  loadSummary(): void {
    this.timeService.getReport('week').subscribe({
      next: (report) => this.summary.set(report),
      error: () => this.summary.set(null),
    });
  }

  loadMonthlySummary(): void {
    this.timeService.getReport('month').subscribe({
      next: (report) => this.monthlySummary.set(report),
      error: () => this.monthlySummary.set(null),
    });
  }

  clearFilters(): void {
    this.filterForm.reset({ dateFrom: null, dateTo: null, client: null });
    this.page.set(0);
    this.loadEntries();
  }

  goToTracker(): void {
    // Navigation handled by routerLink in template
  }

  clientName(clientId: string): string {
    const c = this.clients().find((x) => x.id === clientId);
    return c?.name ?? '—';
  }

  formatDuration(minutes: number | null): string {
    if (minutes === null || minutes === undefined) return '—';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  formatHours(value: number | undefined | null): string {
    if (value === undefined || value === null) return '—';
    return `${value.toFixed(1)}h`;
  }

  statusFor(status: string): string {
    if (status === 'approved') return 'ready';
    if (status === 'submitted') return 'review';
    if (status === 'running') return 'pending';
    return 'pending';
  }
}
