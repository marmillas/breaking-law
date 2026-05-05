export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  law_firm_id: string;
  is_active: boolean;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface LawFirm {
  id: string;
  name: string;
  timezone: string;
}

export interface ConnectionOut {
  id: string;
  provider: string;
  email_address: string;
  scopes: string;
  connected_at: string;
  last_synced_at: string | null;
}
