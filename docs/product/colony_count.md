# Conteo preliminar de colonias

## Comportamiento de la versión 0.6.0

El flujo oficial de dos imágenes conserva en `prediction.feature_summary.colony_count` un conteo preliminar obtenido de las regiones candidatas que ya detecta el segmentador Petri. No se ha añadido un detector entrenado ni se ha demostrado exactitud biológica del conteo.

El objeto incluye `status`, `estimated_count`, `candidate_region_count`, `visible_region_count`, `coverage_fraction`, `reason_codes`, `warnings`, `method_version` y `validation_status`. La predicción original y sus mediciones no se sobrescriben al revisar la muestra.

- `preliminary`: hay un conteo de regiones interpretable según las reglas actuales, pendiente de revisión experta.
- `not_countable`: el conteo automático se suspende y `estimated_count` es null. Esto no equivale a cero ni a ausencia de crecimiento.
- Un análisis histórico sin ese objeto no recibe un conteo retrospectivo.

La evaluación suspende el conteo cuando falta segmentación fiable, límite de placa, enfoque, exposición o cobertura válida; también ante crecimiento conectado, cobertura >=45 % o más de 300 regiones. Estos umbrales son políticas heurísticas iniciales, no criterios microbiológicos validados.

El conteo usa todas las regiones detectadas, aunque la superposición existente muestre solo las 80 mayores. El redimensionado a 1200 píxeles y el área mínima del segmentador pueden omitir colonias pequeñas. Regiones pegadas, polvo, burbujas y reflejos pueden alterar el resultado. Una región no demuestra una colonia viable ni una unidad formadora de colonias.

## Revisión manual y atribución

`POST /api/v1/analysis-runs/{id}/reviews` admite `reviewed_colony_count`, un entero opcional entre 0 y 100000. Cero significa que el especialista verificó cero colonias; null significa que no confirmó un conteo. Una muestra rechazada como inválida no puede tener conteo confirmado. Es posible registrar un conteo aunque la identidad morfológica sea inconclusa, siempre que el especialista pueda contar la placa.

La identidad se obtiene de la sesión: `reviewer_user_id` y el nombre de usuario histórico. El campo antiguo `reviewer_name` se acepta por compatibilidad, pero no determina la identidad. Las revisiones históricas mantienen reviewer_user_id null: no se inventa una identidad a partir de un nombre libre.

El resultado manual aparece en el detalle consolidado y la API de revisiones. La revisión final puede sustituirse por otra conservando el historial. El conteo automático permanece junto a la evidencia original.

No se calcula UFC/mL: faltan protocolos validados de dilución, volumen sembrado, réplicas y reglas de aceptación del laboratorio. No deben inferirse esos datos desde la fotografía.

## Integridad y límites

Las muestras, ambas imágenes, ejecución y predicción se escriben dentro de un Unit of Work. Cualquier fallo antes del commit revierte esas filas y solicita borrar los archivos guardados. La versión del motor es metadato compartido y puede permanecer registrada aunque una muestra falle.

La compensación es una protección ante excepciones normales; no constituye una transacción distribuida entre PostgreSQL y disco. Un corte de proceso, fallo de limpieza o resultado incierto del commit requiere recuperación. Antes de producción se necesita reconciliación de archivos, política de retención y pruebas de restauración.

La API lee cada imagen por bloques hasta el límite de 20 MiB por defecto. El parser multipart puede haber recibido o almacenado el cuerpo antes de esa lectura: el límite del gateway también es necesario. Nginx admite 41 MiB totales para las dos imágenes y metadatos. Si se cambia MAX_UPLOAD_SIZE_MB, también debe ajustarse el límite total del gateway. El validador limita a 25 millones de píxeles por imagen. Las operaciones de visión, disco y base de datos se ejecutan en threadpool desde la ruta async; esto no es una cola de trabajo ni asegura capacidad ilimitada.

Nginx limita intentos de login por IP a cinco por minuto con ráfaga adicional de cinco, devolviendo 429. Esta defensa solo aplica al gateway. Un proxy externo necesita configuración confiable de IP real; sin ella, varios usuarios pueden compartir un límite. Falta defensa por cuenta y se mantiene como tarea de endurecimiento.

## Verificación de esta entrega

Se ejecutaron 21 pruebas aisladas con unittest y 6 comprobaciones del cliente API con el transformador TypeScript de Node. Las pruebas de aplicación usan dependencias inyectadas; no sustituyen PostgreSQL ni OpenCV. Se comprobó sintaxis Python y consistencia del diff.

También se añadieron regresiones a pytest/API y Vitest. Las suites completas, el build Vite, Nginx y las migraciones deben verificarse en CI antes de integrar; las dependencias externas no estaban disponibles para esa ejecución local. Los tests sintéticos no prueban precisión científica.

Comandos para un entorno con dependencias:

```bash
pip install -e ".[dev]"
pytest -v
python scripts/check_postgres_migrations.py
cd frontend
npm install
npm run check
```

Comprobaciones aisladas:

```bash
PYTHONPATH=src python -m unittest discover -s tests/review_checks -v
node scripts/check_session_client.mjs
```

El segundo comando requiere Node 22.13+ o 24 y utiliza una API experimental; es una comprobación auxiliar, no un reemplazo del compilador del proyecto.
