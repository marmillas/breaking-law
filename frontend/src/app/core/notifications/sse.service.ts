import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { NotificationStore } from './notification.store';

@Injectable({ providedIn: 'root' })
export class SseService {
  private eventSource: EventSource | null = null;
  private reconnectTimeout: any = null;
  private retryAttempt = 0;
  private readonly MAX_RETRY_DELAY = 30000;

  readonly connectionState = signal<'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed'>('disconnected');
  readonly retryCount = signal(0);

  constructor(
    private authService: AuthService,
    private notificationStore: NotificationStore
  ) {}

  connect(token: string): void {
    this.disconnect();
    this.connectionState.set('connecting');

    const url = `${environment.sseBaseUrl}/api/notifications/stream?token=${encodeURIComponent(token)}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.connectionState.set('connected');
      this.retryAttempt = 0;
      this.retryCount.set(0);
    };

    this.eventSource.addEventListener('document.processed', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      this.notificationStore.add({ type: 'document.processed', ...data, read: false });
    });

    this.eventSource.addEventListener('deadline.reminder', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      this.notificationStore.add({ type: 'deadline.reminder', ...data, read: false });
    });

    this.eventSource.addEventListener('system.alert', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      this.notificationStore.add({ type: 'system.alert', ...data, read: false });
    });

    this.eventSource.addEventListener('heartbeat', () => {
      // Keepalive — no action needed
    });

    this.eventSource.onerror = () => {
      this.connectionState.set('reconnecting');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    this.disconnect();
    const delay = Math.min(1000 * Math.pow(2, this.retryAttempt), this.MAX_RETRY_DELAY);
    this.retryAttempt++;
    this.retryCount.set(this.retryAttempt);

    this.reconnectTimeout = setTimeout(() => {
      const token = this.authService.getAccessToken();
      if (token) {
        this.connect(token);
      } else {
        this.connectionState.set('failed');
      }
    }, delay);
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.connectionState.set('disconnected');
  }
}
