import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TimeService } from '../time.service';

@Component({
  selector: 'app-timer-widget',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (timeService.runningEntry(); as entry) {
      <div class="timer-widget" (click)="goToTracker()">
        <div class="timer-elapsed">{{ timeService.elapsed() }}</div>
        <div class="timer-info">
          <span class="client">{{ entry.clientName }}</span>
          <span class="matter">{{ entry.matterReference }}</span>
        </div>
        <button class="timer-stop" (click)="stopTimer($event)" title="Detener">
          <i class="pi pi-stop"></i>
        </button>
      </div>
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .timer-widget {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      padding: 0.625rem 0.875rem;
      margin: 0.5rem;
      background-color: rgba(0, 0, 0, 0.25);
      border-left: 3px solid var(--color-gold);
      border-radius: 6px;
      cursor: pointer;
      transition: background-color var(--transition-fast);
    }

    .timer-widget:hover {
      background-color: rgba(0, 0, 0, 0.35);
    }

    .timer-elapsed {
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--color-gold);
      white-space: nowrap;
      min-width: 64px;
    }

    .timer-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
      gap: 0.125rem;
    }

    .timer-info .client {
      font-size: 0.8125rem;
      font-weight: 500;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .timer-info .matter {
      font-size: 0.75rem;
      color: var(--color-text-sidebar);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .timer-stop {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 4px;
      color: var(--color-critical);
      cursor: pointer;
      font-size: 0.75rem;
      flex-shrink: 0;
      transition: background-color var(--transition-fast), border-color var(--transition-fast);
    }

    .timer-stop:hover {
      background-color: rgba(155, 34, 38, 0.15);
      border-color: rgba(155, 34, 38, 0.4);
    }
  `],
})
export class TimerWidgetComponent {
  readonly timeService = inject(TimeService);
  private readonly router = inject(Router);

  stopTimer(event: Event): void {
    event.stopPropagation();
    const entry = this.timeService.runningEntry();
    if (!entry) return;

    this.timeService.stopTimer(entry.entryId).subscribe({
      next: () => {
        this.timeService.stopLocalTimer();
      },
      error: () => {
        // Even if stop fails on backend, stop local timer
        this.timeService.stopLocalTimer();
      },
    });
  }

  goToTracker(): void {
    this.router.navigate(['/time/tracker']);
  }
}
