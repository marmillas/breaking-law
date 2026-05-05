import { ErrorHandler, Injectable, Injector } from '@angular/core';
import { ToastService } from './toast.service';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  constructor(private injector: Injector) {}

  handleError(error: any): void {
    // Avoid circular dependency: get ToastService lazily
    const toastService = this.injector.get(ToastService);

    console.error('Unhandled error:', error);

    // Don't show toast for known Angular errors that are handled elsewhere
    if (error?.message?.includes('ExpressionChangedAfterItHasBeenCheckedError')) {
      // Dev-only warning, don't show to user
      return;
    }

    toastService.error('Ocurrió un error inesperado. Recargá la página si el problema persiste.', 'Error');

    // Still throw so Angular's default behavior (dev mode stack trace) works
    throw error;
  }
}
