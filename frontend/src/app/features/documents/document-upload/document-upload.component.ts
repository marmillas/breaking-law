import { Component, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { HttpEventType } from '@angular/common/http';
import { Subject, takeUntil } from 'rxjs';

import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';

import { DocumentService } from '../document.service';
import { FileDropzoneComponent } from '../../../shared/components/file-dropzone/file-dropzone.component';
import { ProgressBarComponent } from '../../../shared/components/progress-bar/progress-bar.component';
import { ToastService } from '../../../core/http/toast.service';

interface ClassificationOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    InputTextModule,
    DropdownModule,
    ButtonModule,
    CheckboxModule,
    FileDropzoneComponent,
    ProgressBarComponent,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Subir documento</h1>
        <a routerLink="/documents" class="back-link">
          <i class="pi pi-arrow-left"></i> Volver a documentos
        </a>
      </div>

      <div class="upload-layout">
        <div class="dropzone-section">
          @if (!selectedFile()) {
            <app-file-dropzone
              [acceptedFormats]="['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg']"
              [maxSizeMB]="50"
              (fileSelected)="onFileSelected($event)"
            ></app-file-dropzone>
          } @else {
            <div class="file-preview">
              <i class="pi pi-file"></i>
              <span class="file-name">{{ selectedFile()!.name }}</span>
              <span class="file-size">({{ formattedSize() }})</span>
              @if (!uploading()) {
                <button
                  pButton
                  type="button"
                  icon="pi pi-times"
                  class="p-button-text p-button-sm p-button-danger"
                  (click)="removeFile()"
                ></button>
              }
            </div>
          }

          @if (uploading()) {
            <div class="progress-section">
              <app-progress-bar
                [value]="progress()"
                label="Subiendo..."
                [showPercentage]="true"
              ></app-progress-bar>
              <button
                pButton
                type="button"
                label="Cancelar"
                icon="pi pi-times"
                class="p-button-text p-button-sm"
                (click)="cancelUpload()"
              ></button>
            </div>
          }
        </div>

        @if (selectedFile() && !uploading()) {
          <form [formGroup]="metadataForm" (ngSubmit)="onUpload()" class="metadata-form">
            <div class="form-group">
              <label for="title">Título <span class="required">*</span></label>
              <input
                id="title"
                pInputText
                formControlName="title"
                placeholder="Título del documento"
                class="w-full"
              />
              @if (metadataForm.get('title')?.invalid && metadataForm.get('title')?.touched) {
                <small class="error-text">El título es obligatorio.</small>
              }
            </div>

            <div class="form-group">
              <label for="matter">Expediente</label>
              <input
                id="matter"
                pInputText
                formControlName="matter_id"
                placeholder="ID del expediente (opcional)"
                class="w-full"
              />
            </div>

            <div class="form-group">
              <label for="classification">Clasificación</label>
              <p-dropdown
                id="classification"
                formControlName="classification"
                [options]="classificationOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Seleccionar clasificación"
                styleClass="w-full"
                [showClear]="true"
              ></p-dropdown>
            </div>

            <div class="form-group checkbox-group">
              <p-checkbox
                formControlName="is_confidential"
                [binary]="true"
                inputId="confidential"
              ></p-checkbox>
              <label for="confidential" class="checkbox-label">Documento confidencial</label>
            </div>

            @if (error()) {
              <div class="error-banner">
                <i class="pi pi-exclamation-circle"></i>
                <span>{{ error() }}</span>
              </div>
            }

            <div class="form-actions">
              <button
                pButton
                type="submit"
                label="Subir"
                icon="pi pi-upload"
                class="p-button-warning"
                [disabled]="metadataForm.invalid || uploading()"
                [loading]="uploading()"
              ></button>
            </div>
          </form>
        }
      </div>
    </div>
  `,
  styles: [`
    .page-container {
      padding: 1.5rem;
      max-width: 800px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .page-title {
      font-family: var(--font-heading);
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      margin: 0;
    }

    .back-link {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: var(--color-review);
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
    }

    .back-link:hover {
      text-decoration: underline;
    }

    .upload-layout {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .dropzone-section {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
    }

    .file-preview {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background-color: var(--color-sepia-light);
      border-radius: 6px;
      border: 1px solid var(--color-border);
    }

    .file-preview i {
      color: var(--color-gold);
      font-size: 1.25rem;
    }

    .file-name {
      font-weight: 500;
      color: var(--color-text);
      flex: 1;
    }

    .file-size {
      color: var(--color-text-secondary);
      font-size: 0.875rem;
    }

    .progress-section {
      margin-top: 1rem;
    }

    .metadata-form {
      background-color: var(--color-surface);
      border-radius: 8px;
      border: 1px solid var(--color-border);
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }

    .form-group label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text);
    }

    .required {
      color: var(--color-critical);
    }

    .error-text {
      color: var(--color-critical);
      font-size: 0.8125rem;
    }

    .checkbox-group {
      flex-direction: row;
      align-items: center;
      gap: 0.5rem;
    }

    .checkbox-label {
      font-size: 0.875rem;
      color: var(--color-text);
      cursor: pointer;
    }

    .error-banner {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      background-color: rgba(155, 34, 38, 0.08);
      border: 1px solid rgba(155, 34, 38, 0.2);
      border-radius: 6px;
      color: var(--color-critical);
      font-size: 0.875rem;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 0.5rem;
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
export class DocumentUploadComponent implements OnDestroy {
  private readonly documentService = inject(DocumentService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  readonly selectedFile = signal<File | null>(null);
  readonly uploading = signal(false);
  readonly progress = signal(0);
  readonly error = signal<string | null>(null);

  metadataForm: FormGroup = this.fb.group({
    title: ['', Validators.required],
    matter_id: [''],
    classification: [null],
    is_confidential: [false],
  });

  readonly classificationOptions: ClassificationOption[] = [
    { label: 'Contrato', value: 'contrato' },
    { label: 'Demanda', value: 'demanda' },
    { label: 'Sentencia', value: 'sentencia' },
    { label: 'Dictamen', value: 'dictamen' },
    { label: 'Escrito', value: 'escrito' },
    { label: 'Informe', value: 'informe' },
  ];

  private uploadAbort$ = new Subject<void>();
  private destroy$ = new Subject<void>();

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.uploadAbort$.next();
    this.uploadAbort$.complete();
  }

  onFileSelected(file: File): void {
    this.selectedFile.set(file);
    this.error.set(null);
    // Pre-fill title with filename (without extension)
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
    this.metadataForm.patchValue({ title: nameWithoutExt });
  }

  removeFile(): void {
    this.selectedFile.set(null);
    this.progress.set(0);
    this.metadataForm.reset({
      title: '',
      matter_id: '',
      classification: null,
      is_confidential: false,
    });
  }

  onUpload(): void {
    if (this.metadataForm.invalid || !this.selectedFile()) return;

    this.uploading.set(true);
    this.progress.set(0);
    this.error.set(null);

    const file = this.selectedFile()!;
    const metadata = this.metadataForm.value;

    // Clean empty strings to undefined
    const cleanMetadata = {
      title: metadata.title,
      matter_id: metadata.matter_id || undefined,
      classification: metadata.classification || undefined,
      is_confidential: metadata.is_confidential,
    };

    this.documentService.upload(file, cleanMetadata)
      .pipe(takeUntil(this.uploadAbort$))
      .subscribe({
        next: (event) => {
          if (event.type === HttpEventType.UploadProgress && event.total) {
            const pct = Math.round((event.loaded / event.total) * 100);
            this.progress.set(pct);
          } else if (event.type === HttpEventType.Response && event.body) {
            this.uploading.set(false);
            this.progress.set(100);
            this.toast.success('Documento subido correctamente');
            this.router.navigate(['/documents', event.body.document_id]);
          }
        },
        error: (err) => {
          this.uploading.set(false);
          this.progress.set(0);
          this.error.set(err.error?.detail ?? 'Error al subir el documento. Intente nuevamente.');
        },
      });
  }

  cancelUpload(): void {
    this.uploadAbort$.next();
    this.uploading.set(false);
    this.progress.set(0);
  }

  formattedSize(): string {
    const file = this.selectedFile();
    if (!file) return '';
    const mb = file.size / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(file.size / 1024).toFixed(1)} KB`;
  }
}
