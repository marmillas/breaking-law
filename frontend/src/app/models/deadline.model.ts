export interface Deadline {
  id: string;
  law_firm_id: string;
  matter_id: string | null;
  created_by: string;
  title: string;
  description: string | null;
  due_date: string;
  priority: string;
  status: string;
  notification_sent_at: string | null;
  acknowledged_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeadlineCreate {
  title: string;
  description?: string;
  due_date: string;
  priority?: string;
  matter_id?: string;
}
