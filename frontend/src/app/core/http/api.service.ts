import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  private joinPath(path: string): string {
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    return `${this.baseUrl}/${cleanPath}`;
  }

  get<T>(path: string, params?: Record<string, string | number | boolean | null | undefined>): Observable<T> {
    let httpParams = new HttpParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          httpParams = httpParams.set(key, String(value));
        }
      });
    }
    return this.http.get<T>(this.joinPath(path), { params: httpParams });
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(this.joinPath(path), body);
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(this.joinPath(path), body);
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(this.joinPath(path));
  }

  download(path: string): Observable<Blob> {
    return this.http.get(this.joinPath(path), { responseType: 'blob' });
  }

  upload<T>(path: string, formData: FormData): Observable<HttpEvent<T>> {
    return this.http.post<T>(this.joinPath(path), formData, {
      reportProgress: true,
      observe: 'events',
    }) as Observable<HttpEvent<T>>;
  }
}
