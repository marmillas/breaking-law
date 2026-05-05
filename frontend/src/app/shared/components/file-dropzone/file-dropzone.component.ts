import { Component, input, output, signal } from '@angular/core';
import { NgIf, NgClass } from '@angular/common';

@Component({
  selector: 'app-file-dropzone',
  standalone: true,
  imports: [NgIf],
  template: `
    <div
      class="dropzone"
      [class.dragover]="isDragOver()"
      (dragover)="onDragOver($event)"
      (dragleave)="onDragLeave($event)"
      (drop)="onDrop($event)"
      (click)="fileInput.click()"
    >
      <input
        #fileInput
        type="file"
        class="hidden-input"
        [accept]="acceptAttribute()"
        (change)="onFileSelected($event)"
      />
      <i class="pi pi-cloud-upload"></i>
      <p class="dropzone-title">Arrastrá archivos aquí o hacé clic para seleccionar</p>
      <p class="dropzone-hint">Formatos: {{ formatsLabel() }} · Máx: {{ maxSizeMB() }} MB</p>
      <div *ngIf="selectedFile()" class="selected-file">
        <i class="pi pi-file"></i>
        <span class="file-name">{{ selectedFile()?.name }}</span>
        <span class="file-size">({{ formattedSize() }})</span>
      </div>
      <p *ngIf="error()" class="error-message">{{ error() }}</p>
    </div>
  `,
  styles: [`
    .dropzone {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem 1.5rem;
      border: 2px dashed var(--color-border);
      border-radius: 8px;
      background-color: var(--color-sepia-light);
      cursor: pointer;
      transition: border-color var(--transition-fast), background-color var(--transition-fast);
      text-align: center;
    }

    .dropzone:hover {
      border-color: var(--color-gold);
      background-color: rgba(184, 150, 90, 0.04);
    }

    .dropzone.dragover {
      border-color: var(--color-gold);
      background-color: rgba(184, 150, 90, 0.08);
    }

    .hidden-input {
      display: none;
    }

    .dropzone i.pi-cloud-upload {
      font-size: 2.5rem;
      color: var(--color-gold);
      margin-bottom: 0.75rem;
    }

    .dropzone-title {
      font-size: 1rem;
      font-weight: 500;
      color: var(--color-text);
      margin-bottom: 0.25rem;
    }

    .dropzone-hint {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
      margin-bottom: 0.75rem;
    }

    .selected-file {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 0.75rem;
      padding: 0.5rem 0.875rem;
      background-color: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 6px;
    }

    .selected-file i {
      color: var(--color-gold);
    }

    .file-name {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text);
    }

    .file-size {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
    }

    .error-message {
      margin-top: 0.75rem;
      font-size: 0.875rem;
      color: var(--color-critical);
      font-weight: 500;
    }
  `],
})
export class FileDropzoneComponent {
  acceptedFormats = input<string[]>(['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg']);
  maxSizeMB = input<number>(50);

  fileSelected = output<File>();

  readonly isDragOver = signal(false);
  readonly selectedFile = signal<File | null>(null);
  readonly error = signal<string | null>(null);

  acceptAttribute() {
    return this.acceptedFormats().join(',');
  }

  formatsLabel() {
    return this.acceptedFormats().join(', ').toUpperCase();
  }

  formattedSize() {
    const file = this.selectedFile();
    if (!file) return '';
    const mb = file.size / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(file.size / 1024).toFixed(1)} KB`;
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.validateAndEmit(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (files && files.length > 0) {
      this.validateAndEmit(files[0]);
    }
  }

  private validateAndEmit(file: File): void {
    this.error.set(null);

    // Size check
    const maxBytes = this.maxSizeMB() * 1024 * 1024;
    if (file.size > maxBytes) {
      this.error.set(`El archivo excede el tamaño máximo de ${this.maxSizeMB()} MB.`);
      return;
    }

    // Format check by extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const formats = this.acceptedFormats().map(f => f.toLowerCase());
    const mimeToExt: Record<string, string> = {
      'application/pdf': '.pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
      'text/plain': '.txt',
      'image/png': '.png',
      'image/jpeg': '.jpg',
      'image/jpg': '.jpg',
    };
    const mimeExt = mimeToExt[file.type.toLowerCase()];

    const valid = formats.includes(ext) || (mimeExt && formats.includes(mimeExt));
    if (!valid) {
      this.error.set(`Formato no permitido. Aceptados: ${this.formatsLabel()}`);
      return;
    }

    this.selectedFile.set(file);
    this.fileSelected.emit(file);
  }
}
