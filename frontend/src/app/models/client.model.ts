export interface ClientOut {
  id: string;
  law_firm_id: string;
  name: string;
  email: string;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientCreate {
  name: string;
  email: string;
  phone?: string;
}

export interface ClientUpdate {
  name?: string;
  email?: string;
  phone?: string;
}
