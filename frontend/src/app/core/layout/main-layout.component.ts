import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from './sidebar.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [SidebarComponent, RouterOutlet],
  template: `
    <div class="app-layout">
      <app-sidebar [collapsed]="sidebarCollapsed()" />
      <main class="main-content" [class.expanded]="sidebarCollapsed()">
        <router-outlet />
      </main>
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
  `],
})
export class MainLayoutComponent {
  sidebarCollapsed = signal(false);
}
