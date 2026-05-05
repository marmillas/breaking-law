import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'dateEs', standalone: true })
export class DateEsPipe implements PipeTransform {
  transform(value: string | Date | null | undefined, format: 'short' | 'long' | 'full' = 'short'): string {
    if (!value) return '';
    const date = new Date(value);
    if (isNaN(date.getTime())) return '';

    if (format === 'short') {
      return date.toLocaleDateString('es-ES'); // DD/MM/YYYY
    }
    if (format === 'long') {
      return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    return date.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }
}
