import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler, LOCALE_ID } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';

import { routes } from './app.routes';
import { jwtInterceptor } from './core/auth/jwt.interceptor';
import { errorInterceptor } from './core/http/error.interceptor';
import { cacheInterceptor } from './core/http/cache.interceptor';
import { ToastService } from './core/http/toast.service';
import { GlobalErrorHandler } from './core/http/global-error-handler';

registerLocaleData(localeEs, 'es-ES');

const primeNGTranslation = {
  accept: 'Aceptar',
  reject: 'Cancelar',
  monthNames: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
  monthNamesShort: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
  dayNames: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
  dayNamesShort: ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'],
  dayNamesMin: ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá'],
  emptyMessage: 'No hay opciones disponibles',
  emptyFilterMessage: 'No se encontraron resultados',
  startsWith: 'Empieza con',
  contains: 'Contiene',
  notContains: 'No contiene',
  endsWith: 'Termina con',
  equals: 'Igual a',
  notEquals: 'Distinto de',
  noFilter: 'Sin filtro',
  lt: 'Menor que',
  lte: 'Menor o igual que',
  gt: 'Mayor que',
  gte: 'Mayor o igual que',
  dateIs: 'Fecha es',
  dateIsNot: 'Fecha no es',
  dateBefore: 'Fecha antes de',
  dateAfter: 'Fecha después de',
  clear: 'Limpiar',
  apply: 'Aplicar',
  matchAll: 'Coincidir todo',
  matchAny: 'Coincidir cualquiera',
  addRule: 'Agregar regla',
  removeRule: 'Eliminar regla',
  choose: 'Elegir',
  upload: 'Subir',
  cancel: 'Cancelar',
  fileSizeTypes: ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
  pending: 'Pendiente',
  chooseYear: 'Elegir año',
  chooseMonth: 'Elegir mes',
  chooseDate: 'Elegir fecha',
  prevDecade: 'Década anterior',
  nextDecade: 'Década siguiente',
  prevYear: 'Año anterior',
  nextYear: 'Año siguiente',
  prevMonth: 'Mes anterior',
  nextMonth: 'Mes siguiente',
  prevHour: 'Hora anterior',
  nextHour: 'Hora siguiente',
  prevMinute: 'Minuto anterior',
  nextMinute: 'Minuto siguiente',
  prevSecond: 'Segundo anterior',
  nextSecond: 'Segundo siguiente',
  am: 'am',
  pm: 'pm',
  today: 'Hoy',
  weekHeader: 'Sem',
  firstDayOfWeek: 0,
  dateFormat: 'dd/mm/yy',
  weak: 'Débil',
  medium: 'Medio',
  strong: 'Fuerte',
  passwordPrompt: 'Ingresá una contraseña',
  searchMessage: 'Hay {0} resultados disponibles',
  selectionMessage: '{0} elementos seleccionados',
  emptySelectionMessage: 'No hay elementos seleccionados',
  emptySearchMessage: 'No se encontraron resultados',
  aria: {
    trueLabel: 'Verdadero',
    falseLabel: 'Falso',
    nullLabel: 'No seleccionado',
    star: '1 estrella',
    stars: '{star} estrellas',
    selectAll: 'Seleccionar todo',
    unselectAll: 'Deseleccionar todo',
    close: 'Cerrar',
    previous: 'Anterior',
    next: 'Siguiente',
    navigation: 'Navegación',
    scrollTop: 'Desplazar arriba',
    moveTop: 'Mover arriba',
    moveUp: 'Mover arriba',
    moveDown: 'Mover abajo',
    moveBottom: 'Mover abajo',
    moveToTarget: 'Mover a destino',
    moveToSource: 'Mover a origen',
    moveAllToTarget: 'Mover todo a destino',
    moveAllToSource: 'Mover todo a origen',
    rotateRight: 'Rotar derecha',
    rotateLeft: 'Rotar izquierda',
    selectLabel: 'Seleccionar',
    unselectLabel: 'Deseleccionar',
    expandLabel: 'Expandir',
    collapseLabel: 'Colapsar',
  },
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([jwtInterceptor, errorInterceptor, cacheInterceptor])),
    provideAnimationsAsync(),
    providePrimeNG({ translation: primeNGTranslation }),
    MessageService,
    ToastService,
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    { provide: LOCALE_ID, useValue: 'es-ES' },
  ],
};
