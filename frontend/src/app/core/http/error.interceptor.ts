import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from './toast.service';

function mapErrorToMessage(error: HttpErrorResponse): string {
  if (error.status === 0) {
    return 'Error de conexión';
  }

  switch (error.status) {
    case 400:
      return 'Datos inválidos';
    case 401:
      // Skip — JWT interceptor handles auth errors
      return '';
    case 403:
      return 'No tiene permisos';
    case 404:
      return 'No encontrado';
    case 413:
      return 'Archivo demasiado grande';
    case 422:
      return 'Datos inválidos';
    case 500:
      return 'Error del servidor. Intente nuevamente.';
    default:
      return error.error?.detail ?? error.error?.message ?? 'Error de conexión';
  }
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toastService = inject(ToastService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const message = mapErrorToMessage(error);

      if (message && error.status !== 401) {
        toastService.error(message);
      }

      return throwError(() => error);
    })
  );
};
