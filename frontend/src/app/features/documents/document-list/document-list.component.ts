import { Component, OnInit, signal, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, switchMap, catchError, of, finalize } from 'rxjs';
import { TableModule } from 'primeng/table';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { CalendarModule } from 'primeng/calendar';

import { DocumentService } from '../document.service';
import { DocumentOut } from '../../../models/document.model';
import { PaginatedResponse } from '../../../models/pagination.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';

interface FilterOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    TableModule,
    InputTextModule,
    DropdownModule,
    ButtonModule,
    TagModule,
    CalendarModule,
    StatusBadgeComponent,
    EmptyStateComponent,
    SkeletonLoaderComponent,
    DateEsPipe,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Documentos</h1>
        <button
          pButton
          label="Subir documento"
          icon="pi pi-upload"
          class="p-button-warning"
          routerLink="/documents/upload"
        ></button>
      </div>

      <div class="toolbar">
        <form [formGroup]="filterForm" class="toolbar-filters">
          <span class="p-input-icon-left search-field">
            <i class="pi pi-search"></i>
            <input
              pInputText
              type="text"
              placeholder="Buscar documentos..."
              formControlName="search"
              class="w-full"
            />
          </span>

          <p-dropdown
            formControlName="status"
            [options]="statusOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Estado"
            styleClass="w-40"
            [showClear]="true"
          ></p-dropdown>

          <p-dropdown
            formControlName="type"
            [options]="typeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Tipo"
            styleClass="w-44"
            [showClear]="true"
          ></p-dropdown>

          <p-calendar
            formControlName="dateFrom"
            placeholder="Desde"
            dateFormat="dd/mm/yy"
            styleClass="w-40"
            [showClear]="true"
          ></p-calendar>

          <p-calendar
            formControlName="dateTo"
            placeholder="Hasta"
            dateFormat="dd/mm/yy"
            styleClass="w-40"
            [showClear]="true"
          ></p-calendar>

          <button
            pButton
            type="button"
            icon="pi pi-filter-slash"
            class="p-button-text"
            (click)="clearFilters()"
            pTooltip="Limpiar filtros"
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
          (action)="loadDocuments()"
        ></app-empty-state>
      } @else if (documents().length === 0) {
        <app-empty-state
          icon="pi pi-folder-open"
          title="No se encontraron documentos"
          message="Probá ajustando los filtros o subí tu primer documento."
          actionLabel="Subir documento"
          (action)="goToUpload()"
        ></app-empty-state>
      } @else {
        <div class="table-wrapper">
          <p-table
            [value]="documents()"
            [paginator]="true"
            [rows]="pageSize"
            [totalRecords]="totalRecords()"
            [lazy]="true"
            (onLazyLoad)="onLazyLoad($event)"
            [sortField]="'created_at'"
            [sortOrder]="-1"
            [rowsPerPageOptions]="[10, 20, 50]"
            styleClass="p-datatable-striped"
            [scrollable]="true"
            scrollHeight="flex"
          >
          <ng-template pTemplate="header">
            <tr>
              <th pSortableColumn="title">
                Título <p-sortIcon field="title"></p-sortIcon>
              </th>
              <th pSortableColumn="classification">
                Tipo <p-sortIcon field="classification"></p-sortIcon>
              </th>
              <th>Cliente</th>
              <th>Expediente</th>
              <th>Estado</th>
              <th pSortableColumn="created_at">
                Fecha <p-sortIcon field="created_at"></p-sortIcon>
              </th>
              <th class="actions-col">Acciones</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-doc>
            <tr [routerLink]="['/documents', doc.id]" class="cursor-pointer hover-row">
              <td>
                <a [routerLink]="['/documents', doc.id]" class="doc-title" (click)="$event.stopPropagation()">
                  {{ doc.title }}
                </a>
              </td>
              <td>
                @if (doc.classification) {
                  <p-tag [value]="doc.classification" severity="secondary"></p-tag>
                } @else {
                  <span class="text-muted">—</span>
                }
              </td>
              <td>
                <span class="text-muted">—</span>
              </td>
              <td>
                @if (doc.matter_id) {
                  <a [routerLink]="['/matters', doc.matter_id]" class="matter-link" (click)="$event.stopPropagation()">
                    {{ doc.matter_id }}
                  </a>
                } @else {
                  <span class="text-muted">—</span>
                }
              </td>
              <td>
                <app-status-badge [status]="docStatus(doc)"></app-status-badge>
              </td>
              <td>{{ doc.created_at | dateEs:'short' }}</td>
              <td class="actions-col">
                <div class="actions">
                  <button
                    pButton
                    type="button"
                    icon="pi pi-pencil"
                    class="p-button-text p-button-sm"
                    (click)="$event.stopPropagation(); goToEdit(doc.id)"
                  ></button>
                  <button
                    pButton
                    type="button"
                    icon="pi pi-trash"
                    class="p-button-text p-button-sm p-button-danger"
                    (click)="$event.stopPropagation(); deleteDocument(doc)"
                  ></button>
                </div>
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

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .page-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
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

    .search-field {
      flex: 1;
      min-width: 240px;
    }

    .search-field input {
      width: 100%;
    }

    .doc-title {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
    }

    .doc-title:hover {
      color: var(--color-gold);
      text-decoration: underline;
    }

    .matter-link {
      color: var(--color-review);
      text-decoration: none;
      font-size: 0.875rem;
    }

    .matter-link:hover {
      text-decoration: underline;
    }

    .text-muted {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    .actions {
      display: flex;
      gap: 0.25rem;
    }

    .table-wrapper {
      overflow-x: auto;
    }

    .actions-col {
      width: 6rem;
      text-align: center;
    }

    .hover-row:hover {
      background-color: var(--surface-hover);
    }

    :host ::ng-deep .p-datatable .p-datatable-tbody > tr {
      cursor: pointer;
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
  `],
})
export class DocumentListComponent implements OnInit {
  private readonly documentService = inject(DocumentService);
  private readonly fb = inject(FormBuilder);

  readonly documents = signal<DocumentOut[]>([]);
  readonly loading = signal(false);
  readonly totalRecords = signal(0);
  readonly page = signal(0);
  readonly error = signal<string | null>(null);

  readonly pageSize = 20;

  filterForm: FormGroup = this.fb.group({
    search: [''],
    status: [null],
    type: [null],
    dateFrom: [null],
    dateTo: [null],
  });

  readonly statusOptions: FilterOption[] = [
    { label: 'Listo', value: 'ready' },
    { label: 'Pendiente', value: 'pending' },
    { label: 'En revisión', value: 'review' },
    { label: 'Crítico', value: 'critical' },
  ];

  readonly typeOptions: FilterOption[] = [
    { label: 'Contrato', value: 'contrato' },
    { label: 'Demanda', value: 'demanda' },
    { label: 'Sentencia', value: 'sentencia' },
    { label: 'Dictamen', value: 'dictamen' },
    { label: 'Escrito', value: 'escrito' },
    { label: 'Informe', value: 'informe' },
  ];

  private readonly searchSubject = new Subject<string>();

  constructor() {
    effect(() => {
      this.loadDocuments();
    }, { allowSignalWrites: true });

    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(() => {
      this.page.set(0);
      this.loadDocuments();
    });
  }

  ngOnInit(): void {
    this.loadDocuments();

    this.filterForm.valueChanges.subscribe(() => {
      this.page.set(0);
      this.loadDocuments();
    });
  }

  loadDocuments(): void {
    this.loading.set(true);
    this.error.set(null);

    const form = this.filterForm.value;
    const params: Record<string, string | number> = {
      limit: this.pageSize,
      offset: this.page() * this.pageSize,
    };

    if (form.status) params['status'] = form.status;
    if (form.type) params['document_type'] = form.type;
    const dateFrom = this.toIsoDate(form.dateFrom);
    const dateTo = this.toIsoDate(form.dateTo);
    if (dateFrom) params['date_from'] = dateFrom;
    if (dateTo) params['date_to'] = dateTo;

    this.documentService.list(params).pipe(
      finalize(() => this.loading.set(false))
    ).subscribe({
      next: (res: PaginatedResponse<DocumentOut>) => {
        // Client-side search filter if search text is present
        let items = res.items;
        if (form.search?.trim()) {
          const q = form.search.trim().toLowerCase();
          items = items.filter(d =>
            d.title.toLowerCase().includes(q) ||
            (d.classification?.toLowerCase().includes(q) ?? false)
          );
        }
        this.documents.set(items);
        this.totalRecords.set(res.total);
      },
      error: (err) => {
        this.error.set(err.error?.detail ?? 'No se pudieron cargar los documentos.');
      },
    });
  }

  onLazyLoad(event: any): void {
    const newPage = event.first / event.rows;
    if (newPage !== this.page()) {
      this.page.set(newPage);
      this.loadDocuments();
    }
  }

  clearFilters(): void {
    this.filterForm.reset({
      search: '',
      status: null,
      type: null,
      dateFrom: null,
      dateTo: null,
    });
    this.page.set(0);
    this.loadDocuments();
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

  goToUpload(): void {
    // Handled by routerLink in template; this is for programmatic navigation if needed
  }

  goToEdit(id: string): void {
    // Navigation handled by router
  }

  deleteDocument(doc: DocumentOut): void {
    if (!confirm(`¿Eliminar "${doc.title}"?`)) return;
    this.documentService.delete(doc.id).subscribe({
      next: () => this.loadDocuments(),
      error: () => this.error.set('Error al eliminar el documento.'),
    });
  }

  private toIsoDate(date: Date | string | null): string | undefined {
    if (!date) return undefined;
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toISOString().split('T')[0];
  }
}
