import { Directive, ElementRef, HostListener, OnDestroy, OnInit, inject } from '@angular/core';
import { ScrollAnimationService } from '../../core/animations/scroll-animation.service';

@Directive({
  selector: '[appScrollProgress]',
  standalone: true,
})
export class ScrollProgressDirective implements OnInit, OnDestroy {
  private readonly el = inject(ElementRef<HTMLElement>);
  private readonly scrollService = inject(ScrollAnimationService);

  private rafId: number | null = null;
  private useCss = false;
  private useWindow = false;

  ngOnInit(): void {
    // If CSS scroll-driven animations are supported and motion is not reduced,
    // we can rely on CSS animation-timeline. Otherwise, use JS fallback.
    this.useCss = this.scrollService.supported();

    // Determine if the element itself scrolls or if we should use window scroll
    const element = this.el.nativeElement;
    const hasScroll = element.scrollHeight > element.clientHeight;
    this.useWindow = !hasScroll;

    if (!this.useCss && !this.scrollService.reducedMotion()) {
      if (this.useWindow) {
        window.addEventListener('scroll', this.onWindowScroll, { passive: true });
      }
      this.updateProgress();
    }
  }

  ngOnDestroy(): void {
    if (this.rafId != null) {
      cancelAnimationFrame(this.rafId);
    }
    if (this.useWindow) {
      window.removeEventListener('scroll', this.onWindowScroll);
    }
  }

  @HostListener('scroll')
  onScroll(): void {
    if (this.useWindow || this.useCss || this.scrollService.reducedMotion()) {
      return;
    }
    this.scheduleUpdate();
  }

  private onWindowScroll = (): void => {
    if (this.useCss || this.scrollService.reducedMotion()) {
      return;
    }
    this.scheduleUpdate();
  };

  private scheduleUpdate(): void {
    if (this.rafId == null) {
      this.rafId = requestAnimationFrame(() => {
        this.updateProgress();
        this.rafId = null;
      });
    }
  }

  private updateProgress(): void {
    let progress = 0;
    if (this.useWindow) {
      const docEl = document.documentElement;
      const scrollTop = window.scrollY || docEl.scrollTop;
      const maxScroll = docEl.scrollHeight - docEl.clientHeight;
      progress = maxScroll > 0 ? scrollTop / maxScroll : 0;
    } else {
      const el = this.el.nativeElement;
      const scrollTop = el.scrollTop;
      const maxScroll = el.scrollHeight - el.clientHeight;
      progress = maxScroll > 0 ? scrollTop / maxScroll : 0;
    }
    this.el.nativeElement.style.setProperty('--scroll-progress', progress.toFixed(4));
  }
}
