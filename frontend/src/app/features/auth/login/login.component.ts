import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { DividerModule } from 'primeng/divider';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    DividerModule,
    ProgressSpinnerModule,
  ],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-sepia-100 px-4">
      <div class="w-full max-w-md bg-white rounded-xl shadow-lg p-8 border border-sepia-200">
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900 font-heading mb-2">Breaking Law</h1>
          <p class="text-sm text-gray-600">Plataforma jurídica integral</p>
        </div>

        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" class="space-y-5">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Correo electrónico</label>
            <input
              id="email"
              type="email"
              pInputText
              formControlName="email"
              class="w-full"
              placeholder="usuario@estudio.com"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <p-password
              id="password"
              formControlName="password"
              [toggleMask]="true"
              [feedback]="false"
              styleClass="w-full"
              inputStyleClass="w-full"
              placeholder="••••••••"
            ></p-password>
          </div>

          @if (error()) {
            <p class="text-sm text-red-600">{{ error() }}</p>
          }

          <button
            pButton
            type="submit"
            label="Iniciar sesión"
            class="w-full bg-gold-500 hover:bg-gold-600 text-gray-900 font-semibold py-2.5 rounded-lg transition-colors"
            [loading]="loading()"
            [disabled]="loginForm.invalid || loading()"
          ></button>
        </form>

        <p-divider align="center" styleClass="my-6">
          <span class="text-xs text-gray-500 px-2">o</span>
        </p-divider>

        <div class="space-y-3">
          <button
            pButton
            type="button"
            icon="pi pi-google"
            label="Iniciar sesión con Google"
            class="w-full bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
            (click)="onGoogleLogin()"
          ></button>

          <button
            pButton
            type="button"
            icon="pi pi-microsoft"
            label="Iniciar sesión con Microsoft"
            class="w-full bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
            (click)="onMicrosoftLogin()"
          ></button>
        </div>
      </div>
    </div>
  `,
})
export class LoginComponent {
  loginForm: FormGroup;
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(
    private readonly fb: FormBuilder,
    private readonly authService: AuthService,
    private readonly router: Router,
    private readonly route: ActivatedRoute
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    const { email, password } = this.loginForm.value;

    this.authService.login(email, password).subscribe({
      next: () => {
        this.authService.getMe().subscribe({
          next: () => {
            this.loading.set(false);
            const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
            this.router.navigateByUrl(returnUrl);
          },
          error: () => {
            this.loading.set(false);
            this.error.set('Error al cargar el perfil. Intente nuevamente.');
          },
        });
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.error?.detail ?? 'Error al iniciar sesión. Verifique sus credenciales.');
      },
    });
  }

  onGoogleLogin(): void {
    this.authService.startOAuth('google');
  }

  onMicrosoftLogin(): void {
    this.authService.startOAuth('microsoft');
  }
}
