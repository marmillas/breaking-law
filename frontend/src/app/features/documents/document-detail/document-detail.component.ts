import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { AccordionModule } from 'primeng/accordion';
import { PanelModule } from 'primeng/panel';

import { DocumentService } from '../document.service';
import { DocumentOut, DocumentVersion } from '../../../models/document.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { DateEsPipe } from '../../../shared/pipes/date-es.pipe';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { ToastService } from '../../../core/http/toast.service';
import { ScrollProgressDirective } from '../../../shared/directives/scroll-progress.directive';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ButtonModule,
    TagModule,
    CardModule,
    AccordionModule,
    PanelModule,
    StatusBadgeComponent,
    DateEsPipe,
    SkeletonLoaderComponent,
    EmptyStateComponent,
    ConfirmDialogComponent,
    ScrollProgressDirective,
  ],
  template: `
    <div class="page-container">
      <div appScrollProgress class="scroll-progress-bar"></div>

      @if (loading()) {
        <app-skeleton-loader variant="card" [count]="3"></app-skeleton-loader>
      } @else if (notFound()) {
        <app-empty-state
          icon="pi pi-file-excel"
          title="Documento no encontrado"
          message="El documento solicitado no existe o fue eliminado."
          actionLabel="Volver a documentos"
          (action)="goBack()"
        ></app-empty-state>
      } @else {
        <div class="detail-layout">
          <!-- Metadata Card -->
          <div class="metadata-section">
            <div class="doc-header">
              <h1 class="doc-title">{{ document()?.title }}</h1>
              <div class="doc-badges">
                @if (document()?.classification) {
                  <p-tag [value]="document()!.classification ?? ''" severity="secondary"></p-tag>
                }
                <app-status-badge [status]="docStatus()"></app-status-badge>
                @if (document()?.is_confidential) {
                  <p-tag value="Confidencial" severity="warning"></p-tag>
                }
              </div>
            </div>

            <div class="metadata-grid">
              <div class="meta-item">
                <span class="meta-label">Cliente</span>
                <span class="meta-value">—</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Expediente</span>
                @if (document()?.matter_id) {
                  <a [routerLink]="['/matters', document()!.matter_id]" class="meta-link">
                    {{ document()!.matter_id }}
                  </a>
                } @else {
                  <span class="meta-value muted">—</span>
                }
              </div>
              <div class="meta-item">
                <span class="meta-label">Creado</span>
                <span class="meta-value">{{ document()?.created_at | dateEs:'long' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Actualizado</span>
                <span class="meta-value">{{ document()?.updated_at | dateEs:'long' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Versiones</span>
                <span class="meta-value">{{ document()?.versions?.length ?? 0 }}</span>
              </div>
            </div>

            <div class="actions-bar">
              <button
                pButton
                type="button"
                label="Editar"
                icon="pi pi-pencil"
                class="p-button-outlined"
                [routerLink]="['/documents', document()?.id, 'edit']"
              ></button>
              <button
                pButton
                type="button"
                label="Descargar"
                icon="pi pi-download"
                class="p-button-outlined"
                (click)="download()"
                [loading]="downloading()"
              ></button>
              <button
                pButton
                type="button"
                label="Eliminar"
                icon="pi pi-trash"
                class="p-button-danger p-button-outlined"
                (click)="showDeleteDialog.set(true)"
              ></button>
            </div>
          </div>

          <!-- Preview -->
          <div class="preview-section">
            <div class="section-header">
              <h2 class="section-title">Vista previa</h2>
            </div>
            <div class="preview-area">
              @if (latestVersion()?.mime_type === 'application/pdf') {
                @if (downloadUrl()) {
                  <iframe [src]="downloadUrl()" class="preview-frame"></iframe>
                } @else {
                  <div class="preview-placeholder">
                    <i class="pi pi-file-pdf"></i>
                    <p>PDF disponible para descarga</p>
                  </div>
                }
              } @else if (latestVersion()?.mime_type?.startsWith('text/')) {
                <div class="text-preview">
                  <p>Contenido de texto no disponible en vista previa.</p>
                </div>
              } @else {
                <div class="preview-placeholder">
                  <i class="pi pi-image"></i>
                  <p>Vista previa no disponible para este formato</p>
                </div>
              }
            </div>
          </div>

          <!-- Version History -->
          @if (versions().length > 0) {
            <div class="versions-section">
              <div class="section-header">
                <h2 class="section-title">Historial de versiones</h2>
              </div>
              <p-accordion [multiple]="true">
                @for (version of versions(); track version.id) {
                  <p-accordionTab [header]="'Versión ' + version.version_number + ' — ' + (version.created_at | dateEs:'short')">
                    <div class="version-details">
                      <div class="version-meta">
                        <span><strong>Estado:</strong> {{ version.parser_status }}</span>
                        <span><strong>Tipo:</strong> {{ version.mime_type }}</span>
                        <span><strong>Tamaño:</strong> {{ formatBytes(version.size_bytes) }}</span>
                        <span><strong>Hash:</strong> <code>{{ version.sha256_hash.slice(0, 16) }}...</code></span>
                      </div>
                    </div>
                  </p-accordionTab>
                }
              </p-accordion>
            </div>
          }
        </div>
      }
    </div>

    <app-confirm-dialog
      [visible]="showDeleteDialog()"
      title="Eliminar documento"
      [message]="deleteMessage()"
      confirmLabel="Eliminar"
      severity="danger"
      (confirm)="onDeleteConfirm()"
      (cancel)="showDeleteDialog.set(false)"
    ></app-confirm-dialog>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
      position: relative;
    }

    .scroll-progress-bar {
      position: fixed;
      top: 0;
      left: var(--sidebar-width);
      right: 0;
      height: 3px;
      background-color: var(--color-gold);
      transform-origin: left;
      transform: scaleX(var(--scroll-progress, 0));
      z-index: 30;
      transition: transform 100ms linear;
    }

    @media (max-width: 767px) {
      .scroll-progress-bar {
        left: 0;
      }
    }

    .detail-layout {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      max-width: 960px;
    }

    .metadata-section {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
    }

    .doc-header {
      margin-bottom: 1rem;
    }

    .doc-title {
      font-family: var(--font-heading);
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0 0 0.5rem;
    }

    .doc-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1.25rem;
    }

    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .meta-label {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.025em;
      color: var(--color-text-secondary);
    }

    .meta-value {
      font-size: 0.9375rem;
      color: var(--color-text);
    }

    .meta-value.muted {
      color: var(--color-text-secondary);
    }

    .meta-link {
      color: var(--color-review);
      text-decoration: none;
      font-size: 0.9375rem;
    }

    .meta-link:hover {
      text-decoration: underline;
    }

    .actions-bar {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .preview-section {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
    }

    .section-header {
      margin-bottom: 1rem;
    }

    .section-title {
      font-family: var(--font-heading);
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }

    .preview-area {
      min-height: 400px;
      border: 1px solid var(--color-border);
      border-radius: 6px;
      overflow: hidden;
      background-color: var(--color-sepia-light);
    }

    .preview-frame {
      width: 100%;
      height: 500px;
      border: none;
    }

    .preview-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 300px;
      color: var(--color-text-secondary);
      gap: 0.5rem;
    }

    .preview-placeholder i {
      font-size: 2.5rem;
      color: var(--color-gold);
      opacity: 0.6;
    }

    .text-preview {
      padding: 1.5rem;
      font-family: monospace;
      font-size: 0.875rem;
      color: var(--color-text);
      white-space: pre-wrap;
    }

    .versions-section {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
    }

    .version-details {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .version-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      font-size: 0.875rem;
      color: var(--color-text);
    }

    .version-meta code {
      background-color: var(--color-sepia-light);
      padding: 0.125rem 0.375rem;
      border-radius: 4px;
      font-size: 0.8125rem;
    }
  `],
})
export class DocumentDetailComponent implements OnInit {
  private readonly documentService = inject(DocumentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly document = signal<DocumentOut | null>(null);
  readonly loading = signal(true);
  readonly notFound = signal(false);
  readonly downloading = signal(false);
  readonly showDeleteDialog = signal(false);
  readonly downloadUrl = signal<string | null>(null);
  readonly versions = signal<DocumentVersion[]>([]);

  readonly deleteMessage = computed(() => {
    const title = this.document()?.title ?? '';
    return `¿Está seguro de que desea eliminar "${title}"?`;
  });

  readonly docStatus = signal<string>('pending');
  readonly latestVersion = signal<DocumentVersion | null>(null);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.notFound.set(true);
      this.loading.set(false);
      return;
    }
    this.loadDocument(id);
  }

  loadDocument(id: string): void {
    this.loading.set(true);
    this.notFound.set(false);

    this.documentService.get(id).subscribe({
      next: (doc) => {
        this.document.set(doc);
        this.versions.set(doc.versions ?? []);

        const version = doc.versions?.[doc.versions.length - 1] ?? null;
        this.latestVersion.set(version);

        if (version) {
          if (version.parser_status === 'ready') this.docStatus.set('ready');
          else if (version.parser_status === 'processing') this.docStatus.set('review');
          else if (version.parser_status === 'failed') this.docStatus.set('critical');
          else this.docStatus.set('pending');
        }

        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        if (err.status === 404) {
          this.notFound.set(true);
        } else {
          this.toast.error('Error al cargar el documento');
          this.notFound.set(true);
        }
      },
    });
  }

  download(): void {
    const id = this.document()?.id;
    if (!id) return;

    this.downloading.set(true);
    this.documentService.download(id).subscribe({
      next: (blob) => {
        this.downloading.set(false);
        const url = window.URL.createObjectURL(blob);
        this.downloadUrl.set(url);

        // Trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = this.document()?.title ?? 'documento';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      },
      error: () => {
        this.downloading.set(false);
        this.toast.error('Error al descargar el documento');
      },
    });
  }

  onDeleteConfirm(): void {
    const id = this.document()?.id;
    if (!id) return;

    this.showDeleteDialog.set(false);
    this.documentService.delete(id).subscribe({
      next: () => {
        this.toast.success('Documento eliminado');
        this.router.navigate(['/documents']);
      },
      error: () => {
        this.toast.error('Error al eliminar el documento');
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/documents']);
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
