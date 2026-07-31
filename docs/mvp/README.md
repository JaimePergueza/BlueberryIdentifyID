# BlueberryMicroID — MVP demostrable

## 1. Objetivo

Entregar un sistema web funcional que reciba una fotografía de caja Petri y una imagen microscópica de la misma muestra de arándano, genere una clasificación visual preliminar explicable, permita la revisión de un especialista y conserve la trazabilidad completa del proceso.

El sistema es una herramienta de apoyo no diagnóstica. No identifica de forma definitiva género o especie y no sustituye la evaluación microbiológica de un experto.

## 2. Recorrido oficial del producto

1. El usuario inicia sesión.
2. Registra o identifica una muestra.
3. Carga una imagen Petri y una imagen microscópica de la misma muestra.
4. El sistema valida y almacena ambas imágenes.
5. El motor clásico de procesamiento visual genera un resultado preliminar.
6. El sistema muestra categoría, confianza técnica, explicación, calidad y advertencias.
7. Un especialista confirma, corrige, marca como no concluyente o rechaza la muestra.
8. El resultado automático y la revisión humana quedan disponibles en el historial.

El endpoint principal del recorrido es:

```http
POST /api/v1/analysis/two-image-upload
```

## 3. Funcionalidades obligatorias

- Autenticación básica con roles de administrador y especialista.
- Carga conjunta de imagen Petri e imagen microscópica.
- Validación de tipo, contenido, tamaño y legibilidad de archivos.
- Persistencia de muestra, imágenes, ejecución y predicción.
- Resultado preliminar explicable y claramente no diagnóstico.
- Revisión humana auditable.
- Resultado final que diferencie predicción automática y decisión experta.
- Historial consultable por código de muestra, fecha, estado y resultado.
- Visualización protegida de las imágenes almacenadas.
- Despliegue reproducible y modo local para demostración.
- Datos y archivos controlados para una demostración repetible.

## 4. Fuera de alcance para la entrega

- Identificación taxonómica definitiva de género o especie.
- Entrenamiento científico definitivo de YOLO u otro modelo profundo.
- Afirmaciones de precisión clínica, diagnóstica o microbiológica no validadas.
- Aplicación móvil.
- Procesamiento masivo de muestras.
- Nuevas fases experimentales de dataset que no sean necesarias para el recorrido principal.
- Automatización de decisiones sin revisión humana.

## 5. Pantallas mínimas

1. Inicio de sesión.
2. Dashboard operativo.
3. Nuevo análisis.
4. Resultado preliminar.
5. Revisión humana.
6. Historial de análisis.
7. Detalle y trazabilidad de una muestra.

## 6. Criterios de finalización

El MVP se considera terminado cuando:

- El recorrido completo puede ejecutarse desde la interfaz sin utilizar Swagger.
- Las imágenes y resultados permanecen después de reiniciar los servicios.
- El resultado automático nunca se presenta como diagnóstico definitivo.
- La revisión humana puede confirmar o modificar el resultado sin sobrescribir la predicción original.
- El historial muestra de forma clara el resultado preliminar, la revisión y el resultado final.
- Los errores se presentan de forma comprensible y no exponen trazas internas.
- El sistema puede iniciarse localmente con instrucciones reproducibles.
- Existe una demostración preparada que no depende de buscar imágenes ni datos durante la exposición.
- Las pruebas críticas del backend y del recorrido de usuario pasan.

## 7. Orden de implementación

### Sprint 0 — Estabilización

- Congelar el alcance del MVP.
- Unificar documentación y comportamiento del motor de análisis.
- Auditar el recorrido principal y sus pruebas.
- Definir backlog, ramas y criterios de aceptación.

### Sprint 1 — Backend del producto

- Endpoints de historial, búsqueda y detalle.
- Acceso seguro a imágenes.
- Estadísticas básicas para dashboard.
- Contratos consistentes de error y paginación.

### Sprint 2 — Frontend base

- Proyecto web en React y TypeScript.
- Diseño, navegación, login y carga de imágenes.
- Resultado preliminar y manejo de errores.

### Sprint 3 — Revisión y trazabilidad

- Revisión humana.
- Resultado final.
- Historial, filtros y detalle de análisis.
- Roles y protección de rutas.

### Sprint 4 — Operación y presentación

- Dockerización completa.
- Datos de demostración.
- Pruebas de extremo a extremo.
- Despliegue y manual de operación.
- Guion y respaldo para la presentación.

## 8. Historial y trazabilidad API

El frontend del MVP consulta `GET /api/v1/analysis-runs` para un historial
paginado, ordenado de forma estable y filtrable por código de muestra, estado,
revisión, resultado preliminar, resultado final y rango de fechas. El detalle
consolidado está en `GET /api/v1/analysis-runs/{analysis_run_id}/detail`.

El resultado preliminar conserva la `Prediction` automática original. El
resultado final solo se deriva de la revisión humana final vigente; una
corrección nunca sobrescribe la predicción. Ambos contratos omiten rutas
internas y `file_path`. La especificación y ejemplos están en
[`docs/api/analysis_history.md`](../api/analysis_history.md).

## 9. Regla de trabajo

Cada cambio funcional se desarrolla en una rama independiente, se entrega mediante pull request y debe incluir pruebas y criterios de aceptación verificables. `main` debe permanecer estable y demostrable.
