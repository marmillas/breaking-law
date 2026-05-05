import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'numberEs', standalone: true })
export class NumberEsPipe implements PipeTransform {
  transform(value: number | null | undefined, decimals = 2): string {
    if (value == null || isNaN(value)) return '';
    return value.toLocaleString('es-ES', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
}
