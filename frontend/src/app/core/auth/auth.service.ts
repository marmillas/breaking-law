import { Injectable, computed, signal, WritableSignal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  TokenResponse,
  UserProfile,
  RefreshRequest,
  LogoutRequest,
} from '../../models/auth.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = environment.apiBaseUrl;

  private readonly _tokens: WritableSignal<{ access_token: string; refresh_token: string } | null> =
    signal(null);
  private readonly _user: WritableSignal<UserProfile | null> = signal(null);

  readonly isAuthenticated = computed(() => !!this._tokens());
  readonly user = computed(() => this._user());
  readonly role = computed(() => this._user()?.role ?? null);
  readonly accessToken = computed(() => this._tokens()?.access_token ?? null);

  constructor(private readonly http: HttpClient) {}

  login(email: string, password: string): Observable<TokenResponse> {
    const body = new URLSearchParams();
    body.set('username', email);
    body.set('password', password);

    return this.http
      .post<TokenResponse>(`${this.apiUrl}/auth/login`, body.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .pipe(
        tap((response) => {
          this.setTokens(response);
        })
      );
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = this._tokens()?.refresh_token;
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    const payload: RefreshRequest = { refresh_token: refreshToken };
    return this.http.post<TokenResponse>(`${this.apiUrl}/auth/refresh`, payload);
  }

  logout(): Observable<void> {
    const refreshToken = this._tokens()?.refresh_token;
    if (!refreshToken) {
      this.clearAuth();
      return new Observable<void>((observer) => {
        observer.next();
        observer.complete();
      });
    }
    const payload: LogoutRequest = { refresh_token: refreshToken };
    return this.http.post<void>(`${this.apiUrl}/auth/logout`, payload).pipe(
      tap(() => {
        this.clearAuth();
      })
    );
  }

  getMe(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.apiUrl}/auth/me`).pipe(
      tap((user) => {
        this._user.set(user);
      })
    );
  }

  setTokens(response: TokenResponse): void {
    this._tokens.set({
      access_token: response.access_token,
      refresh_token: response.refresh_token,
    });
  }

  clearAuth(): void {
    this._tokens.set(null);
    this._user.set(null);
  }

  getAccessToken(): string | null {
    return this._tokens()?.access_token ?? null;
  }

  startOAuth(provider: 'google' | 'microsoft'): void {
    window.location.href = `${this.apiUrl}/auth/oauth/${provider}/login`;
  }
}
