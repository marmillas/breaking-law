import { Component } from '@angular/core';
import { ToastModule } from 'primeng/toast';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [ToastModule],
  template: `<p-toast position="top-right" [breakpoints]="{ '920px': { width: '100%', right: '0', left: '0' } }" />`,
})
export class ToastComponent {}
