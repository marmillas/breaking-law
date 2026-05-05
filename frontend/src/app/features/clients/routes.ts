import { Routes } from '@angular/router';

export const CLIENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./client-list/client-list.component').then((m) => m.ClientListComponent),
    title: 'Clientes',
  },
  {
    path: ':id',
    loadComponent: () => import('./client-detail/client-detail.component').then((m) => m.ClientDetailComponent),
    title: 'Cliente',
  },
];
