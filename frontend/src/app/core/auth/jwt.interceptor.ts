import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, throwError, BehaviorSubject, catchError, switchMap, take, filter, finalize } from 'rxjs';
import { AuthService } from './auth.service';
import { TokenResponse } from '../../models/auth.model';

let refreshInFlight: boolean = false;
let refreshSubject: BehaviorSubject<TokenResponse | null> | null = null;

function addToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
}

function isAuthEndpoint(url: string): boolean {
  return url.includes('/auth/login') || url.includes('/auth/oauth');
}

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  authService: AuthService,
  router: Router
): Observable<HttpEvent<unknown>> {
  // If the failed request IS the refresh endpoint, logout immediately
  if (req.url.includes('/auth/refresh')) {
    authService.clearAuth();
    router.navigate(['/login']);
    return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Unauthorized' }));
  }

  if (!refreshSubject) {
    refreshSubject = new BehaviorSubject<TokenResponse | null>(null);
  }

  const currentSubject = refreshSubject;

  if (!refreshInFlight) {
    refreshInFlight = true;

    authService.refreshToken()
      .pipe(
        finalize(() => {
          refreshInFlight = false;
          refreshSubject = null;
        })
      )
      .subscribe({
        next: (response) => {
          authService.setTokens(response);
          currentSubject.next(response);
          currentSubject.complete();
        },
        error: () => {
          authService.clearAuth();
          router.navigate(['/login']);
          currentSubject.next(null);
          currentSubject.complete();
        },
      });
  }

  return currentSubject.pipe(
    filter((result): result is TokenResponse => result !== null),
    take(1),
    switchMap((response) => {
      return next(addToken(req, response.access_token));
    }),
    catchError((err) => throwError(() => err))
  );
}

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = authService.getAccessToken();

  if (!token || isAuthEndpoint(req.url)) {
    return next(req);
  }

  const authenticatedReq = addToken(req, token);

  return next(authenticatedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        return handle401(req, next, authService, router);
      }
      return throwError(() => error);
    })
  );
};
