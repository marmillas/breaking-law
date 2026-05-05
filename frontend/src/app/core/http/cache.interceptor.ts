import { HttpInterceptorFn } from '@angular/common/http';

export const cacheInterceptor: HttpInterceptorFn = (req, next) => {
  // Simple no-op interceptor for now.
  // TODO: implement GET cache with TTL and ETag support when needed.
  return next(req);
};
