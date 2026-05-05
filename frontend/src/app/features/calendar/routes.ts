import { Routes } from '@angular/router';

export const CALENDAR_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./deadline-calendar/deadline-calendar.component').then(m => m.DeadlineCalendarComponent),
    title: 'Calendario',
  },
];
