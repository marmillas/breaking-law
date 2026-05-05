import { Component, input, output } from '@angular/core';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="empty-state">
      <i class="pi" [class]="icon()"></i>
      <h3 class="title">{{ title() }}</h3>
      <p class="message">{{ message() }}</p>
      <button *ngIf="actionLabel()" class="action-btn" (click)="action.emit()">
        {{ actionLabel() }}
      </button>
    </div>
  `,
  styles: [`
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 3rem 1.5rem;
      color: var(--color-text-secondary);
    }

    .empty-state i {
      font-size: 3rem;
      color: var(--color-gold);
      margin-bottom: 1rem;
      opacity: 0.7;
    }

    .title {
      font-family: var(--font-heading);
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--color-text);
      margin-bottom: 0.5rem;
    }

    .message {
      font-size: 0.9375rem;
      color: var(--color-text-secondary);
      max-width: 320px;
      margin-bottom: 1.25rem;
      line-height: 1.5;
    }

    .action-btn {
      padding: 0.5rem 1.25rem;
      background-color: var(--color-gold);
      color: #ffffff;
      border: none;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: background-color var(--transition-fast);
    }

    .action-btn:hover {
      background-color: var(--color-gold-dark);
    }
  `],
})
export class EmptyStateComponent {
  icon = input<string>('pi pi-inbox');
  title = input<string>('Sin datos');
  message = input<string>('No hay información para mostrar.');
  actionLabel = input<string>('');
  action = output<void>();
}
