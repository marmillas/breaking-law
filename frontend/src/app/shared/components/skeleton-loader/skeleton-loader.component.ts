import { Component, input } from '@angular/core';
import { NgFor, NgSwitch, NgSwitchCase, NgSwitchDefault } from '@angular/common';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [NgFor, NgSwitch, NgSwitchCase, NgSwitchDefault],
  template: `
    <ng-container *ngFor="let i of items()">
      <div class="skeleton" [class.skeleton-card]="variant() === 'card'" [class.skeleton-table]="variant() === 'table'" [class.skeleton-text]="variant() === 'text'">
        <ng-container [ngSwitch]="variant()">
          <div *ngSwitchCase="'card'" class="card-variant">
            <div class="skeleton-header"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
          </div>
          <div *ngSwitchCase="'table'" class="table-variant">
            <div class="skeleton-row">
              <div class="skeleton-cell"></div>
              <div class="skeleton-cell"></div>
              <div class="skeleton-cell"></div>
              <div class="skeleton-cell"></div>
            </div>
          </div>
          <div *ngSwitchDefault class="text-variant">
            <div class="skeleton-line"></div>
            <div class="skeleton-line medium"></div>
            <div class="skeleton-line short"></div>
          </div>
        </ng-container>
      </div>
    </ng-container>
  `,
  styles: [`
    .skeleton {
      background-color: var(--color-surface);
      border-radius: 6px;
      overflow: hidden;
    }

    .skeleton-card {
      padding: 1.25rem;
      margin-bottom: 1rem;
      border: 1px solid var(--color-border);
    }

    .skeleton-table {
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
      border-bottom: 1px solid var(--color-border);
    }

    .skeleton-text {
      padding: 0.5rem 0;
      margin-bottom: 0.75rem;
    }

    .skeleton-header {
      height: 1.25rem;
      width: 40%;
      background-color: var(--color-sepia-dark);
      border-radius: 4px;
      margin-bottom: 1rem;
      animation: skeleton-pulse 1.5s ease-in-out infinite;
    }

    .skeleton-line {
      height: 0.875rem;
      width: 100%;
      background-color: var(--color-sepia-dark);
      border-radius: 4px;
      margin-bottom: 0.625rem;
      animation: skeleton-pulse 1.5s ease-in-out infinite;
    }

    .skeleton-line.medium {
      width: 70%;
    }

    .skeleton-line.short {
      width: 45%;
    }

    .skeleton-row {
      display: flex;
      gap: 1rem;
    }

    .skeleton-cell {
      flex: 1;
      height: 0.875rem;
      background-color: var(--color-sepia-dark);
      border-radius: 4px;
      animation: skeleton-pulse 1.5s ease-in-out infinite;
    }

    @keyframes skeleton-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
  `],
})
export class SkeletonLoaderComponent {
  variant = input<'card' | 'table' | 'text'>('text');
  count = input<number>(1);

  items() {
    return Array.from({ length: this.count() }, (_, i) => i);
  }
}
