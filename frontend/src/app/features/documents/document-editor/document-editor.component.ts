import { Component, OnInit, OnDestroy, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, debounceTime, takeUntil } from 'rxjs';

import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { PanelModule } from 'primeng/panel';
import { DividerModule } from 'primeng/divider';

import { DocumentService } from '../document.service';
import { DraftOut } from '../../../models/document.model';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { ToastService } from '../../../core/http/toast.service';
import { SkeletonLoaderComponent } from '../../../shared/components/skeleton-loader/skeleton-loader.component';

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface AISuggestion {
  id: string;
  text: string;
  accepted: boolean;
}

@Component({
  selector: 'app-document-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    PanelModule,
    DividerModule,
    ConfirmDialogComponent,
    SkeletonLoaderComponent,
  ],
  template: `
    <div class="editor-page">
      @if (loading()) {
        <app-skeleton-loader variant="card" [count]="2"></app-skeleton-loader>
      } @else {
        <!-- Toolbar -->
        <div class="editor-toolbar">
          <div class="toolbar-group">
            <button
              pButton
              type="button"
              icon="pi pi-bold"
              class="p-button-text p-button-sm"
              (click)="format('bold')"
              title="Negrita"
            ></button>
            <button
              pButton
              type="button"
              icon="pi pi-italic"
              class="p-button-text p-button-sm"
              (click)="format('italic')"
              title="Cursiva"
            ></button>
            <button
              pButton
              type="button"
              icon="pi pi-underline"
              class="p-button-text p-button-sm"
              (click)="format('underline')"
              title="Subrayado"
            ></button>
            <div class="toolbar-divider"></div>
            <button
              pButton
              type="button"
              icon="pi pi-heading"
              class="p-button-text p-button-sm"
              (click)="formatBlock('h2')"
              title="Título"
            ></button>
            <button
              pButton
              type="button"
              icon="pi pi-list"
              class="p-button-text p-button-sm"
              (click)="format('insertUnorderedList')"
              title="Lista"
            ></button>
          </div>

          <div class="toolbar-group">
            <span class="save-state" [class]="saveState()">
              @if (saveState() === 'saving') {
                <i class="pi pi-spin pi-spinner"></i> Guardando...
              } @else if (saveState() === 'saved') {
                <i class="pi pi-check"></i> Guardado
              } @else if (saveState() === 'error') {
                <i class="pi pi-exclamation-circle"></i> Error al guardar
              } @else {
                <i class="pi pi-pencil"></i> Listo
              }
            </span>
            <button
              pButton
              type="button"
              label="Guardar"
              icon="pi pi-save"
              class="p-button-sm p-button-warning"
              (click)="saveNow()"
              [disabled]="saveState() === 'saving' || !dirty()"
            ></button>
            <button
              pButton
              type="button"
              label="Cerrar"
              icon="pi pi-times"
              class="p-button-sm p-button-text"
              (click)="onClose()"
            ></button>
          </div>
        </div>

        <!-- Main Editor -->
        <div class="editor-layout">
          <div class="editor-main" [class.with-sidebar]="showSuggestions()">
            <div class="editor-paper">
              <div
                #editorRef
                class="editor-content"
                contenteditable="true"
                [innerHTML]="content()"
                (input)="onEditorInput($event)"
                (keydown)="onKeyDown($event)"
              ></div>
            </div>
          </div>

          <!-- AI Sidebar -->
          @if (showSuggestions()) {
            <div class="editor-sidebar">
              <div class="sidebar-header">
                <h3>Sugerencias de IA</h3>
                <button
                  pButton
                  type="button"
                  icon="pi pi-times"
                  class="p-button-text p-button-sm"
                  (click)="showSuggestions.set(false)"
                ></button>
              </div>

              <div class="rag-query">
                <input
                  pInputText
                  type="text"
                  placeholder="Consultar a la IA..."
                  [(ngModel)]="ragQueryText"
                  class="w-full"
                  (keyup.enter)="queryRag()"
                />
                <button
                  pButton
                  type="button"
                  icon="pi pi-send"
                  class="p-button-sm p-button-warning"
                  (click)="queryRag()"
                  [loading]="ragLoading()"
                ></button>
              </div>

              <div class="suggestions-list">
                @if (aiSuggestions().length === 0) {
                  <div class="empty-suggestions">
                    <i class="pi pi-sparkles"></i>
                    <p>Consultá a la IA para obtener sugerencias sobre el documento.</p>
                  </div>
                } @else {
                  @for (suggestion of aiSuggestions(); track suggestion.id) {
                    <div class="suggestion-card" [class.accepted]="suggestion.accepted">
                      <p class="suggestion-text">{{ suggestion.text }}</p>
                      <div class="suggestion-actions">
                        <button
                          pButton
                          type="button"
                          icon="pi pi-check"
                          class="p-button-sm p-button-success"
                          (click)="acceptSuggestion(suggestion)"
                          [disabled]="suggestion.accepted"
                        ></button>
                        <button
                          pButton
                          type="button"
                          icon="pi pi-times"
                          class="p-button-sm p-button-text p-button-danger"
                          (click)="dismissSuggestion(suggestion)"
                        ></button>
                      </div>
                    </div>
                  }
                }
              </div>
            </div>
          } @else {
            <button
              pButton
              type="button"
              icon="pi pi-sparkles"
              class="p-button-rounded p-button-warning ai-toggle"
              (click)="showSuggestions.set(true)"
              title="Sugerencias de IA"
            ></button>
          }
        </div>
      }
    </div>

    <app-confirm-dialog
      [visible]="showDiscardDialog()"
      title="Descartar cambios"
      message="¿Descartar cambios sin guardar?"
      confirmLabel="Descartar"
      severity="warning"
      (confirm)="confirmDiscard()"
      (cancel)="showDiscardDialog.set(false)"
    ></app-confirm-dialog>
  `,
  styles: [`
    .editor-page {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 64px);
      background-color: var(--color-sepia-light);
    }

    .editor-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 1rem;
      background-color: var(--color-surface);
      border-bottom: 1px solid var(--color-border);
      flex-shrink: 0;
    }

    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .toolbar-divider {
      width: 1px;
      height: 1.25rem;
      background-color: var(--color-border);
      margin: 0 0.25rem;
    }

    .save-state {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
      margin-right: 0.75rem;
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
    }

    .save-state.saving {
      color: var(--color-pending);
    }

    .save-state.saved {
      color: var(--color-ready);
    }

    .save-state.error {
      color: var(--color-critical);
    }

    .editor-layout {
      display: flex;
      flex: 1;
      overflow: hidden;
      position: relative;
    }

    @media (max-width: 1023px) {
      .editor-layout {
        flex-direction: column;
        overflow-y: auto;
      }
    }

    .editor-main {
      flex: 1;
      overflow-y: auto;
      padding: 2rem;
    }

    .editor-main.with-sidebar {
      padding-right: 1rem;
    }

    @media (max-width: 1023px) {
      .editor-main {
        overflow-y: visible;
        padding: 1rem;
      }
      .editor-main.with-sidebar {
        padding-right: 1rem;
      }
    }

    .editor-paper {
      max-width: 816px;
      min-height: 1056px;
      margin: 0 auto;
      background-color: var(--color-surface);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-radius: 4px;
      padding: 3rem 2.5rem;
    }

    .editor-content {
      min-height: 800px;
      font-family: var(--font-family);
      font-size: 1rem;
      line-height: 1.7;
      color: var(--color-text);
      outline: none;
    }

    .editor-content :is(h1, h2, h3, h4, h5, h6) {
      font-family: var(--font-heading);
      margin-top: 1.5rem;
      margin-bottom: 0.75rem;
    }

    .editor-content p {
      margin-bottom: 0.75rem;
    }

    .editor-content ul, .editor-content ol {
      margin-bottom: 0.75rem;
      padding-left: 1.5rem;
    }

    .editor-content blockquote {
      border-left: 3px solid var(--color-gold);
      padding-left: 1rem;
      margin-left: 0;
      color: var(--color-text-secondary);
      font-style: italic;
    }

    .ai-toggle {
      position: absolute;
      right: 1rem;
      top: 1rem;
      z-index: 10;
    }

    .editor-sidebar {
      width: 320px;
      flex-shrink: 0;
      background-color: var(--color-surface);
      border-left: 1px solid var(--color-border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .sidebar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-bottom: 1px solid var(--color-border);
    }

    .sidebar-header h3 {
      font-family: var(--font-heading);
      font-size: 1rem;
      font-weight: 600;
      margin: 0;
      color: var(--color-text);
    }

    .rag-query {
      display: flex;
      gap: 0.5rem;
      padding: 1rem;
      border-bottom: 1px solid var(--color-border);
    }

    .rag-query input {
      flex: 1;
    }

    .suggestions-list {
      flex: 1;
      overflow-y: auto;
      padding: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .empty-suggestions {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2rem 1rem;
      color: var(--color-text-secondary);
    }

    .empty-suggestions i {
      font-size: 2rem;
      color: var(--color-gold);
      margin-bottom: 0.75rem;
      opacity: 0.6;
    }

    .suggestion-card {
      padding: 0.875rem;
      background-color: var(--color-sepia-light);
      border: 1px solid var(--color-border);
      border-radius: 6px;
      transition: background-color 0.2s;
    }

    .suggestion-card.accepted {
      opacity: 0.6;
      background-color: rgba(45, 106, 79, 0.06);
    }

    .suggestion-text {
      font-size: 0.875rem;
      line-height: 1.5;
      color: var(--color-text);
      margin: 0 0 0.5rem;
    }

    .suggestion-actions {
      display: flex;
      gap: 0.25rem;
      justify-content: flex-end;
    }

    :host ::ng-deep .p-button-warning {
      background-color: var(--color-gold);
      border-color: var(--color-gold);
      color: var(--color-text);
    }

    :host ::ng-deep .p-button-warning:hover {
      background-color: var(--color-gold-dark);
      border-color: var(--color-gold-dark);
    }
  `],
})
export class DocumentEditorComponent implements OnInit, OnDestroy {
  private readonly documentService = inject(DocumentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly draftId = signal<string | null>(null);
  readonly content = signal<string>('');
  readonly originalContent = signal<string>('');
  readonly saveState = signal<SaveState>('idle');
  readonly aiSuggestions = signal<AISuggestion[]>([]);
  readonly showSuggestions = signal(false);
  readonly dirty = computed(() => this.content() !== this.originalContent());
  readonly loading = signal(true);
  readonly showDiscardDialog = signal(false);
  readonly ragLoading = signal(false);

  // For template binding with ngModel
  ragQueryText = '';

  private readonly autoSave$ = new Subject<string>();
  private readonly destroy$ = new Subject<void>();

  constructor() {
    // Auto-save effect: debounce 30s after content changes
    this.autoSave$.pipe(
      debounceTime(30000),
      takeUntil(this.destroy$)
    ).subscribe(() => {
      if (this.dirty()) {
        this.saveDraft();
      }
    });
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.loading.set(false);
      this.toast.error('Documento no encontrado');
      return;
    }
    this.loadDraft(id);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadDraft(documentId: string): void {
    this.loading.set(true);

    // Try to get existing drafts, otherwise create from document
    this.documentService.getDrafts().pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (drafts: DraftOut[]) => {
        const existing = drafts.find(d => d.document_id === documentId);
        if (existing) {
          this.draftId.set(existing.id);
          const html = this.arrayToHtml(existing.content);
          this.content.set(html);
          this.originalContent.set(html);
          this.loading.set(false);
        } else {
          // Load document and create draft from it
          this.documentService.get(documentId).subscribe({
            next: (doc) => {
              const initial = `<h1>${this.escapeHtml(doc.title)}</h1><p></p>`;
              this.content.set(initial);
              this.originalContent.set(initial);
              this.loading.set(false);
            },
            error: () => {
              this.loading.set(false);
              this.toast.error('Error al cargar el documento');
            },
          });
        }
      },
      error: () => {
        // Fallback: load document directly
        this.documentService.get(documentId).subscribe({
          next: (doc) => {
            const initial = `<h1>${this.escapeHtml(doc.title)}</h1><p></p>`;
            this.content.set(initial);
            this.originalContent.set(initial);
            this.loading.set(false);
          },
          error: () => {
            this.loading.set(false);
            this.toast.error('Error al cargar el documento');
          },
        });
      },
    });
  }

  onEditorInput(event: Event): void {
    const html = (event.target as HTMLElement).innerHTML;
    this.content.set(html);
    this.saveState.set('idle');
    this.autoSave$.next(html);
  }

  onKeyDown(event: KeyboardEvent): void {
    // Ctrl/Cmd + S to save
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
      event.preventDefault();
      this.saveNow();
    }
  }

  saveNow(): void {
    if (!this.dirty()) return;
    this.saveDraft();
  }

  saveDraft(): void {
    const id = this.draftId();
    if (!id) {
      // No draft yet, just mark as saved locally
      this.originalContent.set(this.content());
      this.saveState.set('saved');
      return;
    }

    this.saveState.set('saving');
    const contentArray = this.htmlToArray(this.content());

    this.documentService.saveDraft(id, contentArray).subscribe({
      next: () => {
        this.originalContent.set(this.content());
        this.saveState.set('saved');
      },
      error: () => {
        this.saveState.set('error');
      },
    });
  }

  onClose(): void {
    if (this.dirty()) {
      this.showDiscardDialog.set(true);
    } else {
      this.router.navigate(['/documents']);
    }
  }

  confirmDiscard(): void {
    this.showDiscardDialog.set(false);
    this.router.navigate(['/documents']);
  }

  format(command: string): void {
    document.execCommand(command, false);
  }

  formatBlock(tag: string): void {
    document.execCommand('formatBlock', false, tag);
  }

  queryRag(): void {
    const query = this.ragQueryText.trim();
    if (!query) return;

    this.ragLoading.set(true);
    this.documentService.queryRag(query).subscribe({
      next: (response: any) => {
        this.ragLoading.set(false);
        const text = response?.answer ?? response?.result ?? JSON.stringify(response);
        const suggestion: AISuggestion = {
          id: crypto.randomUUID(),
          text,
          accepted: false,
        };
        this.aiSuggestions.update(list => [...list, suggestion]);
      },
      error: () => {
        this.ragLoading.set(false);
        this.toast.error('Error al consultar la IA');
      },
    });
  }

  acceptSuggestion(suggestion: AISuggestion): void {
    const current = this.content();
    const updated = current + `<p><strong>Sugerencia:</strong> ${this.escapeHtml(suggestion.text)}</p>`;
    this.content.set(updated);
    this.aiSuggestions.update(list =>
      list.map(s => s.id === suggestion.id ? { ...s, accepted: true } : s)
    );
    this.saveState.set('idle');
    this.autoSave$.next(updated);
  }

  dismissSuggestion(suggestion: AISuggestion): void {
    this.aiSuggestions.update(list => list.filter(s => s.id !== suggestion.id));
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private arrayToHtml(content: unknown[] | null): string {
    if (!content || !Array.isArray(content)) return '<p></p>';
    // Simple conversion: assume array of paragraph objects or strings
    return content.map((item: any) => {
      if (typeof item === 'string') return `<p>${this.escapeHtml(item)}</p>`;
      if (item?.type === 'heading') return `<h2>${this.escapeHtml(item.text ?? '')}</h2>`;
      return `<p>${this.escapeHtml(JSON.stringify(item))}</p>`;
    }).join('');
  }

  private htmlToArray(html: string): unknown[] {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const result: unknown[] = [];
    doc.body.childNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const el = node as HTMLElement;
        if (el.tagName.match(/^H[1-6]$/i)) {
          result.push({ type: 'heading', level: parseInt(el.tagName[1]), text: el.textContent ?? '' });
        } else if (el.tagName === 'UL' || el.tagName === 'OL') {
          result.push({ type: 'list', ordered: el.tagName === 'OL', items: Array.from(el.children).map(li => li.textContent ?? '') });
        } else if (el.tagName === 'BLOCKQUOTE') {
          result.push({ type: 'quote', text: el.textContent ?? '' });
        } else {
          result.push({ type: 'paragraph', text: el.textContent ?? '' });
        }
      } else if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim()) {
        result.push({ type: 'paragraph', text: node.textContent.trim() });
      }
    });
    return result.length ? result : [{ type: 'paragraph', text: '' }];
  }
}
