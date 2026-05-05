import { Component, input, computed } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [NgClass],
  template: `<span class="badge" [ngClass]="classes()">{{ label() }}</span>`,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.625rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      line-height: 1.25;
      white-space: nowrap;
    }

    .badge-ready {
      background-color: rgba(45, 106, 79, 0.12);
      color: var(--color-ready);
    }

    .badge-pending {
      background-color: rgba(188, 108, 37, 0.12);
      color: var(--color-pending);
    }

    .badge-review {
      background-color: rgba(38, 70, 83, 0.12);
      color: var(--color-review);
    }

    .badge-critical {
      background-color: rgba(155, 34, 38, 0.12);
      color: var(--color-critical);
    }

    .badge-default {
      background-color: rgba(44, 44, 44, 0.08);
      color: var(--color-text-secondary);
    }
  `],
})
export class StatusBadgeComponent {
  status = input<string>('');

  readonly label = computed(() => {
    const map: Record<string, string> = {
      ready: 'Listo',
      pending: 'Pendiente',
      review: 'En revisión',
      critical: 'Vencido',
    };
    return map[this.status()] ?? this.status();
  });

  readonly classes = computed(() => {
    const s = this.status();
    if (s === 'ready') return 'badge-ready';
    if (s === 'pending') return 'badge-pending';
    if (s === 'review') return 'badge-review';
    if (s === 'critical') return 'badge-critical';
    return 'badge-default';
  });
}
