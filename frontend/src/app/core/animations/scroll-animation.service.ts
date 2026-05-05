import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ScrollAnimationService {
  readonly supported = signal(false);
  readonly reducedMotion = signal(false);

  constructor() {
    if (typeof window !== 'undefined') {
      this.supported.set(CSS.supports('animation-timeline: scroll()'));
      this.reducedMotion.set(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }
  }

  shouldAnimate(): boolean {
    return this.supported() && !this.reducedMotion();
  }
}
