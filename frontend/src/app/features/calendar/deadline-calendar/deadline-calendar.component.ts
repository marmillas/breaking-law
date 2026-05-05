import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { finalize } from 'rxjs';

import { DeadlineService } from '../deadline.service';
import { Deadline } from '../../../models/deadline.model';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';
import { ScrollRevealDirective } from '../../../shared/directives/scroll-reveal.directive';

@Component({
  selector: 'app-deadline-calendar',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ButtonModule,
    TagModule,
    EmptyStateComponent,
    SkeletonLoaderComponent,
    DateEsPipe,
    ScrollRevealDirective,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Calendario de vencimientos</h1>
      </div>

      <div class="calendar-layout">
        <!-- Calendar Grid -->
        <div class="calendar-panel">
          <div class="calendar-header">
            <button class="nav-btn" (click)="prevMonth()" aria-label="Mes anterior">
              <i class="pi pi-chevron-left"></i>
            </button>
            <span class="month-label">{{ monthLabel() }}</span>
            <button class="nav-btn" (click)="nextMonth()" aria-label="Mes siguiente">
              <i class="pi pi-chevron-right"></i>
            </button>
          </div>

          @if (loading()) {
            <app-skeleton-loader variant="card" [count]="6"></app-skeleton-loader>
          } @else {
            <div class="calendar-grid">
              <div class="day-header" *ngFor="let d of dayNames">{{ d }}</div>
              @for (day of calendarDays(); track day.date) {
                <div
                  class="day-cell"
                  [class.other-month]="day.otherMonth"
                  [class.today]="day.isToday"
                  [class.selected]="day.isSelected"
                  (click)="selectDay(day.date)"
                  role="button"
                  [attr.aria-label]="day.dayOfMonth + ' de ' + monthLabel()"
                  tabindex="0"
                  (keydown.enter)="selectDay(day.date)"
                >
                  <span class="day-number">{{ day.dayOfMonth }}</span>
                  <div class="day-dots">
                    @for (dot of day.dots; track dot.color + $index) {
                      <span class="dot" [class]="dot.color"></span>
                    }
                  </div>
                </div>
              }
            </div>
          }
        </div>

        <!-- Side Panel -->
        <div class="side-panel">
          <div class="panel-header">
            <h2 class="panel-title">
              @if (selectedDate()) {
                Vencimientos del {{ selectedDate()! | dateEs:'short' }}
              } @else {
                Próximos vencimientos
              }
            </h2>
          </div>

          @if (loading()) {
            <app-skeleton-loader variant="card" [count]="3"></app-skeleton-loader>
          } @else if (filteredDeadlines().length === 0) {
            <app-empty-state
              icon="pi pi-calendar"
              title="Sin vencimientos"
              message="No hay vencimientos para esta fecha."
            ></app-empty-state>
          } @else {
            <div class="deadline-list">
              @for (dl of filteredDeadlines(); track dl.id) {
                <div class="deadline-row" appScrollReveal>
                  <div class="deadline-main">
                    <span class="deadline-title">{{ dl.title }}</span>
                    @if (dl.matter_id) {
                      <a [routerLink]="['/matters', dl.matter_id]" class="deadline-matter" (click)="$event.stopPropagation()">
                        Ver expediente
                      </a>
                    }
                  </div>
                  <div class="deadline-meta">
                    <span class="deadline-date">{{ dl.due_date | dateEs:'short' }}</span>
                    <span class="deadline-status" [class]="statusClass(dl)">
                      {{ statusLabel(dl) }}
                    </span>
                  </div>
                  <div class="deadline-actions">
                    @if (dl.status !== 'completed') {
                      <button
                        pButton
                        type="button"
                        icon="pi pi-check"
                        class="p-button-text p-button-sm"
                        title="Completar"
                        (click)="completeDeadline(dl.id)"
                      ></button>
                    }
                    @if (dl.status === 'pending' && !dl.acknowledged_at) {
                      <button
                        pButton
                        type="button"
                        icon="pi pi-eye"
                        class="p-button-text p-button-sm"
                        title="Reconocer"
                        (click)="acknowledgeDeadline(dl.id)"
                      ></button>
                    }
                  </div>
                </div>
              }
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
    }

    .page-header {
      margin-bottom: 1.5rem;
    }

    .page-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
    }

    .calendar-layout {
      display: grid;
      grid-template-columns: 1fr 380px;
      gap: 1.5rem;
    }

    @media (max-width: 960px) {
      .calendar-layout {
        grid-template-columns: 1fr;
      }
    }

    .calendar-panel {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.25rem;
    }

    .calendar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    .nav-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background: transparent;
      border: 1px solid var(--color-border);
      border-radius: 6px;
      color: var(--color-text);
      cursor: pointer;
      font-size: 0.875rem;
      transition: background-color var(--transition-fast);
    }

    .nav-btn:hover {
      background-color: var(--surface-hover);
    }

    .month-label {
      font-family: var(--font-heading);
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--color-text);
      text-transform: capitalize;
    }

    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 0.25rem;
    }

    .day-header {
      text-align: center;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--color-text-secondary);
      padding: 0.5rem 0;
    }

    .day-cell {
      aspect-ratio: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.25rem;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color var(--transition-fast);
      position: relative;
      padding: 0.25rem;
    }

    .day-cell:hover {
      background-color: var(--surface-hover);
    }

    .day-cell.other-month {
      opacity: 0.4;
    }

    .day-cell.today {
      background-color: rgba(184, 150, 90, 0.1);
      outline: 1px solid var(--color-gold);
    }

    .day-cell.selected {
      background-color: rgba(184, 150, 90, 0.2);
    }

    .day-number {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text);
    }

    .day-dots {
      display: flex;
      gap: 3px;
      flex-wrap: wrap;
      justify-content: center;
      max-width: 100%;
    }

    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .dot-red {
      background-color: var(--color-critical);
    }

    .dot-orange {
      background-color: var(--color-pending);
    }

    .dot-green {
      background-color: var(--color-ready);
    }

    .side-panel {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.25rem;
      min-height: 400px;
    }

    .panel-header {
      margin-bottom: 1rem;
    }

    .panel-title {
      font-family: var(--font-heading);
      font-size: 1rem;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }

    .deadline-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .deadline-row {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
      padding: 0.75rem;
      border-radius: 6px;
      border: 1px solid var(--color-border);
      transition: background-color var(--transition-fast);
    }

    .deadline-row:hover {
      background-color: var(--surface-hover);
    }

    .deadline-main {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .deadline-title {
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--color-text);
    }

    .deadline-matter {
      font-size: 0.8125rem;
      color: var(--color-review);
      text-decoration: none;
    }

    .deadline-matter:hover {
      text-decoration: underline;
    }

    .deadline-meta {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .deadline-date {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
    }

    .deadline-status {
      display: inline-flex;
      align-items: center;
      padding: 0.125rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.6875rem;
      font-weight: 600;
    }

    .status-overdue {
      background-color: rgba(155, 34, 38, 0.12);
      color: var(--color-critical);
    }

    .status-upcoming {
      background-color: rgba(188, 108, 37, 0.12);
      color: var(--color-pending);
    }

    .status-completed {
      background-color: rgba(45, 106, 79, 0.12);
      color: var(--color-ready);
    }

    .status-pending {
      background-color: rgba(44, 44, 44, 0.08);
      color: var(--color-text-secondary);
    }

    .deadline-actions {
      display: flex;
      gap: 0.25rem;
      margin-top: 0.25rem;
    }
  `],
})
export class DeadlineCalendarComponent implements OnInit {
  private readonly deadlineService = inject(DeadlineService);

  readonly currentMonth = signal(new Date());
  readonly selectedDate = signal<string | null>(null);
  readonly deadlines = signal<Deadline[]>([]);
  readonly loading = signal(false);

  readonly dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

  readonly monthLabel = () => {
    const d = this.currentMonth();
    return d.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
  };

  readonly calendarDays = () => {
    const month = this.currentMonth();
    const year = month.getFullYear();
    const monthIndex = month.getMonth();

    const firstDayOfMonth = new Date(year, monthIndex, 1);
    const lastDayOfMonth = new Date(year, monthIndex + 1, 0);
    const daysInMonth = lastDayOfMonth.getDate();

    const startDayOfWeek = firstDayOfMonth.getDay(); // 0 = Sunday

    const days: CalendarDay[] = [];
    const today = new Date();
    const todayStr = this.dateKey(today);
    const selectedStr = this.selectedDate();

    // Previous month padding
    const prevMonthLastDay = new Date(year, monthIndex, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const d = prevMonthLastDay - i;
      const date = new Date(year, monthIndex - 1, d);
      days.push(this.makeDay(date, true, todayStr, selectedStr));
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, monthIndex, d);
      days.push(this.makeDay(date, false, todayStr, selectedStr));
    }

    // Next month padding to complete 6 rows (42 cells) or minimum to end of week
    const remaining = (7 - (days.length % 7)) % 7;
    for (let d = 1; d <= remaining; d++) {
      const date = new Date(year, monthIndex + 1, d);
      days.push(this.makeDay(date, true, todayStr, selectedStr));
    }

    return days;
  };

  readonly deadlinesByDay = () => {
    const map = new Map<string, Deadline[]>();
    for (const dl of this.deadlines()) {
      const key = this.dateKey(new Date(dl.due_date));
      const arr = map.get(key) ?? [];
      arr.push(dl);
      map.set(key, arr);
    }
    return map;
  };

  readonly filteredDeadlines = () => {
    const selected = this.selectedDate();
    if (!selected) {
      // Show upcoming deadlines for the current month
      return this.deadlines().filter((dl) => dl.status !== 'completed');
    }
    const map = this.deadlinesByDay();
    return map.get(selected) ?? [];
  };

  ngOnInit(): void {
    this.loadDeadlinesForMonth();
  }

  loadDeadlinesForMonth(): void {
    const month = this.currentMonth();
    const year = month.getFullYear();
    const monthIndex = month.getMonth();

    const startDate = new Date(year, monthIndex, 1);
    const endDate = new Date(year, monthIndex + 1, 0);
    endDate.setHours(23, 59, 59, 999);

    this.loading.set(true);
    this.deadlineService
      .getDeadlines({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        limit: 500,
      })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (items) => {
          this.deadlines.set(items);
        },
        error: () => {
          this.deadlines.set([]);
        },
      });
  }

  prevMonth(): void {
    const d = this.currentMonth();
    this.currentMonth.set(new Date(d.getFullYear(), d.getMonth() - 1, 1));
    this.loadDeadlinesForMonth();
  }

  nextMonth(): void {
    const d = this.currentMonth();
    this.currentMonth.set(new Date(d.getFullYear(), d.getMonth() + 1, 1));
    this.loadDeadlinesForMonth();
  }

  selectDay(date: Date): void {
    const key = this.dateKey(date);
    if (this.selectedDate() === key) {
      this.selectedDate.set(null);
    } else {
      this.selectedDate.set(key);
    }
  }

  acknowledgeDeadline(id: string): void {
    this.deadlineService.acknowledge(id).subscribe({
      next: () => this.loadDeadlinesForMonth(),
    });
  }

  completeDeadline(id: string): void {
    this.deadlineService.complete(id).subscribe({
      next: () => this.loadDeadlinesForMonth(),
    });
  }

  statusLabel(dl: Deadline): string {
    if (dl.status === 'completed') return 'Completado';
    const due = new Date(dl.due_date);
    const now = new Date();
    const diffDays = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 'Vencido';
    if (diffDays <= 7) return 'Próximo';
    return 'Pendiente';
  }

  statusClass(dl: Deadline): string {
    if (dl.status === 'completed') return 'status-completed';
    const due = new Date(dl.due_date);
    const now = new Date();
    const diffDays = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return 'status-overdue';
    if (diffDays <= 7) return 'status-upcoming';
    return 'status-pending';
  }

  private makeDay(date: Date, otherMonth: boolean, todayStr: string, selectedStr: string | null): CalendarDay {
    const key = this.dateKey(date);
    const map = this.deadlinesByDay();
    const dayDeadlines = map.get(key) ?? [];

    const dots: { color: string }[] = [];
    const hasOverdue = dayDeadlines.some((dl) => this.statusClass(dl) === 'status-overdue');
    const hasUpcoming = dayDeadlines.some((dl) => this.statusClass(dl) === 'status-upcoming');
    const hasCompleted = dayDeadlines.some((dl) => dl.status === 'completed');

    if (hasOverdue) dots.push({ color: 'dot-red' });
    if (hasUpcoming) dots.push({ color: 'dot-orange' });
    if (hasCompleted) dots.push({ color: 'dot-green' });

    return {
      date,
      dayOfMonth: date.getDate(),
      otherMonth,
      isToday: key === todayStr,
      isSelected: key === selectedStr,
      dots,
    };
  }

  private dateKey(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}

interface CalendarDay {
  date: Date;
  dayOfMonth: number;
  otherMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  dots: { color: string }[];
}
