import { Routes } from '@angular/router';

export const TIME_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./time-history/time-history.component').then(m => m.TimeHistoryComponent),
    title: 'Tiempo',
  },
  {
    path: 'tracker',
    loadComponent: () => import('./time-tracker/time-tracker.component').then(m => m.TimeTrackerComponent),
    title: 'Registrar tiempo',
  },
];
