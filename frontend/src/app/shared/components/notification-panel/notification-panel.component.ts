import { Component, input, Output, EventEmitter, inject } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { NotificationStore } from '../../../core/notifications/notification.store';
import { AppNotification } from '../../../models/notification.model';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';

@Component({
  selector: 'app-notification-panel',
  standalone: true,
  imports: [CommonModule, DateEsPipe],
  template: `
    @if (visible()) {
      <div class="notification-panel">
        <div class="panel-header">
          <h3>Notificaciones</h3>
          @if (store.unreadCount() > 0) {
            <button (click)="markAllRead()">Marcar todas como leídas</button>
          }
        </div>
        <div class="panel-list">
          @for (notification of store.notifications(); track notification.id || $index) {
            <div class="notification-item" [class.unread]="!notification.read" (click)="onClick(notification)">
              <span class="notif-icon"><i [class]="iconFor(notification.type)"></i></span>
              <div class="notif-content">
                <span class="notif-title">{{ notification.title || notification.type }}</span>
                <span class="notif-message">{{ notification.message }}</span>
                @if (notification.created_at) {
                  <span class="notif-time">{{ notification.created_at | dateEs:'short' }}</span>
                }
              </div>
              @if (!notification.read) {
                <span class="unread-dot"></span>
              }
            </div>
          } @empty {
            <div class="empty">Sin notificaciones</div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .notification-panel {
      position: absolute;
      bottom: 100%;
      left: 0;
      margin-bottom: 0.5rem;
      width: 360px;
      max-height: 420px;
      background-color: var(--color-sidebar);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 100;
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.875rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      flex-shrink: 0;
    }

    .panel-header h3 {
      margin: 0;
      font-family: var(--font-heading);
      font-size: 1rem;
      font-weight: 600;
      color: #ffffff;
    }

    .panel-header button {
      background: transparent;
      border: none;
      color: var(--color-gold);
      font-size: 0.75rem;
      cursor: pointer;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      transition: background-color var(--transition-fast);
    }

    .panel-header button:hover {
      background-color: rgba(184, 150, 90, 0.12);
    }

    .panel-list {
      overflow-y: auto;
      flex: 1;
      padding: 0.5rem;
    }

    .notification-item {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.625rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color var(--transition-fast);
      position: relative;
    }

    .notification-item:hover {
      background-color: var(--color-sidebar-hover);
    }

    .notification-item.unread {
      background-color: rgba(184, 150, 90, 0.08);
    }

    .notification-item.unread:hover {
      background-color: rgba(184, 150, 90, 0.15);
    }

    .notif-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background-color: rgba(184, 150, 90, 0.15);
      color: var(--color-gold);
      font-size: 0.875rem;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .notif-content {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      flex: 1;
      min-width: 0;
    }

    .notif-title {
      font-size: 0.8125rem;
      font-weight: 600;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .notif-message {
      font-size: 0.75rem;
      color: var(--color-text-sidebar);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .notif-time {
      font-size: 0.6875rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .unread-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--color-gold);
      flex-shrink: 0;
      margin-top: 6px;
    }

    .empty {
      padding: 2rem 1rem;
      text-align: center;
      color: var(--color-text-sidebar);
      font-size: 0.875rem;
    }
  `],
})
export class NotificationPanelComponent {
  visible = input.required<boolean>();
  @Output() close = new EventEmitter<void>();

  readonly store = inject(NotificationStore);
  private readonly router = inject(Router);

  iconFor(type: AppNotification['type']): string {
    switch (type) {
      case 'document.processed':
        return 'pi pi-file';
      case 'deadline.reminder':
        return 'pi pi-calendar';
      case 'system.alert':
        return 'pi pi-exclamation-triangle';
      default:
        return 'pi pi-info-circle';
    }
  }

  onClick(notification: AppNotification): void {
    if (notification.id) {
      this.store.markRead(notification.id);
    }
    this.close.emit();
    if (notification.link) {
      this.router.navigate([notification.link]);
    }
  }

  markAllRead(): void {
    this.store.markAllRead();
  }
}
