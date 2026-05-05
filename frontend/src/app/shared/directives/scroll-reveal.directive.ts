import { Directive, ElementRef, OnDestroy, OnInit, inject } from '@angular/core';
import { ScrollAnimationService } from '../../core/animations/scroll-animation.service';

@Directive({
  selector: '[appScrollReveal]',
  standalone: true,
})
export class ScrollRevealDirective implements OnInit, OnDestroy {
  private readonly el = inject(ElementRef<HTMLElement>);
  private readonly scrollService = inject(ScrollAnimationService);

  private observer: IntersectionObserver | null = null;

  ngOnInit(): void {
    const element = this.el.nativeElement;

    if (this.scrollService.supported()) {
      // CSS handles it via animation-timeline: view()
      element.classList.add('scroll-reveal');
      return;
    }

    if (this.scrollService.reducedMotion()) {
      // Ensure visible, no animation
      element.style.opacity = '1';
      element.style.transform = 'none';
      return;
    }

    // Fallback: IntersectionObserver
    element.style.opacity = '0';
    element.style.transform = 'translateY(24px)';
    element.style.transition = 'opacity 400ms ease, transform 400ms ease';

    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
            this.observer?.unobserve(element);
          }
        });
      },
      { threshold: 0.1 }
    );

    this.observer.observe(element);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
