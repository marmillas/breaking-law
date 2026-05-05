import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { MainLayoutComponent } from './core/layout/main-layout.component';

export const routes: Routes = [
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
        title: 'Inicio',
      },
      {
        path: 'documents',
        loadChildren: () => import('./features/documents/routes').then(m => m.DOCUMENT_ROUTES),
      },
      {
        path: 'clients',
        loadChildren: () => import('./features/clients/routes').then(m => m.CLIENT_ROUTES),
      },
      {
        path: 'matters',
        loadChildren: () => import('./features/matters/routes').then(m => m.MATTER_ROUTES),
      },
      {
        path: 'time',
        loadChildren: () => import('./features/time/routes').then(m => m.TIME_ROUTES),
      },
      {
        path: 'calendar',
        loadChildren: () => import('./features/calendar/routes').then(m => m.CALENDAR_ROUTES),
      },
      {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent),
        title: 'Configuración',
      },
    ],
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent),
    title: 'Iniciar Sesión',
  },
  {
    path: 'oauth/callback',
    loadComponent: () => import('./features/auth/oauth-callback/oauth-callback.component').then(m => m.OAuthCallbackComponent),
    title: 'Autenticando',
  },
  { path: '**', redirectTo: '' },
];
