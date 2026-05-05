import { Directive, Input, TemplateRef, ViewContainerRef, effect } from '@angular/core';
import { AuthService } from './auth.service';

@Directive({
  selector: '[hasRole]',
  standalone: true,
})
export class HasRoleDirective {
  private hasView = false;

  @Input({ required: true }) set hasRole(roles: string | string[]) {
    this.requiredRoles = Array.isArray(roles) ? roles : [roles];
    this.updateView();
  }

  private requiredRoles: string[] = [];

  constructor(
    private readonly templateRef: TemplateRef<unknown>,
    private readonly viewContainer: ViewContainerRef,
    private readonly authService: AuthService
  ) {
    effect(() => {
      // Re-evaluate when role signal changes
      this.authService.role();
      this.updateView();
    });
  }

  private updateView(): void {
    const userRole = this.authService.role();
    const allowed = userRole !== null && this.requiredRoles.includes(userRole);

    if (allowed && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!allowed && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }
}
