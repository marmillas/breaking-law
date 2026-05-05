export interface MatterOut {
  id: string;
  law_firm_id: string;
  client_id: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MatterCreate {
  client_id: string;
  title: string;
  description?: string;
  status?: string;
}

export interface MatterUpdate {
  client_id?: string;
  title?: string;
  description?: string;
  status?: string;
}
