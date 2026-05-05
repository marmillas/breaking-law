export interface NotificationOut {
  id: string;
  law_firm_id: string;
  user_id: string;
  deadline_id: string | null;
  title: string;
  message: string;
  priority: string;
  read: boolean;
  created_at: string;
}

export interface MarkReadResponse {
  message: string;
}

export interface MarkAllReadResponse {
  marked_count: number;
}

export interface AppNotification extends Partial<NotificationOut> {
  type: 'document.processed' | 'deadline.reminder' | 'system.alert';
  link?: string;
}
