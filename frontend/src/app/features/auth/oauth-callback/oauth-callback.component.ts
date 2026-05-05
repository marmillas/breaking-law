import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../../core/auth/auth.service';
import { environment } from '../../../../environments/environment';
import { TokenResponse } from '../../../models/auth.model';

@Component({
  selector: 'app-oauth-callback',
  standalone: true,
  imports: [CommonModule, ProgressSpinnerModule, ButtonModule],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-sepia-100 px-4">
      <div class="text-center">
        @if (!error()) {
          <p-progressSpinner
            styleClass="w-12 h-12 mb-4"
            strokeWidth="4"
          ></p-progressSpinner>
          <p class="text-lg font-medium text-gray-800">Autenticando...</p>
        } @else {
          <div class="space-y-4">
            <p class="text-lg font-medium text-red-700">{{ error() }}</p>
            <button
              pButton
              type="button"
              label="Intentar nuevamente"
              class="bg-gold-500 hover:bg-gold-600 text-gray-900 font-semibold"
              (click)="retry()"
            ></button>
          </div>
        }
      </div>
    </div>
  `,
})
export class OAuthCallbackComponent implements OnInit {
  error = signal<string | null>(null);

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    const code = this.route.snapshot.queryParamMap.get('code');
    const state = this.route.snapshot.queryParamMap.get('state');

    if (!code || !state) {
      this.error.set('Error al iniciar sesión. Parámetros faltantes.');
      return;
    }

    this.exchangeCode(code, state);
  }

  private exchangeCode(code: string, state: string): void {
    this.http
      .post<TokenResponse>(`${environment.apiBaseUrl}/auth/oauth/callback`, { code, state })
      .subscribe({
        next: (response) => {
          this.authService.setTokens(response);
          this.authService.getMe().subscribe({
            next: () => {
              this.router.navigate(['/dashboard']);
            },
            error: () => {
              this.error.set('Error al cargar el perfil. Intente nuevamente.');
            },
          });
        },
        error: () => {
          this.error.set('Error al iniciar sesión. Intente nuevamente.');
        },
      });
  }

  retry(): void {
    this.error.set(null);
    this.router.navigate(['/login']);
  }
}
