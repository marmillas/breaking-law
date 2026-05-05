import { Routes } from '@angular/router';

export const DOCUMENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./document-list/document-list.component').then(m => m.DocumentListComponent),
    title: 'Documentos',
  },
  {
    path: 'upload',
    loadComponent: () => import('./document-upload/document-upload.component').then(m => m.DocumentUploadComponent),
    title: 'Subir documento',
  },
  {
    path: ':id',
    loadComponent: () => import('./document-detail/document-detail.component').then(m => m.DocumentDetailComponent),
    title: 'Documento',
  },
  {
    path: ':id/edit',
    loadComponent: () => import('./document-editor/document-editor.component').then(m => m.DocumentEditorComponent),
    title: 'Editor',
  },
];
