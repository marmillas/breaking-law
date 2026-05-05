import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, finalize } from 'rxjs';
import { TableModule } from 'primeng/table';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';

import { ClientService } from '../client.service';
import { ClientOut } from '../../../models/client.model';
import { PaginatedResponse } from '../../../models/pagination.model';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';

@Component({
  selector: 'app-client-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    TableModule,
    InputTextModule,
    ButtonModule,
    EmptyStateComponent,
    SkeletonLoaderComponent,
    DateEsPipe,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Clientes</h1>
        <button
          pButton
          label="Nuevo cliente"
          icon="pi pi-plus"
          class="p-button-warning"
          (click)="goToNew()"
        ></button>
      </div>

      <div class="toolbar">
        <form [formGroup]="searchForm" class="toolbar-filters">
          <span class="p-input-icon-left search-field">
            <i class="pi pi-search"></i>
            <input
              pInputText
              type="text"
              placeholder="Buscar clientes..."
              formControlName="search"
              class="w-full"
            />
          </span>

          <button
            pButton
            type="button"
            icon="pi pi-filter-slash"
            class="p-button-text"
            (click)="clearSearch()"
            title="Limpiar búsqueda"
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
          (action)="loadClients()"
        ></app-empty-state>
      } @else if (clients().length === 0) {
        <app-empty-state
          icon="pi pi-users"
          title="Sin clientes"
          message="Agregá tu primer cliente"
          actionLabel="Nuevo cliente"
          (action)="goToNew()"
        ></app-empty-state>
      } @else {
        <div class="table-wrapper">
          <p-table
            [value]="clients()"
            [paginator]="true"
            [rows]="pageSize"
            [totalRecords]="totalRecords()"
            styleClass="p-datatable-striped"
            [scrollable]="true"
            scrollHeight="flex"
          >
          <ng-template pTemplate="header">
            <tr>
              <th>Nombre</th>
              <th>Email</th>
              <th>Teléfono</th>
              <th>Fecha de alta</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-client>
            <tr [routerLink]="['/clients', client.id]" class="cursor-pointer hover-row">
              <td>
                <a
                  [routerLink]="['/clients', client.id]"
                  class="client-name"
                  (click)="$event.stopPropagation()"
                >
                  {{ client.name }}
                </a>
              </td>
              <td>{{ client.email }}</td>
              <td>
                @if (client.phone) {
                  {{ client.phone }}
                } @else {
                  <span class="text-muted">—</span>
                }
              </td>
              <td>{{ client.created_at | dateEs:'short' }}</td>
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

    .client-name {
      color: var(--color-text);
      text-decoration: none;
      font-weight: 500;
    }

    .client-name:hover {
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
export class ClientListComponent implements OnInit {
  private readonly clientService = inject(ClientService);
  private readonly fb = inject(FormBuilder);

  readonly clients = signal<ClientOut[]>([]);
  readonly loading = signal(false);
  readonly totalRecords = signal(0);
  readonly page = signal(0);
  readonly searchQuery = signal('');
  readonly error = signal<string | null>(null);

  readonly pageSize = 20;

  searchForm: FormGroup = this.fb.group({
    search: [''],
  });

  private readonly searchSubject = new Subject<string>();

  constructor() {
    this.searchSubject
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((query) => {
        this.searchQuery.set(query);
        this.page.set(0);
        this.loadClients();
      });
  }

  ngOnInit(): void {
    this.loadClients();

    this.searchForm.valueChanges.subscribe(() => {
      this.searchSubject.next(this.searchForm.value.search ?? '');
    });
  }

  loadClients(): void {
    this.loading.set(true);
    this.error.set(null);

    const query = this.searchQuery().trim().toLowerCase();

    this.clientService
      .list({ limit: 1000 })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (res: PaginatedResponse<ClientOut>) => {
          let items = res.items;
          if (query) {
            items = items.filter(
              (c) =>
                c.name.toLowerCase().includes(query) ||
                c.email.toLowerCase().includes(query) ||
                (c.phone?.toLowerCase().includes(query) ?? false)
            );
          }
          this.clients.set(items);
          this.totalRecords.set(items.length);
        },
        error: (err) => {
          this.error.set(err.error?.detail ?? 'No se pudieron cargar los clientes.');
        },
      });
  }

  clearSearch(): void {
    this.searchForm.reset({ search: '' });
    this.searchQuery.set('');
    this.page.set(0);
    this.loadClients();
  }

  goToNew(): void {
    // Navigation handled by routerLink in template
  }
}
