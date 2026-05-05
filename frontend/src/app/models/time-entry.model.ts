export interface TimeEntry {
  id: string;
  law_firm_id: string;
  user_id: string;
  matter_id: string | null;
  client_id: string | null;
  description: string | null;
  started_at: string;
  ended_at: string | null;
  duration_minutes: number | null;
  billable: boolean;
  billing_rate: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StartTimerRequest {
  matter_id?: string;
  client_id?: string;
  description?: string;
}

export interface ReportOut {
  total_hours: number;
  billable_hours: number;
  total_entries: number;
  matter_breakdown: Record<string, number>;
}
