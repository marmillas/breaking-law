import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-deadline-calendar',
  standalone: true,
  imports: [CommonModule],
  template: `<div class="p-6"><h1 class="text-2xl font-heading">Calendario</h1></div>`,
})
export class DeadlineCalendarComponent {}
