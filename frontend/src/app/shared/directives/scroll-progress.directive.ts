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

  ngOnInit(): void {
    // If CSS scroll-driven animations are supported and motion is not reduced,
    // we can rely on CSS animation-timeline. Otherwise, use JS fallback.
    this.useCss = this.scrollService.supported();

    if (!this.useCss && !this.scrollService.reducedMotion()) {
      this.updateProgress();
    }
  }

  ngOnDestroy(): void {
    if (this.rafId != null) {
      cancelAnimationFrame(this.rafId);
    }
  }

  @HostListener('scroll')
  onScroll(): void {
    if (this.useCss || this.scrollService.reducedMotion()) {
      return;
    }
    if (this.rafId == null) {
      this.rafId = requestAnimationFrame(() => {
        this.updateProgress();
        this.rafId = null;
      });
    }
  }

  private updateProgress(): void {
    const el = this.el.nativeElement;
    const scrollTop = el.scrollTop;
    const maxScroll = el.scrollHeight - el.clientHeight;
    const progress = maxScroll > 0 ? scrollTop / maxScroll : 0;
    el.style.setProperty('--scroll-progress', progress.toFixed(4));
  }
}
