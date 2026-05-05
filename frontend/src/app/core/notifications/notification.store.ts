import { Injectable, computed, signal } from '@angular/core';
import { ApiService } from '../http/api.service';
import { AppNotification } from '../../models/notification.model';

@Injectable({ providedIn: 'root' })
export class NotificationStore {
  private readonly MAX_NOTIFICATIONS = 50;

  readonly notifications = signal<AppNotification[]>([]);
  readonly unreadCount = computed(() => this.notifications().filter(n => !n.read).length);

  constructor(private api: ApiService) {}

  add(notification: AppNotification): void {
    this.notifications.update(list => {
      const updated = [notification, ...list];
      if (updated.length > this.MAX_NOTIFICATIONS) {
        updated.length = this.MAX_NOTIFICATIONS;
      }
      return updated;
    });
  }

  markRead(id: string): void {
    this.notifications.update(list =>
      list.map(n => n.id === id ? { ...n, read: true } : n)
    );
    // Sync to backend
    this.api.post(`/notifications/${id}/read`, {}).subscribe();
  }

  markAllRead(): void {
    this.notifications.update(list =>
      list.map(n => ({ ...n, read: true }))
    );
    // Sync to backend if endpoint exists
    this.api.post('/notifications/read-all', {}).subscribe();
  }

  loadFromServer(): void {
    this.api.get<any[]>('/notifications/', { limit: 50 }).subscribe({
      next: (data) => {
        const mapped: AppNotification[] = (Array.isArray(data) ? data : (data as any).items || []).map((n: any) => ({
          id: n.id,
          type: n.type || 'system.alert',
          title: n.title,
          message: n.message,
          link: n.link || (n.document_id ? `/documents/${n.document_id}` : undefined),
          read: n.read || false,
          created_at: n.created_at,
          priority: n.priority
        }));
        this.notifications.set(mapped);
      }
    });
  }
}
