import { Component, signal, inject, computed } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from './sidebar.component';
import { ResizeService } from './resize.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [SidebarComponent, RouterOutlet],
  template: `
    <div class="app-layout">
      <app-sidebar [mobileOpen]="mobileSidebarOpen()" (closeMobile)="mobileSidebarOpen.set(false)" />

      <!-- Mobile hamburger -->
      @if (isMobile() && !mobileSidebarOpen()) {
        <button
          class="mobile-menu-btn"
          (click)="mobileSidebarOpen.set(true)"
          aria-label="Abrir menú"
        >
          <i class="pi pi-bars"></i>
        </button>
      }

      <main
        id="main-content"
        class="main-content"
        [class.expanded]="sidebarCollapsed()"
        [class.mobile-open]="mobileSidebarOpen()"
        role="main"
      >
        <router-outlet />
      </main>

      <!-- Mobile overlay -->
      @if (isMobile() && mobileSidebarOpen()) {
        <div class="mobile-overlay" (click)="mobileSidebarOpen.set(false)"></div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .app-layout {
      display: flex;
      flex-direction: row;
      min-height: 100vh;
    }

    .main-content {
      flex: 1;
      margin-left: var(--sidebar-width);
      background-color: var(--color-sepia);
      padding: 2rem;
      min-height: 100vh;
      transition: margin-left var(--transition-normal);
    }

    .main-content.expanded {
      margin-left: var(--sidebar-collapsed-width);
    }

    .main-content.mobile-open {
      margin-left: var(--sidebar-width);
    }

    @media (max-width: 767px) {
      .main-content {
        margin-left: 0;
        padding: 1.25rem;
        padding-top: 3.5rem;
      }
      .main-content.mobile-open {
        margin-left: var(--sidebar-width);
      }
    }

    .mobile-menu-btn {
      position: fixed;
      top: 0.75rem;
      left: 0.75rem;
      z-index: 40;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      color: var(--color-text);
      cursor: pointer;
      font-size: 1.125rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      transition: background-color var(--transition-fast);
    }

    .mobile-menu-btn:hover {
      background-color: var(--color-sepia-dark);
    }

    .mobile-overlay {
      position: fixed;
      inset: 0;
      background-color: rgba(0, 0, 0, 0.4);
      z-index: 45;
    }
  `],
})
export class MainLayoutComponent {
  private readonly resize = inject(ResizeService);

  readonly mobileSidebarOpen = signal(false);
  readonly isMobile = computed(() => this.resize.breakpoint() === 'mobile');
  readonly sidebarCollapsed = computed(() => {
    const bp = this.resize.breakpoint();
    return bp === 'tablet' || bp === 'mobile';
  });
}
