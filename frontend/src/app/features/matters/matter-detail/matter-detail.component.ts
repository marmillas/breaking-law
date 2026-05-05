import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { finalize, catchError, of } from 'rxjs';

import { MatterService } from '../matter.service';
import { ApiService } from '../../../core/http/api.service';
import { MatterOut } from '../../../models/matter.model';
import { DocumentOut } from '../../../models/document.model';
import { TimeEntry } from '../../../models/time-entry.model';
import { Deadline } from '../../../models/deadline.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ScrollRevealDirective } from '../../../shared/directives/scroll-reveal.directive';

@Component({
  selector: 'app-matter-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    TableModule,
    TagModule,
    ButtonModule,
    StatusBadgeComponent,
    DateEsPipe,
    SkeletonLoaderComponent,
    EmptyStateComponent,
    ScrollRevealDirective,
  ],
  template: `
    <div class="page-container">
      @if (matter()) {
        <a [routerLink]="['/clients', matter()!.client_id]" class="back-link">
          ← Volver al cliente
        </a>
      }

      @if (loading()['matter']) {
        <app-skeleton-loader variant="card" [count]="2"></app-skeleton-loader>
      } @else if (notFound()) {
        <app-empty-state
          icon="pi pi-folder"
          title="Expediente no encontrado"
          message="El expediente solicitado no existe o fue eliminado."
          actionLabel="Volver a clientes"
          (action)="goToClients()"
        ></app-empty-state>
      } @else {
        <div class="detail-layout">
          <!-- Matter Info Card -->
          <div class="info-card">
            <div class="info-header">
              <h1 class="info-title">{{ matter()?.title }}</h1>
              <div class="info-badges">
                <app-status-badge [status]="matter()?.status ?? 'pending'"></app-status-badge>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Cliente</span>
                <a [routerLink]="['/clients', matter()?.client_id]" class="info-link">
                  Ver cliente
                </a>
              </div>
              <div class="info-item">
                <span class="info-label">Estado</span>
                <span class="info-value">{{ matter()?.status }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Fecha de apertura</span>
                <span class="info-value">{{ matter()?.created_at | dateEs:'short' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Última actualización</span>
                <span class="info-value">{{ matter()?.updated_at | dateEs:'short' }}</span>
              </div>
            </div>

            @if (matter()?.description) {
              <div class="description">
                <span class="info-label">Descripción</span>
                <p class="description-text">{{ matter()?.description }}</p>
              </div>
            }
          </div>

          <!-- Documentos vinculados -->
          <div class="section-card" appScrollReveal>
            <div class="section-header">
              <h2 class="section-title">Documentos vinculados</h2>
            </div>
            @if (loading()['documents']) {
              <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
            } @else if (documents().length === 0) {
              <app-empty-state
                icon="pi pi-file"
                title="Sin documentos"
                message="No hay documentos vinculados a este expediente."
              ></app-empty-state>
            } @else {
              <p-table [value]="documents()" styleClass="p-datatable-striped" [scrollable]="true" scrollHeight="flex">
                <ng-template pTemplate="header">
                  <tr>
                    <th>Título</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                  </tr>
                </ng-template>
                <ng-template pTemplate="body" let-doc>
                  <tr [routerLink]="['/documents', doc.id]" class="cursor-pointer hover-row">
                    <td>
                      <a [routerLink]="['/documents', doc.id]" class="doc-link" (click)="$event.stopPropagation()">
                        {{ doc.title }}
                      </a>
                    </td>
                    <td>
                      @if (doc.classification) {
                        <span class="text-muted">{{ doc.classification }}</span>
                      } @else {
                        <span class="text-muted">—</span>
                      }
                    </td>
                    <td>
                      <app-status-badge [status]="docStatus(doc)"></app-status-badge>
                    </td>
                    <td>{{ doc.created_at | dateEs:'short' }}</td>
                  </tr>
                </ng-template>
              </p-table>
            }
          </div>

          <!-- Registros de tiempo -->
          <div class="section-card" appScrollReveal>
            <div class="section-header">
              <h2 class="section-title">Registros de tiempo</h2>
            </div>
            @if (loading()['timeEntries']) {
              <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
            } @else if (timeEntries().length === 0) {
              <app-empty-state
                icon="pi pi-clock"
                title="Sin registros de tiempo"
                message="No hay registros de tiempo para este expediente."
              ></app-empty-state>
            } @else {
              <p-table [value]="timeEntries()" styleClass="p-datatable-striped" [scrollable]="true" scrollHeight="flex">
                <ng-template pTemplate="header">
                  <tr>
                    <th>Fecha</th>
                    <th>Descripción</th>
                    <th>Duración</th>
                    <th>Facturable</th>
                  </tr>
                </ng-template>
                <ng-template pTemplate="body" let-entry>
                  <tr>
                    <td>{{ entry.started_at | dateEs:'short' }}</td>
                    <td>{{ entry.description ?? '—' }}</td>
                    <td>{{ formatDuration(entry.duration_minutes) }}</td>
                    <td>
                      @if (entry.billable) {
                        <span class="badge-ready">Sí</span>
                      } @else {
                        <span class="text-muted">No</span>
                      }
                    </td>
                  </tr>
                </ng-template>
              </p-table>
            }
          </div>

          <!-- Resumen de facturación -->
          <div class="section-card" appScrollReveal>
            <div class="section-header">
              <h2 class="section-title">Resumen de facturación</h2>
            </div>
            <app-empty-state
              icon="pi pi-chart-bar"
              title="Próximamente"
              message="El resumen de facturación estará disponible en una próxima versión."
            ></app-empty-state>
          </div>

          <!-- Vencimientos -->
          <div class="section-card" appScrollReveal>
            <div class="section-header">
              <h2 class="section-title">Vencimientos</h2>
            </div>
            @if (loading()['deadlines']) {
              <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
            } @else if (deadlines().length === 0) {
              <app-empty-state
                icon="pi pi-calendar"
                title="Sin vencimientos"
                message="No hay vencimientos registrados para este expediente."
              ></app-empty-state>
            } @else {
              <p-table [value]="deadlines()" styleClass="p-datatable-striped" [scrollable]="true" scrollHeight="flex">
                <ng-template pTemplate="header">
                  <tr>
                    <th>Título</th>
                    <th>Prioridad</th>
                    <th>Estado</th>
                    <th>Fecha límite</th>
                  </tr>
                </ng-template>
                <ng-template pTemplate="body" let-dl>
                  <tr>
                    <td>{{ dl.title }}</td>
                    <td>
                      <p-tag [value]="dl.priority" severity="secondary"></p-tag>
                    </td>
                    <td>
                      <app-status-badge [status]="dl.status"></app-status-badge>
                    </td>
                    <td>{{ dl.due_date | dateEs:'short' }}</td>
                  </tr>
                </ng-template>
              </p-table>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
    }

    .back-link {
      display: inline-block;
      margin-bottom: 1.25rem;
      color: var(--color-gold);
      text-decoration: none;
      font-weight: 500;
      font-size: 0.9375rem;
    }

    .back-link:hover {
      text-decoration: underline;
    }

    .detail-layout {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      max-width: 960px;
    }

    .info-card,
    .section-card {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
    }

    .info-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .info-title {
      font-family: var(--font-heading);
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
    }

    .info-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .info-label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.025em;
      color: var(--color-text-secondary);
    }

    .info-value {
      font-size: 0.9375rem;
      color: var(--color-text);
    }

    .info-link {
      color: var(--color-review);
      text-decoration: none;
      font-size: 0.9375rem;
    }

    .info-link:hover {
      text-decoration: underline;
    }

    .description {
      margin-top: 0.5rem;
    }

    .description-text {
      font-size: 0.9375rem;
      color: var(--color-text);
      line-height: 1.5;
      margin: 0.25rem 0 0;
    }

    .section-header {
      margin-bottom: 1rem;
    }

    .section-title {
      font-family: var(--font-heading);
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }

    .doc-link {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
    }

    .doc-link:hover {
      color: var(--color-gold);
      text-decoration: underline;
    }

    .text-muted {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    .hover-row:hover {
      background-color: var(--surface-hover);
    }

    :host ::ng-deep .p-datatable .p-datatable-tbody > tr {
      cursor: pointer;
    }

    .badge-ready {
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.625rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      background-color: rgba(45, 106, 79, 0.12);
      color: var(--color-ready);
    }
  `],
})
export class MatterDetailComponent implements OnInit {
  private readonly matterService = inject(MatterService);
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly matter = signal<MatterOut | null>(null);
  readonly documents = signal<DocumentOut[]>([]);
  readonly timeEntries = signal<TimeEntry[]>([]);
  readonly deadlines = signal<Deadline[]>([]);
  readonly notFound = signal(false);

  readonly loading = signal<Record<string, boolean>>({
    matter: false,
    documents: false,
    timeEntries: false,
    deadlines: false,
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.notFound.set(true);
      return;
    }
    this.loadMatter(id);
    this.loadDocuments(id);
    this.loadTimeEntries(id);
    this.loadDeadlines(id);
  }

  loadMatter(id: string): void {
    this.setLoading('matter', true);
    this.matterService.get(id).subscribe({
      next: (m) => {
        this.matter.set(m);
        this.setLoading('matter', false);
      },
      error: (err) => {
        this.setLoading('matter', false);
        if (err.status === 404) {
          this.notFound.set(true);
        }
      },
    });
  }

  loadDocuments(matterId: string): void {
    this.setLoading('documents', true);
    this.api
      .get<DocumentOut[]>('/documents/', { matter_id: matterId, limit: 50 })
      .pipe(
        finalize(() => this.setLoading('documents', false)),
        catchError(() => of([]))
      )
      .subscribe((docs) => {
        this.documents.set(docs);
      });
  }

  loadTimeEntries(matterId: string): void {
    this.setLoading('timeEntries', true);
    this.api
      .get<TimeEntry[]>('/time/entries', { matter_id: matterId, limit: 100 })
      .pipe(
        finalize(() => this.setLoading('timeEntries', false)),
        catchError(() => of([]))
      )
      .subscribe((entries) => {
        this.timeEntries.set(entries);
      });
  }

  loadDeadlines(matterId: string): void {
    this.setLoading('deadlines', true);
    this.api
      .get<Deadline[]>('/deadlines', { matter_id: matterId, limit: 100 })
      .pipe(
        finalize(() => this.setLoading('deadlines', false)),
        catchError(() => of([]))
      )
      .subscribe((items) => {
        this.deadlines.set(items);
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

  formatDuration(minutes: number | null): string {
    if (minutes === null || minutes === undefined) return '—';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  goToClients(): void {
    this.router.navigate(['/clients']);
  }

  private setLoading(key: string, value: boolean): void {
    this.loading.update((state) => ({ ...state, [key]: value }));
  }
}
