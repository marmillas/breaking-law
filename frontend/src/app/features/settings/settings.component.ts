import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../core/auth/auth.service';
import { ApiService } from '../../core/http/api.service';
import { HasRoleDirective } from '../../core/auth/role.directive';
import { UserProfile, ConnectionOut } from '../../models/auth.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, RouterLink, CardModule, ButtonModule, HasRoleDirective],
  template: `
    <div class="settings-page">
      <h1 class="page-title">Configuración</h1>

      <!-- Perfil -->
      <p-card styleClass="settings-card" header="Perfil">
        <div class="profile-section">
          <div class="avatar">{{ userInitials() }}</div>
          <div class="profile-info">
            <div class="info-row">
              <span class="info-label">Nombre</span>
              <span class="info-value">{{ user()?.full_name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Email</span>
              <span class="info-value">{{ user()?.email }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Rol</span>
              <span class="info-value">{{ user()?.role }}</span>
            </div>
          </div>
        </div>
        <div class="profile-actions">
          <a routerLink="/settings/change-password" class="password-link">Cambiar contraseña</a>
        </div>
      </p-card>

      <!-- Cuentas conectadas -->
      <p-card styleClass="settings-card" header="Cuentas conectadas">
        @if (loading()) {
          <div class="loading">Cargando...</div>
        } @else {
          <div class="connection-list">
            <div class="connection-item">
              <div class="connection-info">
                <i class="pi pi-google connection-icon google"></i>
                <div>
                  <span class="connection-name">Google</span>
                  @if (googleConnection(); as conn) {
                    <span class="connection-status connected">Conectado — {{ conn.email_address }}</span>
                  } @else {
                    <span class="connection-status">No conectado</span>
                  }
                </div>
              </div>
              @if (googleConnection(); as conn) {
                <button
                  pButton
                  type="button"
                  label="Desconectar"
                  class="p-button-outlined p-button-secondary"
                  size="small"
                  (click)="disconnect(conn.id)"
                ></button>
              } @else {
                <button
                  pButton
                  type="button"
                  label="Conectar"
                  class="p-button-outlined"
                  size="small"
                  (click)="connect('google')"
                ></button>
              }
            </div>

            <div class="connection-item">
              <div class="connection-info">
                <i class="pi pi-microsoft connection-icon microsoft"></i>
                <div>
                  <span class="connection-name">Microsoft</span>
                  @if (microsoftConnection(); as conn) {
                    <span class="connection-status connected">Conectado — {{ conn.email_address }}</span>
                  } @else {
                    <span class="connection-status">No conectado</span>
                  }
                </div>
              </div>
              @if (microsoftConnection(); as conn) {
                <button
                  pButton
                  type="button"
                  label="Desconectar"
                  class="p-button-outlined p-button-secondary"
                  size="small"
                  (click)="disconnect(conn.id)"
                ></button>
              } @else {
                <button
                  pButton
                  type="button"
                  label="Conectar"
                  class="p-button-outlined"
                  size="small"
                  (click)="connect('microsoft')"
                ></button>
              }
            </div>
          </div>
        }
      </p-card>

      <!-- Admin -->
      <ng-container *hasRole="'admin'">
        <p-card styleClass="settings-card" header="Administración">
          <div class="admin-actions">
            <button
              pButton
              type="button"
              label="Gestión de usuarios"
              class="p-button-outlined"
              size="small"
              disabled
            ></button>
            <button
              pButton
              type="button"
              label="Políticas de retención"
              class="p-button-outlined"
              size="small"
              disabled
            ></button>
          </div>
        </p-card>
      </ng-container>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .settings-page {
      padding: 1.5rem;
      max-width: 800px;
    }

    .page-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin-bottom: 1.5rem;
    }

    .settings-card {
      margin-bottom: 1.5rem;
    }

    .settings-card ::ng-deep .p-card-header {
      padding: 1rem 1.25rem 0;
      font-family: var(--font-heading);
      font-weight: 600;
      font-size: 1.125rem;
      color: var(--color-text);
    }

    .settings-card ::ng-deep .p-card-body {
      padding: 1.25rem;
    }

    .profile-section {
      display: flex;
      align-items: center;
      gap: 1.25rem;
      margin-bottom: 1rem;
    }

    .avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 64px;
      height: 64px;
      background-color: var(--color-gold);
      color: var(--color-sidebar);
      font-weight: 700;
      font-size: 1.5rem;
      border-radius: 50%;
      flex-shrink: 0;
      text-transform: uppercase;
    }

    .profile-info {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex: 1;
    }

    .info-row {
      display: flex;
      align-items: baseline;
      gap: 0.75rem;
    }

    .info-label {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-secondary);
      min-width: 60px;
    }

    .info-value {
      font-size: 0.9375rem;
      color: var(--color-text);
    }

    .profile-actions {
      margin-top: 0.5rem;
    }

    .password-link {
      font-size: 0.875rem;
      color: var(--color-gold);
      text-decoration: none;
      transition: opacity var(--transition-fast);
    }

    .password-link:hover {
      opacity: 0.8;
      text-decoration: underline;
    }

    .loading {
      padding: 1rem;
      text-align: center;
      color: var(--color-text-secondary);
    }

    .connection-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .connection-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.75rem;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
    }

    .connection-info {
      display: flex;
      align-items: center;
      gap: 0.875rem;
    }

    .connection-icon {
      font-size: 1.5rem;
      width: 40px;
      text-align: center;
    }

    .connection-icon.google {
      color: #db4437;
    }

    .connection-icon.microsoft {
      color: #0078d4;
    }

    .connection-name {
      display: block;
      font-weight: 600;
      font-size: 0.9375rem;
      color: var(--color-text);
    }

    .connection-status {
      display: block;
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
    }

    .connection-status.connected {
      color: var(--green-500);
    }

    .admin-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }
  `],
})
export class SettingsComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly api = inject(ApiService);

  readonly user = signal<UserProfile | null>(null);
  readonly connections = signal<ConnectionOut[]>([]);
  readonly loading = signal(false);

  readonly userInitials = computed(() => {
    const name = this.user()?.full_name ?? '';
    const parts = name.split(' ').filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  });

  readonly googleConnection = computed(() =>
    this.connections().find(c => c.provider === 'google') ?? null
  );

  readonly microsoftConnection = computed(() =>
    this.connections().find(c => c.provider === 'microsoft') ?? null
  );

  ngOnInit(): void {
    this.user.set(this.authService.user());
    this.loadConnections();
  }

  loadConnections(): void {
    this.loading.set(true);
    this.api.get<ConnectionOut[]>('/oauth/connections').subscribe({
      next: (data) => {
        this.connections.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  connect(provider: 'google' | 'microsoft'): void {
    window.location.href = `${environment.apiBaseUrl}/oauth/${provider}/authorize`;
  }

  disconnect(connectionId: string): void {
    this.api.delete<void>(`/oauth/connections/${connectionId}`).subscribe({
      next: () => {
        this.connections.update(list => list.filter(c => c.id !== connectionId));
      }
    });
  }
}
