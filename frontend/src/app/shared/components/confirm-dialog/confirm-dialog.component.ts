import { Component, input, output } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [DialogModule, ButtonModule, NgClass],
  template: `
    <p-dialog
      [visible]="visible()"
      (visibleChange)="onVisibleChange($event)"
      [header]="title()"
      [modal]="true"
      [closable]="true"
      [style]="{ width: '24rem' }"
      [draggable]="false"
      [resizable]="false"
    >
      <div class="confirm-body">
        <i class="pi pi-exclamation-circle confirm-icon" [ngClass]="severityClass()"></i>
        <p class="confirm-message">{{ message() }}</p>
      </div>
      <div class="confirm-footer">
        <p-button
          label="Cancelar"
          styleClass="p-button-text"
          (onClick)="onCancel()"
        />
        <p-button
          [label]="confirmLabel()"
          [styleClass]="confirmButtonClass()"
          (onClick)="onConfirm()"
        />
      </div>
    </p-dialog>
  `,
  styles: [`
    .confirm-body {
      display: flex;
      align-items: flex-start;
      gap: 0.875rem;
      padding: 0.5rem 0 1rem;
    }

    .confirm-icon {
      font-size: 1.5rem;
      flex-shrink: 0;
      margin-top: 0.125rem;
    }

    .confirm-icon.danger {
      color: var(--color-critical);
    }

    .confirm-icon.warning {
      color: var(--color-pending);
    }

    .confirm-message {
      font-size: 0.9375rem;
      line-height: 1.5;
      color: var(--color-text);
      margin: 0;
    }

    .confirm-footer {
      display: flex;
      justify-content: flex-end;
      gap: 0.5rem;
      padding-top: 0.5rem;
    }

    :host ::ng-deep .p-dialog-header {
      font-family: var(--font-heading);
      font-weight: 700;
    }
  `],
})
export class ConfirmDialogComponent {
  visible = input<boolean>(false);
  title = input<string>('Confirmar');
  message = input<string>('¿Está seguro?');
  confirmLabel = input<string>('Confirmar');
  severity = input<'danger' | 'warning'>('warning');

  confirm = output<void>();
  cancel = output<void>();

  severityClass() {
    return this.severity() === 'danger' ? 'danger' : 'warning';
  }

  confirmButtonClass() {
    return this.severity() === 'danger' ? 'p-button-danger' : 'p-button-warning';
  }

  onVisibleChange(visible: boolean): void {
    if (!visible) {
      this.cancel.emit();
    }
  }

  onConfirm(): void {
    this.confirm.emit();
  }

  onCancel(): void {
    this.cancel.emit();
  }
}
