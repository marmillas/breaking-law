import { Component, input, computed } from '@angular/core';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-progress-bar',
  standalone: true,
  imports: [NgIf],
  template: `
    <div class="progress-wrapper">
      <div *ngIf="label() || showPercentage()" class="progress-header">
        <span *ngIf="label()" class="progress-label">{{ label() }}</span>
        <span *ngIf="showPercentage()" class="progress-percentage">{{ percentage() }}%</span>
      </div>
      <div class="progress-container">
        <div
          class="progress-fill"
          [class.scroll-driven]="isScrollDriven()"
          [style.width.%]="isScrollDriven() ? undefined : percentage()"
        ></div>
      </div>
    </div>
  `,
  styles: [`
    .progress-wrapper {
      width: 100%;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.375rem;
    }

    .progress-label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-secondary);
    }

    .progress-percentage {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--color-text);
    }

    .progress-container {
      width: 100%;
      height: 6px;
      background-color: var(--color-sepia-dark);
      border-radius: 3px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background-color: var(--color-gold);
      border-radius: 3px;
      transition: width 300ms ease;
      transform-origin: left;
    }

    .progress-fill.scroll-driven {
      width: 100%;
      transform: scaleX(var(--scroll-progress, 0));
      transition: none;
    }
  `],
})
export class ProgressBarComponent {
  value = input<number>(0);
  label = input<string>('');
  showPercentage = input<boolean>(true);

  readonly percentage = computed(() => Math.min(100, Math.max(0, Math.round(this.value()))));
  readonly isScrollDriven = computed(() => this.value() < 0); // negative value signals scroll-driven mode
}
