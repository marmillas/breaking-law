import { Injectable, signal } from '@angular/core';

export type Breakpoint = 'mobile' | 'tablet' | 'desktop';

@Injectable({ providedIn: 'root' })
export class ResizeService {
  readonly breakpoint = signal<Breakpoint>('desktop');
  readonly width = signal<number>(typeof window !== 'undefined' ? window.innerWidth : 1200);

  constructor() {
    if (typeof window !== 'undefined') {
      this.updateBreakpoint(window.innerWidth);
      window.addEventListener('resize', () => {
        const w = window.innerWidth;
        this.width.set(w);
        this.updateBreakpoint(w);
      });
    }
  }

  private updateBreakpoint(w: number): void {
    if (w < 768) {
      this.breakpoint.set('mobile');
    } else if (w < 1024) {
      this.breakpoint.set('tablet');
    } else {
      this.breakpoint.set('desktop');
    }
  }
}
