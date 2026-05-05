import { Component, input, signal, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NgIf } from '@angular/common';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, NgIf],
  template: `
    <aside class="sidebar" [class.collapsed]="collapsed()">
      <!-- Logo area -->
      <div class="sidebar-logo">
        <span class="logo-text">BL</span>
        <span class="logo-full" *ngIf="!collapsed()">Breaking Law</span>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact:true}" class="nav-item">
          <i class="pi pi-home"></i>
          <span *ngIf="!collapsed()">Inicio</span>
        </a>
        <a routerLink="/documents" routerLinkActive="active" class="nav-item">
          <i class="pi pi-file"></i>
          <span *ngIf="!collapsed()">Documentos</span>
        </a>
        <a routerLink="/clients" routerLinkActive="active" class="nav-item">
          <i class="pi pi-users"></i>
          <span *ngIf="!collapsed()">Clientes</span>
        </a>
        <a routerLink="/calendar" routerLinkActive="active" class="nav-item">
          <i class="pi pi-calendar"></i>
          <span *ngIf="!collapsed()">Calendario</span>
        </a>
        <a routerLink="/time" routerLinkActive="active" class="nav-item">
          <i class="pi pi-clock"></i>
          <span *ngIf="!collapsed()">Tiempo</span>
        </a>
        <a routerLink="/settings" routerLinkActive="active" class="nav-item">
          <i class="pi pi-cog"></i>
          <span *ngIf="!collapsed()">Configuración</span>
        </a>
      </nav>

      <!-- Notification bell -->
      <div class="sidebar-notifications">
        <button class="notification-bell" (click)="toggleNotifications()" title="Notificaciones">
          <i class="pi pi-bell"></i>
          <span class="badge" *ngIf="unreadCount() > 0">{{ unreadCount() }}</span>
        </button>
      </div>

      <!-- User info at bottom -->
      <div class="sidebar-user">
        <div class="user-avatar">{{ userInitials() }}</div>
        <div class="user-info" *ngIf="!collapsed()">
          <span class="user-name">{{ userName() }}</span>
          <span class="user-role">{{ userRole() }}</span>
        </div>
        <button class="logout-btn" (click)="logout()" title="Cerrar sesión">
          <i class="pi pi-sign-out"></i>
        </button>
      </div>
    </aside>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sidebar {
      position: fixed;
      left: 0;
      top: 0;
      height: 100vh;
      width: var(--sidebar-width);
      background-color: var(--color-sidebar);
      display: flex;
      flex-direction: column;
      transition: width var(--transition-normal);
      z-index: 50;
    }

    .sidebar.collapsed {
      width: var(--sidebar-collapsed-width);
    }

    .sidebar-logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1.25rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .logo-text {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background-color: var(--color-gold);
      color: var(--color-sidebar);
      font-family: var(--font-heading);
      font-weight: 700;
      font-size: 1rem;
      border-radius: 6px;
      flex-shrink: 0;
    }

    .logo-full {
      font-family: var(--font-heading);
      font-weight: 700;
      font-size: 1.125rem;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
    }

    .sidebar-nav {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 0.75rem 0.5rem;
      gap: 0.25rem;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.875rem;
      padding: 0.625rem 0.875rem;
      border-radius: 6px;
      color: var(--color-text-sidebar);
      text-decoration: none;
      font-size: 0.9375rem;
      transition: background-color var(--transition-fast), color var(--transition-fast);
      border-left: 3px solid transparent;
    }

    .nav-item:hover {
      background-color: var(--color-sidebar-hover);
      color: #ffffff;
    }

    .nav-item.active {
      background-color: var(--color-sidebar-active);
      color: var(--color-text-sidebar-active);
      border-left-color: var(--color-gold);
    }

    .nav-item i {
      font-size: 1.125rem;
      width: 20px;
      text-align: center;
      flex-shrink: 0;
    }

    .nav-item span {
      white-space: nowrap;
      overflow: hidden;
    }

    .sidebar-notifications {
      padding: 0.75rem 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .notification-bell {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: transparent;
      border: none;
      border-radius: 6px;
      color: var(--color-text-sidebar);
      cursor: pointer;
      font-size: 1.125rem;
      transition: background-color var(--transition-fast), color var(--transition-fast);
    }

    .notification-bell:hover {
      background-color: var(--color-sidebar-hover);
      color: #ffffff;
    }

    .badge {
      position: absolute;
      top: 4px;
      right: 4px;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      background-color: var(--color-critical);
      color: #ffffff;
      font-size: 0.6875rem;
      font-weight: 600;
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .sidebar-user {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .user-avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background-color: var(--color-gold);
      color: var(--color-sidebar);
      font-weight: 700;
      font-size: 0.875rem;
      border-radius: 50%;
      flex-shrink: 0;
      text-transform: uppercase;
    }

    .user-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
      overflow: hidden;
    }

    .user-name {
      font-size: 0.875rem;
      font-weight: 500;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 0.75rem;
      color: var(--color-text-sidebar);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .logout-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      background: transparent;
      border: none;
      border-radius: 6px;
      color: var(--color-text-sidebar);
      cursor: pointer;
      font-size: 1rem;
      flex-shrink: 0;
      transition: background-color var(--transition-fast), color var(--transition-fast);
    }

    .logout-btn:hover {
      background-color: var(--color-sidebar-hover);
      color: #ffffff;
    }
  `],
})
export class SidebarComponent {
  collapsed = input<boolean>(false);

  private readonly authService = inject(AuthService);

  readonly userName = computed(() => this.authService.user()?.full_name ?? this.authService.user()?.email ?? 'Usuario');
  readonly userRole = computed(() => this.authService.user()?.role ?? '');
  readonly userInitials = computed(() => {
    const name = this.userName();
    const parts = name.split(' ').filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  });

  // Placeholder: will wire to NotificationStore in Batch 7
  readonly unreadCount = signal(0);

  toggleNotifications(): void {
    // Placeholder for notification panel toggle
  }

  logout(): void {
    this.authService.logout().subscribe();
  }
}
