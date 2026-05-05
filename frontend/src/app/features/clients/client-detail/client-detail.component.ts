import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TabViewModule } from 'primeng/tabview';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { finalize, catchError, of } from 'rxjs';

import { ClientService } from '../client.service';
import { MatterService } from '../../matters/matter.service';
import { ApiService } from '../../../core/http/api.service';
import { ClientOut } from '../../../models/client.model';
import { MatterOut } from '../../../models/matter.model';
import { DocumentOut } from '../../../models/document.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-client-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    TabViewModule,
    TableModule,
    ButtonModule,
    StatusBadgeComponent,
    DateEsPipe,
    SkeletonLoaderComponent,
    EmptyStateComponent,
    ConfirmDialogComponent,
  ],
  template: `
    <div class="page-container">
      <a routerLink="/clients" class="back-link">← Volver a clientes</a>

      @if (loading()['client']) {
        <app-skeleton-loader variant="card" [count]="2"></app-skeleton-loader>
      } @else if (notFound()) {
        <app-empty-state
          icon="pi pi-user"
          title="Cliente no encontrado"
          message="El cliente solicitado no existe o fue eliminado."
          actionLabel="Volver a clientes"
          (action)="goBack()"
        ></app-empty-state>
      } @else {
        <div class="detail-layout">
          <!-- Client Info Card -->
          <div class="info-card">
            <div class="info-header">
              <h1 class="info-title">{{ client()?.name }}</h1>
              <div class="actions-bar">
                <button
                  pButton
                  type="button"
                  label="Editar"
                  icon="pi pi-pencil"
                  class="p-button-outlined"
                ></button>
                <button
                  pButton
                  type="button"
                  label="Eliminar"
                  icon="pi pi-trash"
                  class="p-button-danger p-button-outlined"
                  (click)="showDeleteDialog.set(true)"
                ></button>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">Email</span>
                <span class="info-value">{{ client()?.email }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Teléfono</span>
                <span class="info-value">
                  @if (client()?.phone) {
                    {{ client()?.phone }}
                  } @else {
                    <span class="text-muted">—</span>
                  }
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">Fecha de alta</span>
                <span class="info-value">{{ client()?.created_at | dateEs:'short' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Última actualización</span>
                <span class="info-value">{{ client()?.updated_at | dateEs:'short' }}</span>
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <p-tabView>
            <!-- Expedientes -->
            <p-tabPanel header="Expedientes">
              @if (loading()['matters']) {
                <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
              } @else if (matters().length === 0) {
                <app-empty-state
                  icon="pi pi-folder"
                  title="Sin expedientes"
                  message="Este cliente no tiene expedientes registrados."
                ></app-empty-state>
              } @else {
                <p-table [value]="matters()" styleClass="p-datatable-striped" [scrollable]="true" scrollHeight="flex">
                  <ng-template pTemplate="header">
                    <tr>
                      <th>Referencia</th>
                      <th>Estado</th>
                      <th>Fecha</th>
                    </tr>
                  </ng-template>
                  <ng-template pTemplate="body" let-matter>
                    <tr [routerLink]="['/matters', matter.id]" class="cursor-pointer hover-row">
                      <td>
                        <a [routerLink]="['/matters', matter.id]" class="matter-link" (click)="$event.stopPropagation()">
                          {{ matter.title }}
                        </a>
                      </td>
                      <td>
                        <app-status-badge [status]="matter.status"></app-status-badge>
                      </td>
                      <td>{{ matter.created_at | dateEs:'short' }}</td>
                    </tr>
                  </ng-template>
                </p-table>
              }
            </p-tabPanel>

            <!-- Documentos -->
            <p-tabPanel header="Documentos">
              @if (loading()['documents']) {
                <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
              } @else if (documents().length === 0) {
                <app-empty-state
                  icon="pi pi-file"
                  title="Sin documentos"
                  message="No hay documentos asociados a este cliente."
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
            </p-tabPanel>

            <!-- Historial de comunicación -->
            <p-tabPanel header="Historial de comunicación">
              <app-empty-state
                icon="pi pi-comments"
                title="Próximamente"
                message="El historial de comunicación estará disponible en una próxima versión."
              ></app-empty-state>
            </p-tabPanel>
          </p-tabView>
        </div>
      }
    </div>

    <app-confirm-dialog
      [visible]="showDeleteDialog()"
      title="Eliminar cliente"
      [message]="deleteMessage()"
      confirmLabel="Eliminar"
      severity="danger"
      (confirm)="onDeleteConfirm()"
      (cancel)="showDeleteDialog.set(false)"
    ></app-confirm-dialog>
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

    .info-card {
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

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
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

    .actions-bar {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .text-muted {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    .matter-link,
    .doc-link {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
    }

    .matter-link:hover,
    .doc-link:hover {
      color: var(--color-gold);
      text-decoration: underline;
    }

    .hover-row:hover {
      background-color: var(--surface-hover);
    }

    :host ::ng-deep .p-datatable .p-datatable-tbody > tr {
      cursor: pointer;
    }

    :host ::ng-deep .p-tabview .p-tabview-panels {
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-top: none;
      border-radius: 0 0 8px 8px;
      padding: 1.25rem;
    }

    :host ::ng-deep .p-tabview .p-tabview-nav {
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-bottom: none;
      border-radius: 8px 8px 0 0;
    }

    :host ::ng-deep .p-tabview .p-tabview-nav li .p-tabview-nav-link {
      font-family: var(--font-heading);
      font-weight: 600;
      color: var(--color-text-secondary);
    }

    :host ::ng-deep .p-tabview .p-tabview-nav li.p-highlight .p-tabview-nav-link {
      color: var(--color-gold);
    }
  `],
})
export class ClientDetailComponent implements OnInit {
  private readonly clientService = inject(ClientService);
  private readonly matterService = inject(MatterService);
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly client = signal<ClientOut | null>(null);
  readonly matters = signal<MatterOut[]>([]);
  readonly documents = signal<DocumentOut[]>([]);
  readonly notFound = signal(false);
  readonly showDeleteDialog = signal(false);

  readonly deleteMessage = computed(() => {
    const name = this.client()?.name ?? '';
    return `¿Está seguro de que desea eliminar a "${name}"?`;
  });

  readonly loading = signal<Record<string, boolean>>({
    client: false,
    matters: false,
    documents: false,
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.notFound.set(true);
      return;
    }
    this.loadClient(id);
    this.loadMatters(id);
    this.loadDocuments(id);
  }

  loadClient(id: string): void {
    this.setLoading('client', true);
    this.clientService.get(id).subscribe({
      next: (c) => {
        this.client.set(c);
        this.setLoading('client', false);
      },
      error: (err) => {
        this.setLoading('client', false);
        if (err.status === 404) {
          this.notFound.set(true);
        }
      },
    });
  }

  loadMatters(clientId: string): void {
    this.setLoading('matters', true);
    this.matterService
      .listByClient(clientId)
      .pipe(
        finalize(() => this.setLoading('matters', false)),
        catchError(() => of({ items: [], total: 0, limit: 0, offset: 0 }))
      )
      .subscribe((res) => {
        this.matters.set(res.items);
      });
  }

  loadDocuments(clientId: string): void {
    this.setLoading('documents', true);
    this.api
      .get<DocumentOut[]>('/documents/', { client_id: clientId, limit: 50 })
      .pipe(
        finalize(() => this.setLoading('documents', false)),
        catchError(() => of([]))
      )
      .subscribe((docs) => {
        this.documents.set(docs);
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

  onDeleteConfirm(): void {
    const id = this.client()?.id;
    if (!id) return;

    this.showDeleteDialog.set(false);
    this.clientService.delete(id).subscribe({
      next: () => {
        this.router.navigate(['/clients']);
      },
      error: () => {
        // Error is handled by the error interceptor
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/clients']);
  }

  private setLoading(key: string, value: boolean): void {
    this.loading.update((state) => ({ ...state, [key]: value }));
  }
}
