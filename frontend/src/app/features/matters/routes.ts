import { Routes } from '@angular/router';

export const MATTER_ROUTES: Routes = [
  {
    path: ':id',
    loadComponent: () => import('./matter-detail/matter-detail.component').then((m) => m.MatterDetailComponent),
    title: 'Expediente',
  },
];
