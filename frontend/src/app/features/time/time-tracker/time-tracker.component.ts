import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { InputTextarea } from 'primeng/inputtextarea';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { TimeService } from '../time.service';
import { ClientService } from '../../clients/client.service';
import { MatterService } from '../../matters/matter.service';
import { TimeEntry } from '../../../models/time-entry.model';
import { ClientOut } from '../../../models/client.model';
import { MatterOut } from '../../../models/matter.model';
import { PaginatedResponse } from '../../../models/pagination.model';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';

@Component({
  selector: 'app-time-tracker',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    ButtonModule,
    DropdownModule,
    InputTextarea,
    TableModule,
    TagModule,
    EmptyStateComponent,
    SkeletonLoaderComponent,
    DateEsPipe,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Registrar tiempo</h1>
        <a routerLink="/time" class="back-link">← Ver historial</a>
      </div>

      <!-- Timer Form -->
      <div class="tracker-card">
        @if (dropdownsLoading()) {
          <app-skeleton-loader variant="card" [count]="2"></app-skeleton-loader>
        } @else if (!isRunning()) {
          <form [formGroup]="timerForm" class="tracker-form">
            <div class="form-row">
              <div class="form-field">
                <label>Cliente</label>
                <p-dropdown
                  [options]="clients()"
                  formControlName="client"
                  optionLabel="name"
                  placeholder="Seleccionar cliente"
                  [showClear]="true"
                  styleClass="w-full"
                  (onChange)="onClientChange($event.value)"
                ></p-dropdown>
              </div>

              <div class="form-field">
                <label>Expediente</label>
                <p-dropdown
                  [options]="matters()"
                  formControlName="matter"
                  optionLabel="title"
                  placeholder="Seleccionar expediente"
                  [showClear]="true"
                  [disabled]="matters().length === 0"
                  styleClass="w-full"
                ></p-dropdown>
              </div>
            </div>

            <div class="form-field">
              <label>Descripción</label>
              <textarea
                pInputTextarea
                formControlName="description"
                rows="3"
                placeholder="¿En qué estás trabajando?"
                class="w-full"
              ></textarea>
            </div>

            <div class="form-actions">
              <button
                pButton
                type="button"
                label="Iniciar"
                icon="pi pi-play"
                class="p-button-warning start-btn"
                [disabled]="timerForm.invalid || loading()"
                (click)="startTimer()"
              ></button>
            </div>
          </form>
        } @else {
          <!-- Active Timer -->
          <div class="active-timer">
            <div class="timer-display">{{ timeService.elapsed() }}</div>
            <div class="timer-meta">
              <span class="meta-client">{{ selectedClientName() }}</span>
              <span class="meta-matter">{{ selectedMatterTitle() }}</span>
              <span class="meta-desc">{{ timerForm.value.description }}</span>
            </div>
            <div class="timer-actions">
              <button
                pButton
                type="button"
                label="Detener"
                icon="pi pi-stop"
                class="p-button-danger stop-btn"
                (click)="stopTimer()"
              ></button>
            </div>
          </div>
        }
      </div>

      <!-- Recent Entries -->
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">Registros recientes</h2>
        </div>

        @if (loadingEntries()) {
          <app-skeleton-loader variant="table" [count]="3"></app-skeleton-loader>
        } @else if (recentEntries().length === 0) {
          <app-empty-state
            icon="pi pi-clock"
            title="Sin registros"
            message="Todavía no registraste tiempo."
          ></app-empty-state>
        } @else {
          <p-table [value]="recentEntries()" styleClass="p-datatable-striped" [scrollable]="true" scrollHeight="flex">
            <ng-template pTemplate="header">
              <tr>
                <th>Fecha</th>
                <th>Descripción</th>
                <th>Duración</th>
                <th>Facturable</th>
                <th>Estado</th>
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
                <td>
                  <p-tag [value]="entry.status" severity="secondary"></p-tag>
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </div>
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

    .back-link {
      color: var(--color-gold);
      text-decoration: none;
      font-weight: 500;
      font-size: 0.9375rem;
    }

    .back-link:hover {
      text-decoration: underline;
    }

    .tracker-card {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .tracker-form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .form-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }

    .form-field label {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--color-text-secondary);
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
    }

    .start-btn {
      background-color: var(--color-gold);
      border-color: var(--color-gold);
      color: var(--color-text);
    }

    .start-btn:hover {
      background-color: var(--color-gold-dark);
      border-color: var(--color-gold-dark);
    }

    .active-timer {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      padding: 2rem 1rem;
      text-align: center;
    }

    .timer-display {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 3.5rem;
      font-weight: 700;
      color: var(--color-gold);
      letter-spacing: 0.05em;
    }

    .timer-meta {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .meta-client {
      font-size: 1rem;
      font-weight: 600;
      color: var(--color-text);
    }

    .meta-matter {
      font-size: 0.875rem;
      color: var(--color-text-secondary);
    }

    .meta-desc {
      font-size: 0.875rem;
      color: var(--color-text-secondary);
      font-style: italic;
      max-width: 480px;
    }

    .timer-actions {
      margin-top: 0.5rem;
    }

    .stop-btn {
      min-width: 120px;
    }

    .section-card {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
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

    :host ::ng-deep .p-dropdown {
      width: 100%;
    }

    :host ::ng-deep .p-inputtextarea {
      width: 100%;
    }
  `],
})
export class TimeTrackerComponent implements OnInit, OnDestroy {
  readonly timeService = inject(TimeService);
  private readonly clientService = inject(ClientService);
  private readonly matterService = inject(MatterService);
  private readonly fb = inject(FormBuilder);

  readonly clients = signal<ClientOut[]>([]);
  readonly matters = signal<MatterOut[]>([]);
  readonly loading = signal(false);
  readonly loadingEntries = signal(false);
  readonly dropdownsLoading = signal(false);
  readonly isRunning = signal(false);
  readonly recentEntries = signal<TimeEntry[]>([]);
  readonly selectedClientName = signal('');
  readonly selectedMatterTitle = signal('');

  timerForm: FormGroup = this.fb.group({
    client: [null, Validators.required],
    matter: [null, Validators.required],
    description: ['', Validators.required],
  });

  ngOnInit(): void {
    this.loadClients();
    this.loadRecentEntries();

    // If there's already a running timer from another page, reflect it
    const running = this.timeService.runningEntry();
    if (running) {
      this.isRunning.set(true);
      this.selectedClientName.set(running.clientName);
      this.selectedMatterTitle.set(running.matterReference);
    }
  }

  ngOnDestroy(): void {
    // Do NOT stop the timer on destroy — it's a shared service timer
  }

  loadClients(): void {
    this.dropdownsLoading.set(true);
    this.clientService.list({ limit: 1000 }).subscribe({
      next: (res: PaginatedResponse<ClientOut>) => {
        this.clients.set(res.items);
        this.dropdownsLoading.set(false);
      },
      error: () => {
        this.dropdownsLoading.set(false);
      },
    });
  }

  onClientChange(client: ClientOut | null): void {
    this.matters.set([]);
    this.timerForm.patchValue({ matter: null });
    if (!client) return;

    this.dropdownsLoading.set(true);
    this.matterService.listByClient(client.id).subscribe({
      next: (res: PaginatedResponse<MatterOut>) => {
        this.matters.set(res.items);
        this.dropdownsLoading.set(false);
      },
      error: () => {
        this.dropdownsLoading.set(false);
      },
    });
  }

  startTimer(): void {
    if (this.timerForm.invalid) return;
    const values = this.timerForm.value;
    const client: ClientOut = values.client;
    const matter: MatterOut = values.matter;

    this.loading.set(true);
    this.timeService.startTimer(client.id, matter.id, values.description).subscribe({
      next: (entry: TimeEntry) => {
        this.loading.set(false);
        this.isRunning.set(true);
        this.selectedClientName.set(client.name);
        this.selectedMatterTitle.set(matter.title);
        this.timeService.startLocalTimer({
          entryId: entry.id,
          clientName: client.name,
          matterReference: matter.title,
          description: values.description,
        });
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  stopTimer(): void {
    const running = this.timeService.runningEntry();
    if (!running) return;

    this.timeService.stopTimer(running.entryId).subscribe({
      next: () => {
        this.timeService.stopLocalTimer();
        this.isRunning.set(false);
        this.timerForm.reset({ client: null, matter: null, description: '' });
        this.selectedClientName.set('');
        this.selectedMatterTitle.set('');
        this.loadRecentEntries();
      },
      error: () => {
        this.timeService.stopLocalTimer();
        this.isRunning.set(false);
        this.loadRecentEntries();
      },
    });
  }

  loadRecentEntries(): void {
    this.loadingEntries.set(true);
    this.timeService
      .getEntries({ limit: 10 })
      .pipe(finalize(() => this.loadingEntries.set(false)))
      .subscribe({
        next: (res: PaginatedResponse<TimeEntry>) => {
          this.recentEntries.set(res.items);
        },
        error: () => {
          this.recentEntries.set([]);
        },
      });
  }

  formatDuration(minutes: number | null): string {
    if (minutes === null || minutes === undefined) return '—';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }
}
