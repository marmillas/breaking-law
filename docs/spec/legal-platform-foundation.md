# Especificación Plataforma Legal

**Superseded By**: `legal-ai-platform-foundation-mvp.md` (2026-05-03)

This document has been superseded by the comprehensive MVP specification.

## Propósito

Definir requisitos y comportamientos para plataforma legal multi-tenant con capacidades de IA, gestión documental, búsqueda híbrida y cumplimiento normativo.

## Requisitos AGREGADOS

### Requisito: Límites Multi-Tenant
La plataforma DEBE mantener aislamiento estricto entre bufetes distintos. Cada bufete posee espacio lógico separado. Datos cruzados entre bufetes NO DEBEN ser accesibles salvo consentimiento explícito.

#### Escenario: Acceso a Documento Correcto
- GIVEN abogado del bufete A
- WHEN solicita acceso a documento
- THEN sistema SOLO muestra documentos de bufete A
- AND rechaza solicitudes a datos de bufete B

#### Escenario: Intento Acceso Cruzado
- GIVEN abogado de bufete A
- WHEN intenta acceder a documento de bufete B
- THEN sistema deniega acceso
- AND registra intento en logs

### Requisito: Ingestión Documental
La plataforma DEBE aceptar carga de documentos en formatos comunes (PDF, DOCX, TXT). Sistema extrae metadatos automáticamente. Contenido indexado para búsqueda inmediata.

#### Escenario: Carga PDF
- GIVEN usuario carga PDF desde web
- WHEN archivo subido
- THEN sistema extrae texto, metadatos
- AND indexa contenido para búsqueda inmediata

#### Escenario: Documento Confidencial
- GIVEN documento marcado como confidencial
- WHEN se procesa
- THEN sistema aplica reglas estrictas acceso
- AND evita indexación pública

### Requisito: Acceso Web a Documentos
La plataforma DEBE permitir acceso web a documentos almacenados. Interfaz web permite búsqueda, visualización, descarga. Control acceso por roles.

#### Escenario: Búsqueda Documento
- GIVEN abogado autenticado
- WHEN busca término en interfaz web
- THEN sistema muestra resultados relevantes
- AND filtra por permisos del usuario

#### Escenario: Descarga Documento
- GIVEN abogado con permiso
- WHEN solicita descarga
- THEN sistema genera archivo
- AND entrega descarga segura

### Requisito: Búsqueda Legal Híbrida
La plataforma DEBE implementar búsqueda híbrida: BM25 + vectorial. Combina búsqueda léxica exacta con semántica contextual. Mejora precisión resultados legales.

#### Escenario: Búsqueda Término Legal
- GIVEN consulta "contrato laboral"
- WHEN abogado busca
- THEN sistema retorna documentos relevantes
- AND prioriza por contexto semántico

#### Escenario: Búsqueda por Similaridad
- GIVEN documento base
- WHEN abogado solicita similares
- THEN sistema encuentra casos análogos
- AND ordena por relevancia

### Requisito: Anti-Alucinación Legal
La plataforma NO DEBE inventar jurisprudencia. Sistema DEBE verificar afirmaciones legales vs fuentes oficiales. Fallback explícito cuando duda.

#### Escenario: Respuesta Legal
- GIVEN consulta sobre ley específica
- WHEN IA responde
- THEN sistema verifica fuente oficial
- AND advierte si no encuentra respaldo

#### Escenario: Sin Respuesta Válida
- GIVEN consulta legal compleja
- WHEN sistema duda
- THEN responde "verificación externa necesaria"
- AND sugiere fuentes oficiales

### Requisito: Ruteo LLM Premium
La plataforma DEBE enrutar solicitudes a modelos LLM según complejidad. Tareas simples → modelo económico. Tareas complejas → modelos premium (GPT-4, Claude Opus).

#### Escenario: Tarea Simple
- GIVEN consulta corta rutinaria
- WHEN sistema analiza
- THEN usa modelo económico
- AND responde rápido

#### Escenario: Documento Complejo
- GIVEN documento 50+ páginas
- WHEN sistema procesa
- THEN enruta a modelo premium
- AND permite análisis profundo

### Requisito: Autenticación OAuth
La plataforma DEBE usar OAuth 2.0. Integración Google, Microsoft. Perfiles detallados usuarios. Preferencias correo fuente para inferencia IA.

#### Escenario: Inicio Sesión
- GIVEN usuario accede
- WHEN elige proveedor OAuth
- THEN sistema redirige
- AND obtiene perfil detallado

#### Escenario: Preferencias Correo
- GIVEN perfil con correo corporativo
- WHEN sistema infiere rol
- THEN asigna casos según dominio
- AND adapta sugerencias IA

### Requisito: Inbox Acciones IA
La plataforma DEBE presentar acciones sugeridas IA en inbox. Orden prioridad: urgencia legal. Abogado aprueba tareas (citas, recordatorios).

#### Escenario: Sugerencia Nueva
- GIVEN análisis documento por IA
- WHEN detecta acción posible
- THEN sistema crea tarea en inbox
- AND ordena por urgencia

#### Escenario: Aprobación Tarea
- GIVEN tarea en inbox
- WHEN abogado aprueba
- THEN sistema agenda cita
- AND notifica interesados

### Requisito: Editor Web Documentos
La plataforma DEBE proveer editor web documentos. Permite creación, edición documentos legales directo navegador. Exportación DOCX/PDF.

#### Escenario: Crear Documento Nuevo
- GIVEN abogado en plataforma
- WHEN accede editor
- THEN puede crear documento
- AND guardarlo localmente

#### Escenario: Exportar a DOCX
- GIVEN documento creado/editado
- WHEN abogado elige exportar
- THEN sistema genera DOCX
- AND ofrece descarga

#### Escenario: Exportar a PDF
- GIVEN documento listo
- WHEN abogado solicita PDF
- THEN sistema genera PDF firmado
- AND permite descarga

### Requisito: Auditabilidad Legal
La plataforma DEBE ser completamente auditable. Toda acción IA, usuario, sistema registrada. Explicable ante autoridades legales.

#### Escenario: Traza Acción IA
- GIVEN sugerencia IA
- WHEN abogado actúa
- THEN sistema registra evento
- AND mantiene cadena custodia

#### Escenario: Generar Reporte Auditoría
- GIVEN auditoría requerida
- WHEN se solicita traza
- THEN sistema entrega reporte completo
- AND permite seguimiento acciones

## Requisitos MODIFICADOS

### Requisito: Acceso a Documentos (Previo: Acceso básico)
La plataforma DEBE permitir acceso a documentos almacenados desde aplicación web. Incluye búsqueda, visualización, descarga. Control acceso basado en roles y permisos específicos por documento.

#### Escenario: Búsqueda Avanzada
- GIVEN abogado autenticado
- WHEN realiza búsqueda avanzada
- THEN sistema retorna resultados filtrados
- AND ordena por relevancia

#### Escenario: Visualización Previa
- GIVEN abogado con permiso
- WHEN solicita vista previa
- THEN sistema muestra PDF embebido
- AND permite anotaciones

## Requisitos ELIMINADOS

### Requisito: Registro Manual de Documentos
(Reason: Automatización completa de ingreso documental)