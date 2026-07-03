# ARCHITECTURE.md — BlueberryMicroID

## 1. Propósito del sistema

**BlueberryMicroID** es una plataforma de apoyo al reconocimiento preliminar de microorganismos asociados a **arándanos (blueberry)**, único producto soportado en esta etapa, a partir de dos fuentes visuales por muestra:

1. **Imagen de caja Petri** ("imagen macro" solo por convención de escala): fotografía de la **caja Petri** donde se observa el crecimiento (colonia) del microorganismo. **En ningún caso** es una fotografía del fruto (arándano) ni de su apariencia externa — ese tipo de análisis está fuera de alcance de este proyecto.
2. **Imagen micro**: fotografía obtenida por **microscopio** de la muestra tomada de esa misma caja Petri.

La inferencia multimodal del sistema se basa exclusivamente en la combinación **imagen de caja Petri + imagen microscópica** de una misma muestra. El sistema clasifica cada muestra en categorías visuales preliminares, calcula una confianza técnica (no diagnóstica) y permite que un experto humano confirme, corrija o marque el caso como no concluyente. Todo resultado queda trazado: muestra → imágenes → ejecución de análisis → predicción → modelo/versión → revisión humana.

No es un sistema de diagnóstico clínico. **No afirma identificación taxonómica exacta (especie/género) sin dataset, protocolo y validación de expertos.** Es una herramienta de apoyo y de construcción progresiva de dataset.

## 2. Estilo arquitectónico

Clean Architecture / Ports & Adapters, con 5 capas explícitas dentro de `src/blueberry_microid/`:

```
interfaces/   → adaptadores de entrada (API HTTP)
application/  → casos de uso + puertos (interfaces abstractas)
domain/       → entidades y reglas de negocio puras
infrastructure/ → adaptadores de salida (DB, storage, colas)
ml/           → adaptador de salida especializado (motor de inferencia)
```

Regla de dependencia: las flechas de importación siempre apuntan hacia adentro (`interfaces → application → domain`). `infrastructure` y `ml` dependen de `domain`/`application` (implementan sus puertos), nunca al revés.

## 3. Estructura de carpetas

```
BlueberryMicroID/
├── src/blueberry_microid/
│   ├── domain/
│   │   ├── entities/          # Sample, PetriImage, MicroImage, ModelVersion, AnalysisRun, Prediction, HumanReview
│   │   ├── value_objects/     # SampleCode, ConfidenceScore
│   │   ├── enums/              # ModelType, AnalysisStatus, PredictedLabel, ReviewDecision
│   │   ├── repositories/       # (opcional, si se prefiere ubicar puertos de persistencia aquí)
│   │   └── exceptions/         # EmptySampleCodeError, UnsupportedProductError, etc.
│   │
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── sample/          # CreateSampleUseCase, GetSampleByIdUseCase, GetSampleBySampleCodeUseCase
│   │   │   ├── petri_image/     # RegisterPetriImageUseCase
│   │   │   ├── micro_image/     # RegisterMicroImageUseCase
│   │   │   ├── inference/       # CreateAnalysisRunUseCase, GetAnalysisRunUseCase, ProcessAnalysisRunUseCase, GetPredictionForAnalysisRunUseCase
│   │   │   ├── model_version/   # CreateModelVersionUseCase, ListModelVersionsUseCase
│   │   │   └── review/          # SubmitHumanReview, GetFinalHumanReview, ListHumanReviews
│   │   ├── ports/                # repositorios + ImageStoragePort + ImageValidatorPort + InferenceEnginePort + UnitOfWorkPort
│   │   ├── dto/                  # Request (entrada) + DTO (salida) por entidad, con from_entity(); ProcessAnalysisRunResult
│   │   ├── exceptions.py         # Errores de orquestación: NotFound*, Duplicate*, InvalidImageError...
│   │   └── services/             # ImageIntakeService (validar+guardar+limpiar, compartido por ambos upload use cases)
│   │
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models/           # Modelos SQLAlchemy (Fase 1) + column_types.py (PortableJSON, Fase 4)
│   │   │   ├── repositories/     # Sqlalchemy*Repository (Fase 2, +Prediction en Fase 4) + mappers.py (ORM -> entidad)
│   │   │   └── session/          # create_db_engine, create_session_factory, SqlAlchemyUnitOfWork (repos internos desde Fase 4)
│   │   ├── storage/               # LocalImageStorage + PillowImageValidator (Fase 2; validación estricta desde Fase 3.5)
│   │   ├── tasks/                  # Celery app + task de procesamiento mock asíncrono (Fase 7)
│   │   ├── config/                 # Settings (pydantic-settings): DATABASE_URL, MAX_UPLOAD_SIZE_MB, LOG_LEVEL/LOG_FORMAT...
│   │   └── logging/                 # configure_logging, RequestLoggingMiddleware, formatters (Fase 3.5)
│   │
│   ├── ml/
│   │   ├── preprocessing/          # Normalización, resize, denoise (caja Petri y microscopía) — todavía vacío
│   │   ├── petri_branch/            # Extracción de features de la imagen de caja Petri — todavía vacío
│   │   ├── micro_branch/            # Extracción de features de la imagen microscópica — todavía vacío
│   │   ├── fusion/                   # Fusión tardía de features macro+micro — todavía vacío
│   │   ├── inference_engine/          # MockInferenceEngine (Fase 4) — implementación del InferenceEnginePort
│   │   ├── model_registry/             # Metadata/versionado de modelos — todavía vacío
│   │   ├── contracts/                  # TrainingManifest / TrainingRunResult (Fase 11, sin entrenamiento)
│   │   ├── configs/                    # TrainingConfig futuro (Fase 11)
│   │   ├── data/                       # DatasetLoaderPort + loader JSON de manifests (Fase 11)
│   │   ├── validation/                 # Validadores de manifest/rutas (Fase 11)
│   │   ├── reports/                    # ManifestValidationReport (Fase 11)
│   │   └── training/                   # TrainerPort, train() no implementado aún (Fase 11)
│   │
│   └── interfaces/
│       ├── api/
│       │   ├── app.py            # create_app() -> FastAPI (Fase 3)
│       │   ├── error_handlers.py # Traduce excepciones de dominio/aplicación a JSON + status HTTP (Fase 3)
│       │   ├── middlewares/       # (vacío; el manejo de errores vive en error_handlers.py, no aquí)
│       │   └── v1/
│       │       ├── routers/        # samples, model_versions, petri_images, micro_images, analysis_runs, human_reviews
│       │       ├── schemas/         # Pydantic request/response (+process/prediction y human review)
│       │       └── dependencies.py   # Composition root: settings, sesión DB, repos, storage, motor de inferencia, UoW, casos de uso
│
├── alembic/                # Migraciones de base de datos
├── tests/
│   ├── unit/                # domain + application (sin IO real)
│   ├── integration/          # infrastructure (SQLite real, sin PostgreSQL)
│   ├── api/                  # FastAPI TestClient + SQLite compartida (StaticPool) + storage temporal
│   └── fixtures/images/{petri,micro}/
├── storage/                # Almacenamiento local de imágenes en desarrollo
├── scripts/
│   ├── check_postgres_migrations.py  # Valida Alembic contra Postgres real; falla fuerte y claro si no hay conexión (Fase 3.5)
│   └── api_smoke_test.py               # Camino feliz end-to-end contra un servidor real, sin datasets externos (Fase 3.5)
├── docker-compose.yml       # PostgreSQL + Redis (broker/backend Celery local desde Fase 7)
├── docs/
│   └── development.md        # venv, instalación, Docker, migraciones, logging, límites, smoke test, tests
├── pyproject.toml            # Dependencias formales del proyecto (Fase 3)
├── .env.example
├── CLAUDE.md
├── ARCHITECTURE.md
└── README.md
```

## 4. Modelo de dominio (Fase 1 — implementado)

Entidades principales y su relación (ver [docs/domain-model.md](docs/domain-model.md) si se amplía en el futuro; por ahora documentadas en el propio código de `domain/entities/`):

- **Sample** (muestra): `sample_code` único, `product` (debe ser `blueberry`), `lot_code`, `origin`, `collection_date`, `notes`, timestamps. Puede tener varias `PetriImage` y varias `MicroImage`.
- **PetriImage**: pertenece a un `Sample`. Metadata del archivo (ruta, nombre, mime type, tamaño, dimensiones) + metadata de cultivo/crecimiento observado en la caja Petri (medio de cultivo, temperatura/tiempo de incubación, fecha de siembra, color/forma/borde/textura de colonia observados). **Nunca** representa una foto externa del arándano.
- **MicroImage**: pertenece a un `Sample`. Metadata del archivo + metadata de microscopía (aumento, tipo de microscopio, método de tinción/preparación, estructuras observadas en texto libre, sin taxonomía).
- **ModelVersion**: identifica una versión de motor de inferencia (`name`, `version`, `model_type`: `mock` | `pytorch` | `external`, `is_active`). Existe incluso mientras el motor es simulado.
- **AnalysisRun**: una ejecución concreta de análisis multimodal. Referencia exactamente **un** `Sample`, **una** `PetriImage`, **una** `MicroImage` y **un** `ModelVersion`. Invariante de dominio: la `PetriImage` y la `MicroImage` referenciadas deben pertenecer al mismo `Sample`; esto se valida en el momento de crear el `AnalysisRun` (no a nivel de UI). Estados: `pending`, `processing`, `completed`, `failed`, `needs_review` — estos son estados de **flujo de trabajo**, no clases microbiológicas. Desde la Fase 4, la propia entidad expone `mark_processing()`/`mark_completed()`/`mark_needs_review()`/`mark_failed(error_message)`, cada uno validando la transición de origen permitida (ver § 16).
- **Prediction**: resultado preliminar de un `AnalysisRun` (relación 1—1: cada ejecución produce como máximo una predicción; una re-ejecución crea un nuevo `AnalysisRun`). Etiqueta preliminar (`no_evident_growth`, `suspicious_growth`, `probable_fungal_growth`, `probable_bacterial_growth`, `inconclusive`), confianza opcional (0–1), probabilidades por clase opcionales, observación técnica en texto libre, y bandera `requires_human_review`. Desde la Fase 4 se crea realmente, vía `ProcessAnalysisRunUseCase` (ver § 16) — antes solo existía en el esquema, sin caso de uso que la generara.
- **HumanReview**: revisión de un `AnalysisRun` por un experto. Decisión (`confirmed`, `corrected`, `marked_inconclusive`, `rejected_invalid_sample`), etiqueta corregida (obligatoria si `corrected`), comentarios. No sobrescribe la `Prediction` original — coexisten para trazabilidad y auditoría. Se permite más de una revisión por `AnalysisRun` en el tiempo.

Un `AnalysisRun` **nunca** se ejecuta implícitamente sobre "todas las imágenes" de una muestra: siempre referencia una imagen Petri y una imagen micro concretas, elegidas explícitamente.

## 5. Flujo end-to-end

```
1. RegisterSample          → crea Sample
2. UploadPetriImage        → valida y almacena imagen de caja Petri (asociada al Sample)
3. UploadMicroImage        → valida y almacena imagen microscópica (asociada al Sample)
4. CreateAnalysisRun       → referencia Sample + 1 PetriImage + 1 MicroImage + ModelVersion
                              (valida que ambas imágenes pertenezcan al mismo Sample)
5. ProcessAnalysisRun      → pending → processing → motor de inferencia (hoy: simulado) →
                              Prediction + AnalysisRun completed/needs_review, o failed si el motor falla
6. SubmitHumanReview       → experto confirma/corrige/marca no concluyente/rechaza muestra inválida
```

**Los pasos 1–6 ya están expuestos por HTTP** (Fase 3 para 1–4, Fase 4 para 5, Fase 5 para 6, Fase 7 para cola asíncrona — ver § 14, § 16, § 18 y § 22). El paso 5 puede correr de forma **síncrona** dentro del propio request HTTP (`POST /analysis-runs/{id}/process`) o de forma asíncrona con Celery (`POST /analysis-runs/{id}/process-async`), sin preprocesamiento real de imágenes ni fusión de features — el motor sigue siendo una simulación determinista (ver § 16). La revisión humana no sobrescribe la `Prediction`: agrega registros `HumanReview` auditables y marca una revisión final vigente.

## 6. Puertos (`application/ports/`) — implementados por fases

- `SampleRepositoryPort`, `PetriImageRepositoryPort`, `MicroImageRepositoryPort`, `ModelVersionRepositoryPort` (incluye `list_all()`, añadido en Fase 3 para el endpoint de listado), `AnalysisRunRepositoryPort` (incluye `update()` y `claim_for_processing()`), `PredictionRepositoryPort` (Fase 4), `HumanReviewRepositoryPort` (Fase 5) — cada uno con `add`, `get_by_id`, y métodos de consulta/listado donde aplica. Implementados por `Sqlalchemy*Repository` en `infrastructure/db/repositories/`.
- `ImageStoragePort` (`save(category, original_file_name, content) -> file_path`, `delete(path) -> None`) — implementado por `LocalImageStorage` (filesystem, `storage/petri_images/` y `storage/micro_images/` separados; nombre final siempre UUID, nunca el nombre original). `delete` es idempotente: borrar una ruta ya inexistente no es un error.
- `ImageValidatorPort` (`validate(file_name, mime_type, content) -> ImageValidationResult`) — implementado por `PillowImageValidator` (tamaño > 0, MIME/extensión permitidos, imagen decodificable sin corrupción, dimensiones, y desde la Fase 3.5 también que el formato real detectado por Pillow concuerde con el MIME declarado y con la extensión — ver § 15).
- `InferenceEnginePort` (Fase 4, `application/ports/inference_engine.py`) — `process(analysis_run, petri_image, micro_image, model_version) -> InferenceOutput`. Implementado hoy únicamente por `MockInferenceEngine` (`ml/inference_engine/`), una simulación determinista — ver § 16.
- `UnitOfWorkPort` (Fase 2.5, extendido en Fases 4 y 5) — implementado por `SqlAlchemyUnitOfWork`. Consumidores reales: `ProcessAnalysisRunUseCase` y `SubmitHumanReviewUseCase` — ver § 16 y § 18.

## 7. Persistencia

- PostgreSQL como base de datos principal. `docker-compose.yml` (raíz del repo) levanta un Postgres 16 y un Redis 7 locales para desarrollo (ver § 13 y `docs/development.md`).
- SQLAlchemy como ORM, Alembic para migraciones versionadas (nunca modificar el esquema directamente en producción). La cadena de conexión se lee de `DATABASE_URL` vía `infrastructure/config/settings.py`, nunca hardcodeada.
- `pgvector` queda contemplado en el diseño (columna de embeddings a futuro en `PetriImage`/`MicroImage` o en una tabla de features) pero **no se activa en el MVP** hasta que exista un caso de uso real de búsqueda por similitud.

## 8. Procesamiento asíncrono (Fase 7)

- Redis está provisionado por `docker-compose.yml` y se usa como broker/result backend de Celery en desarrollo local.
- `src/blueberry_microid/infrastructure/tasks/celery_app.py` crea `celery_app` desde `Settings`, con JSON como único formato aceptado (`accept_content=["json"]`) y cola `analysis`.
- `src/blueberry_microid/infrastructure/tasks/analysis_tasks.py` define `process_analysis_run_task(analysis_run_id: str)`, convierte a `UUID`, construye repositorios SQLAlchemy reales, `SqlAlchemyUnitOfWork` y `MockInferenceEngine`, y llama al mismo `ProcessAnalysisRunUseCase` del endpoint síncrono.
- `POST /api/v1/analysis-runs/{id}/process-async` encola la task y devuelve `202 Accepted`; no ejecuta inferencia dentro del request.
- `GET /api/v1/tasks/{task_id}` expone estado auxiliar de Celery sin traceback. La fuente durable de verdad sigue siendo `AnalysisRun` y `Prediction`.
- No hay preprocesamiento pesado, reentrenamiento, PyTorch ni IA real.

## 9. Observabilidad (implementado en Fase 3.5 — ver § 15)

- Logging estructurado con la librería estándar (`logging`), no `structlog` ni ningún servicio externo — ver `infrastructure/logging/`. Cada línea incluye `timestamp`, `level`, `request_id`, `method`, `path`, `status_code`, `duration_ms` y, si aplica, `exception_type`.
- Todo error 5xx se loguea en servidor con traza completa (`exc_info`); el cliente nunca recibe esos detalles, solo un mensaje genérico y el `code` correspondiente.
- `request_id` viaja como header `X-Request-ID` en toda respuesta (éxito o error), reutilizando el que envíe el cliente si lo hace.
- Pendiente: correlacionar `sample_id`/`analysis_run_id` en las líneas de log de cada caso de uso (hoy el log estructurado es exclusivamente a nivel de request HTTP, no dentro de `application/`).

## 10. Preparación para el futuro (sin implementarlo ahora)

- Sustituir el motor de inferencia simulado por modelos PyTorch reales (uno por rama: macro y micro) sin tocar capas superiores.
- Incorporar Cellpose u otro modelo especializado en segmentación de estructuras microscópicas dentro de `ml/micro_branch/`.
- Activar `pgvector` para búsqueda de muestras visualmente similares.
- Ampliar el catálogo de clases una vez exista dataset validado por expertos, sin romper compatibilidad con resultados históricos (versionado de taxonomía de clases).

## 11. Límites explícitos del sistema (declaración de alcance)

- El sistema no determina especie ni género microbiológico; no afirma identificación taxonómica exacta sin dataset, protocolo y validación de expertos.
- El sistema no reemplaza el criterio de un microbiólogo.
- Ninguna métrica de desempeño (accuracy, precisión, etc.) se muestra sin evaluación real documentada.
- La imagen "macro" es siempre y únicamente de la caja Petri, nunca del fruto (arándano). El sistema no analiza la apariencia externa del arándano.
- El único producto soportado en esta etapa es arándano (blueberry).
- `POST /api/v1/analysis-runs` únicamente registra una solicitud de análisis en estado `pending` — no ejecuta nada. Desde la Fase 4, `POST /api/v1/analysis-runs/{id}/process` sí ejecuta un motor de inferencia y crea una `Prediction`; desde la Fase 7, `POST /api/v1/analysis-runs/{id}/process-async` encola esa misma operación en Celery. En ambos casos el motor es **exclusivamente `MockInferenceEngine`**: una simulación determinista que nunca abre ni analiza el contenido real de las imágenes, no usa PyTorch/OpenCV/Cellpose, y no tiene validez diagnóstica — ver § 16 y § 22.

## 12. Fase 2 — capa de aplicación, persistencia y almacenamiento (implementada)

Objetivo cumplido: registrar muestras, registrar imágenes de caja Petri y microscópicas, y preparar un `AnalysisRun` pendiente — todo sin API HTTP, sin Celery y sin inferencia real.

**Casos de uso** (`application/use_cases/`): `CreateSampleUseCase`, `RegisterPetriImageUseCase`, `RegisterMicroImageUseCase`, `CreateAnalysisRunUseCase`, `CreateModelVersionUseCase`. Cada uno depende únicamente de puertos (constructor injection), nunca de SQLAlchemy, Pillow ni del sistema de archivos directamente.

**Excepciones de aplicación** (`application/exceptions.py`): distintas de las excepciones de dominio (§ ver CLAUDE.md). Cubren "no encontrado" (`SampleNotFoundError`, `PetriImageNotFoundError`, `MicroImageNotFoundError`, `ModelVersionNotFoundError`, `AnalysisRunNotFoundError`), "conflicto" (`DuplicateSampleCodeError`, `DuplicateModelVersionError`) y validación de archivos (`InvalidImageError`, `InvalidModelTypeError`, `ImageStorageError`).

**Repositorios SQLAlchemy** (`infrastructure/db/repositories/`): un archivo por puerto, más `mappers.py` con funciones `*_to_entity` que convierten modelo ORM → entidad de dominio. Ningún repositorio devuelve un modelo SQLAlchemy a la capa de aplicación.

**Decisión: sin Unit of Work todavía.** Cada método `add()` de cada repositorio hace su propio `commit()`/`rollback()`. Se evaluó introducir un Unit of Work (sesión compartida entre repositorios con un solo commit), pero ningún caso de uso de la Fase 2 escribe en más de un agregado por invocación (`CreateAnalysisRunUseCase` solo lee de cuatro repositorios y escribe en uno). Se documenta como pendiente: si una futura fase necesita atomicidad multi-agregado (p. ej. crear `AnalysisRun` + `Prediction` en la misma transacción), introducir un `UnitOfWorkPort` en `application/ports/` antes de escribir esa lógica.

**Manejo de duplicados:** `SampleModel.sample_code` y `ModelVersionModel.(name, version)` tienen `UniqueConstraint` a nivel de base de datos. Los repositorios capturan `sqlalchemy.exc.IntegrityError` en el `commit()` y la traducen a `DuplicateSampleCodeError`/`DuplicateModelVersionError` — la capa de aplicación nunca ve una excepción de SQLAlchemy.

**Almacenamiento de imágenes** (`infrastructure/storage/local_image_storage.py`): `LocalImageStorage` escribe en `storage/petri_images/` o `storage/micro_images/` según `ImageCategory`. El nombre final es siempre `uuid4().hex + extensión`; el nombre original solo se usa (de forma segura, vía `Path.suffix`) para recuperar la extensión, nunca para construir la ruta — elimina cualquier riesgo de colisión o path traversal.

**Validación de imágenes** (`infrastructure/storage/pillow_image_validator.py`): `PillowImageValidator` valida, en orden, tamaño > 0, MIME permitido, extensión permitida, y decodificación exitosa con Pillow (`Image.verify()` + reapertura para leer dimensiones, porque `verify()` invalida el objeto para lecturas posteriores). Constantes `ALLOWED_MIME_TYPES`/`ALLOWED_EXTENSIONS` viven en `application/ports/image_validator.py` como única fuente de verdad, reutilizadas también por `LocalImageStorage`.

**Estrategia de testing** (ver `tests/unit/application/` y `tests/integration/db/`):
- Tests unitarios de casos de uso usan dobles en memoria (`tests/unit/application/fakes.py`) para los repositorios y el storage — rápidos, sin base de datos. `PillowImageValidator` se usa directamente (no se mockea) porque es cómputo puro determinista, no I/O externo.
- Tests de integración de repositorios usan **SQLite en memoria** (`tests/integration/db/conftest.py`). Desde la Fase 2.5 también se incluye la tabla `human_reviews` (no depende de `JSONB`); desde la Fase 4 también se incluye `predictions` gracias a `PortableJSON`, que compila a `JSONB` en PostgreSQL y a `JSON` genérico en SQLite.
- **PostgreSQL sigue siendo la base de datos real del proyecto** (ver §7). SQLite es exclusivamente un atajo de testing para no requerir una instancia de Postgres en CI; no se usa en desarrollo ni en producción, y no se han validado en SQLite las columnas `Enum` nativas de Postgres ni las políticas de `ON DELETE` — deben verificarse contra Postgres antes de producción (ver riesgos).

## 13. Fase 2.5 — endurecimiento técnico (implementada)

Objetivo: corregir riesgos identificados al cierre de la Fase 2 antes de construir la API — todavía sin routers, sin Celery, sin inferencia real.

**Consistencia storage/base de datos (archivos huérfanos).** `ImageStoragePort` ganó un método `delete(path) -> None`, idempotente (borrar una ruta inexistente no es error), implementado por `LocalImageStorage.delete` con `Path.unlink(missing_ok=True)`. La lógica de "validar → guardar → construir entidad → persistir" de `RegisterPetriImageUseCase` y `RegisterMicroImageUseCase` se extrajo a un servicio compartido, `application/services/image_intake_service.py` (`ImageIntakeService`), para no duplicarla entre ambos casos de uso. Cada caso de uso envuelve la llamada al repositorio en un `try/except Exception` deliberadamente amplio (no se puede predecir de antemano qué tipo de error lanzará una implementación concreta del repositorio): si falla, se invoca `image_intake.cleanup(file_path)` para borrar el archivo recién guardado y luego se re-lanza el error original sin modificarlo (`raise` desnudo). Si el borrado compensatorio también falla, se lanza `ImageStorageCompensationError` encadenada (`raise ... from repository_error`), de modo que el error original queda disponible en `__cause__` — nunca se pierde contexto.

**Tamaño real de archivo.** Se decidió **no confiar en absoluto en `file_size_bytes` declarado**: `ImageIntakeService.validate_and_store` calcula `len(content)` y, si no coincide exactamente con el valor declarado, rechaza la operación con `InvalidImageError` antes de tocar el storage o la base de datos (fail-fast). Si coincide, el valor persistido siempre es el calculado internamente (`actual_size`), nunca el argumento de entrada tal cual. Se prefirió el rechazo explícito sobre "ignorar silenciosamente" el campo declarado, porque mantener un parámetro de entrada que la implementación descarta sin avisar habría sido una API confusa para la futura capa HTTP.

**Configuración por entorno.** `infrastructure/config/settings.py` usa `pydantic-settings` (ya estaba disponible en el entorno; ver `CLAUDE.md`) para `Settings(BaseSettings)`, con lectura de variables reales de entorno y fallback a un archivo `.env` (ver `.env.example`, nunca versionado — ya cubierto por `.gitignore`). El valor por defecto de `storage_root` **no** es una ruta absoluta hardcodeada ni depende del directorio de trabajo del proceso: se calcula como `Path(__file__).resolve().parents[4] / "storage"`, anclado a la ubicación del paquete instalado, así que ejecutar tests o la futura API desde cualquier directorio resuelve siempre a la misma carpeta `storage/` del repositorio. `get_settings()` cachea una instancia por proceso (`lru_cache`); los tests construyen `Settings(...)` directamente para no depender del caché ni de variables de entorno reales del host.

**Docker Compose.** `docker-compose.yml` en la raíz define `postgres` (16-alpine, con healthcheck) y `redis` (7-alpine, todavía sin ningún consumidor — reservado para una fase futura con Celery). Variables de usuario/contraseña/base/puerto tienen defaults de desarrollo vía `${VAR:-default}`, sobreescribibles por entorno. Comandos documentados en `docs/development.md`.

**Estado real de Alembic/PostgreSQL — NO validado contra Postgres real.** El entorno de esta sesión no tiene Docker disponible (`docker: command not found`), así que no fue posible levantar un Postgres real ni ejecutar `alembic upgrade head` contra él. En su lugar se instaló Alembic (`pip install alembic`) y se ejecutó **validación offline**:

```
DATABASE_URL=postgresql+psycopg://... alembic upgrade head --sql
DATABASE_URL=postgresql+psycopg://... alembic downgrade head:base --sql
```

Esto genera el DDL real que Alembic emitiría para el dialecto PostgreSQL sin necesitar una conexión viva, y confirma que las migraciones `0001` y `0002` son sintácticamente válidas y reversibles (incluyendo el índice único parcial de `human_reviews`). **Esto no reemplaza una ejecución real contra Postgres** (no valida permisos, extensiones del servidor, ni comportamiento real de constraints con datos concurrentes). Antes de confiar en el esquema en cualquier entorno compartido, se debe ejecutar `docker compose up -d` seguido de `alembic upgrade head` (sin `--sql`) al menos una vez — ver `docs/development.md`.

**Unit of Work — Opción B preparada en Fase 2.5 y adoptada después.** Se creó `UnitOfWorkPort` (`application/ports/unit_of_work.py`) y `SqlAlchemyUnitOfWork` (`infrastructure/db/session/sqlalchemy_unit_of_work.py`), con tests de commit explícito, rollback implícito (no se llamó `commit()`) y rollback por excepción. En Fase 2.5 no se migraron los 5 repositorios existentes a usarlo porque ningún caso de uso escribía más de un agregado por invocación. Desde la Fase 4 lo usa `ProcessAnalysisRunUseCase` para persistir `Prediction` + estado final juntos; desde la Fase 5 lo usa `SubmitHumanReviewUseCase` para despromover la final anterior + insertar la nueva final de forma atómica.

**HumanReview.is_final.** Campo nuevo `is_final: bool` (default `True`) en la entidad de dominio y en `HumanReviewModel`. Regla de negocio: como mucho una revisión por `AnalysisRun` debe tener `is_final=True` en un momento dado; el resto son históricas. La entidad por sí sola no puede validar esto (es un invariante que abarca múltiples filas), así que se aplica con un **índice único parcial** a nivel de base de datos: `CREATE UNIQUE INDEX uq_human_reviews_one_final_per_run ON human_reviews (analysis_run_id) WHERE is_final = true` (migración `0002`), verificado tanto en el DDL generado para PostgreSQL como en un test de integración con SQLite (que también soporta índices parciales). Desde la Fase 5, `SubmitHumanReviewUseCase` despromueve la revisión final anterior y crea la nueva final en una sola transacción. No se modificó `Prediction`: sigue sin sobrescribirse nunca.

## 14. Fase 3 — API mínima con FastAPI (implementada)

Objetivo: exponer por HTTP los casos de uso ya existentes (Sample, PetriImage, MicroImage, ModelVersion, AnalysisRun), sin routers de inferencia, sin Celery, sin frontend y sin autenticación.

**`create_app()` como factoría, no un singleton global.** `interfaces/api/app.py` expone `create_app() -> FastAPI`. Construye el engine/session factory de SQLAlchemy y los guarda en `app.state` (no como variables de módulo), precisamente para que los tests puedan construir una app y reemplazar `app.state.engine` / `app.state.session_factory` / `app.state.settings` por una base SQLite temporal antes de emitir requests — ver `tests/api/conftest.py`. `create_engine()` es perezoso en SQLAlchemy, así que construir el engine con la URL de Postgres real de la configuración nunca falla solo porque no haya una base alcanzable en ese momento.

**Endpoints creados**, todos bajo `/api/v1` salvo el healthcheck:

| Método | Ruta | Caso de uso |
|---|---|---|
| GET | `/health` | — (no versionado) |
| POST | `/api/v1/samples` | `CreateSampleUseCase` |
| GET | `/api/v1/samples/{sample_id}` | `GetSampleByIdUseCase` (nuevo) |
| GET | `/api/v1/samples/by-code/{sample_code}` | `GetSampleBySampleCodeUseCase` (nuevo) |
| POST | `/api/v1/model-versions` | `CreateModelVersionUseCase` |
| GET | `/api/v1/model-versions` | `ListModelVersionsUseCase` (nuevo; requirió añadir `list_all()` a `ModelVersionRepositoryPort`) |
| POST | `/api/v1/samples/{sample_id}/petri-images` | `RegisterPetriImageUseCase` |
| POST | `/api/v1/samples/{sample_id}/micro-images` | `RegisterMicroImageUseCase` |
| POST | `/api/v1/analysis-runs` | `CreateAnalysisRunUseCase` |
| GET | `/api/v1/analysis-runs/{analysis_run_id}` | `GetAnalysisRunUseCase` (nuevo) |

La ruta `GET /api/v1/samples/by-code/{sample_code}` se registra **antes** que `GET /api/v1/samples/{sample_id}` en `samples.py`: FastAPI resuelve rutas en orden de registro, y si `{sample_id}` fuera primero, `"by-code"` se interpretaría como un intento de UUID y fallaría con un 422 en vez de llegar a la ruta correcta.

**Composición de dependencias (`interfaces/api/v1/dependencies.py`).** Es el único módulo de `interfaces/` que importa SQLAlchemy, `LocalImageStorage` y `PillowImageValidator` directamente — el punto de inyección explícitamente permitido por CLAUDE.md ("nunca directo a infrastructure/ salvo vía inyección de dependencias"). Cadena típica: `get_db_session` (una `Session` por request, leída de `request.app.state.session_factory`, cerrada al terminar) → `get_sample_repository` (envuelve la sesión en `SqlAlchemySampleRepository`) → `get_create_sample_use_case` (inyecta el repositorio en `CreateSampleUseCase`). Los routers solo importan funciones `get_*_use_case` y clases de caso de uso — nunca un repositorio o `Session` directamente. `application/` no importa `fastapi` en ningún archivo, y `Depends(...)` no aparece fuera de `interfaces/`.

**Tamaño real de archivo en la API.** Los routers de `petri_images.py`/`micro_images.py` hacen `content = await file.read()` y construyen el DTO con `file_size_bytes=len(content)` — el cliente nunca envía ese campo (no existe como parámetro `Form`/`File`); el `mime_type` viene de `UploadFile.content_type`, también real, nunca declarado aparte por el cliente. Esto es consistente con la decisión de Fase 2.5 (`ImageIntakeService` rechaza cualquier discrepancia entre tamaño declarado y real) — como la API siempre declara el tamaño que ella misma calculó, esa comprobación nunca puede fallar por esta vía, pero sigue protegiendo cualquier otro llamador futuro del caso de uso.

**Manejo centralizado de errores (`interfaces/api/error_handlers.py`).** Formato de respuesta: `{"error": {"code": "...", "message": "..."}}`. Detalle no obvio de Starlette: registrar un handler para la clase `Exception` a secas lo convierte en el *fallback* de `ServerErrorMiddleware` (el middleware más externo), que **responde y vuelve a lanzar la excepción** — pensado para que `TestClient(raise_server_exceptions=True)` siga mostrando errores inesperados en desarrollo. Si solo se registra así, cualquier excepción de aplicación (p. ej. `DuplicateSampleCodeError`) se propaga como excepción Python en vez de volver como JSON 409. La solución: registrar el mismo handler también para `ApplicationError` y `DomainError` (las dos superclases que cubren todo lo que lanzamos deliberadamente), lo que las enruta por el `ExceptionMiddleware` interno (responde sin re-lanzar). El registro en `Exception` se mantiene como último recurso para bugs genuinos no anticipados. Los tests de API usan `TestClient(app, raise_server_exceptions=False)` para poder inspeccionar cualquier respuesta 500 sin que la excepción interrumpa el test.

Tabla de mapeo (más específico primero):

| Excepción | HTTP | `code` |
|---|---|---|
| `SampleNotFoundError` / `PetriImageNotFoundError` / `MicroImageNotFoundError` / `ModelVersionNotFoundError` / `AnalysisRunNotFoundError` | 404 | `*_not_found` |
| `PredictionNotFoundError` / `HumanReviewNotFoundError` | 404 | `*_not_found` |
| `DuplicateSampleCodeError` / `DuplicateModelVersionError` | 409 | `duplicate_*` |
| `DuplicatePredictionError` / `DuplicateFinalHumanReviewError` | 409 | `duplicate_*` |
| `AnalysisRunNotReviewableError` | 409 | `analysis_run_not_reviewable` |
| `InvalidModelTypeError` | 422 | `invalid_model_type` |
| `MissingCorrectedLabelError` (dominio) | 422 | `invalid_human_review` |
| `InvalidImageError` | 400 | `invalid_image` |
| `CrossSampleAnalysisError` (dominio) | 400 | `image_sample_mismatch` |
| `ImageStorageCompensationError` | 500 | `image_storage_compensation_failed` |
| Cualquier otro `DomainError` | 400 | `domain_error` |
| Cualquier otro `ApplicationError` | 500 | `application_error` |
| Excepción no anticipada | 500 | `internal_error` |

Mensajes de error con status ≥ 500 nunca incluyen `str(exc)` (podría contener rutas de archivo u otros detalles internos, como en `ImageStorageCompensationError`); usan un mensaje genérico fijo. Mensajes con status < 500 sí devuelven `str(exc)`, porque son mensajes de regla de negocio pensados para el cliente (p. ej. "sample_code 'X' already exists"). **Importante:** este formato solo aplica a excepciones de dominio/aplicación. Los errores de validación básica de Pydantic/FastAPI (un campo faltante, un enum inválido como `model_type: "tensorflow"`) siguen devolviendo el formato por defecto de FastAPI (`{"detail": [...]}`) — no se sobreescribió ese comportamiento, ya que la tarea solo especificaba el mapeo para los errores propios.

**Sin routers de schemas JSON para subida de imágenes.** Los endpoints de imagen aceptan `multipart/form-data`, no JSON, así que los schemas `PetriImageCreate`/`MicroImageCreate` de la Fase 1 quedaron sin uso real y se eliminaron (código muerto); los routers usan parámetros `File(...)`/`Form(...)` individuales en vez de un modelo Pydantic para el cuerpo. Los schemas `PetriImageRead`/`MicroImageRead` sí se mantienen, para las respuestas.

**`SampleCreate` ya no acepta `product`.** En vez de exponer el campo con un validador que solo aceptaba `"blueberry"` (Fase 1), se eliminó por completo del schema: el cliente no puede ni ver la opción de cambiarlo. `CreateSampleUseCase` sigue fijándolo internamente.

**Dependencias formales (`pyproject.toml`).** Se eligió `pyproject.toml` sobre `requirements.txt` + `requirements-dev.txt` para tener una única fuente de verdad (evita que ambos archivos diverjan) y para que el proyecto sea instalable como paquete editable (`pip install -e ".[dev]"`), lo que permite que `import blueberry_microid` funcione en cualquier directorio sin manipular `sys.path` a mano — el `conftest.py` raíz que hacía eso manualmente en fases anteriores se eliminó por quedar redundante.

**Riesgo detectado y resuelto durante esta fase:** el entorno de trabajo (compartido con otras herramientas Python globales, p. ej. un servidor MCP que depende de `sse-starlette`) tenía versiones de `starlette` potencialmente incompatibles entre paquetes instalados globalmente. Instalar el proyecto con `pip install -e ".[dev]"` degradó `starlette` a una versión que rompía esa otra herramienta; se restauró la versión previa (`starlette==0.52.1`) y se verificó explícitamente que FastAPI 0.116.1 sigue funcionando correctamente con ella (aunque técnicamente fuera de su rango declarado) antes de continuar. No se usó un entorno virtual dedicado para este proyecto en esta sesión; **se recomienda crear uno (`python -m venv .venv`) antes de instalar dependencias de proyecto en cualquier máquina compartida**, para evitar este tipo de conflicto por completo.

## 15. Fase 3.5 — validación operativa y endurecimiento de API (implementada)

Objetivo: antes de avanzar a Celery/inferencia, corregir un reporte de tests inconsistente, formalizar el uso de `.venv`, intentar validar Alembic contra PostgreSQL real (o documentar honestamente que no se pudo), agregar logging estructurado, límite de tamaño de subida, validación estricta de formato real de imagen, y un smoke test operativo. Sin Celery, sin inferencia (ni real ni simulada), sin frontend, sin `Prediction`.

**Corrección del conteo de tests.** El resumen de la Fase 3 reportó dos sumas distintas para el mismo total: `52 + 27 = 79` (correcto) y, por separado, un desglose `18 + 21 + 18 + 27 = 84` (incorrecto). La causa: el conteo de `tests/integration/db/` se transcribió como `18` cuando en realidad eran `13`. No hubo tests duplicados ni categorías solapadas — es un error de transcripción en el texto del resumen, nunca reflejado en ningún archivo del repositorio (no había ninguna tabla de conteos incorrecta en `README.md`/`ARCHITECTURE.md` que corregir). El desglose correcto en ese momento era `18 + 21 + 13 + 27 = 79`. A cierre de esta fase, con los tests nuevos, el total real es:

```
python -m pytest tests --collect-only -q   →  102 tests collected
python -m pytest tests -v                  →  102 passed
```

Desglose verificado: `tests/unit/domain` (18) + `tests/unit/application` (21) + `tests/unit/infrastructure` (14) + `tests/integration/db` (13) + `tests/api` (36) = **102**. Ver `docs/development.md` § 10 para la tabla completa y el comando exacto usado para verificarlo.

**Entorno virtual formalizado.** `docs/development.md` § 1 documenta `python -m venv .venv` + activación (PowerShell/`bash`) + `pip install -e ".[dev]"` como el flujo obligatorio, motivado explícitamente por el incidente `starlette`/`sse-starlette` de la Fase 3 (§ 14) — instalar en un Python global puede romper herramientas ajenas sin relación con este proyecto. `.gitignore` ya cubría `.venv/`, `*.egg-info/`, `__pycache__/`, `.pytest_cache/`, `.env` desde fases anteriores; se confirmó, no se modificó.

**PostgreSQL/Alembic — intento real, resultado honesto: NO validado.** Se creó `scripts/check_postgres_migrations.py`: lee `DATABASE_URL` (vía `Settings`), verifica que sea una URL de Postgres, abre una conexión real (`SELECT 1`, con `connect_timeout=5` para fallar rápido en vez de colgarse), ejecuta `alembic upgrade head` + `alembic current`, y por defecto también `alembic downgrade base` + `alembic upgrade head` de nuevo para probar reversibilidad — solo imprime `SUCCESS` si cada paso realmente ocurrió. Se ejecutó en el entorno de esta sesión (`docker: command not found`) y **falló correctamente**, en ~5 segundos, con un mensaje claro (`OperationalError: connection timeout expired`) y código de salida 1 — este es el comportamiento honesto esperado, no un defecto del script. PostgreSQL sigue sin validarse realmente en ningún momento de este proyecto; solo existe la validación offline (`--sql`) de la Fase 2.5, ahora complementada por este script listo para ejecutarse en cuanto haya Docker disponible.

**Logging estructurado.** Nuevo paquete `infrastructure/logging/`: `formatters.py` (`JsonLogFormatter`, `ConsoleLogFormatter`, ambos tolerantes a registros de log de terceros sin los campos estructurados propios — usan `getattr(record, key, None)` en vez de un format string `%()s` que fallaría), `config.py` (`configure_logging(settings)`, fija el handler y nivel del root logger una vez, en `create_app()`), `middleware.py` (`RequestLoggingMiddleware`). Sin `structlog` ni servicio externo — solo `logging` de la librería estándar, tal como pedía la tarea. Cada request obtiene un `request_id` (reutilizando `X-Request-ID` si el cliente lo envía, truncado a 200 caracteres; generando `uuid4().hex` si no) guardado en `request.state.request_id`, y se loguea una línea con `method`, `path`, `status_code`, `duration_ms`.

*Detalle no obvio de Starlette, documentado para no repetir el error:* `RequestLoggingMiddleware` se registra como middleware normal (`app.add_middleware`), lo que lo coloca **dentro** de `ServerErrorMiddleware` pero **fuera** de `ExceptionMiddleware`. Para una excepción de aplicación/dominio conocida (resuelta dentro de `ExceptionMiddleware`), el middleware ve una `Response` normal tras `call_next()`. Para una excepción realmente inesperada (solo capturada por el handler de `Exception`, que vive en `ServerErrorMiddleware`, **fuera** de este middleware), `call_next()` re-lanza la excepción — el middleware no puede escribir el header `X-Request-ID` en una respuesta que no existe todavía en ese punto. La solución: el `request_id` vive en `request.state` (compartido por referencia en todo el `scope` ASGI, visible desde cualquier capa), y es `interfaces/api/error_handlers.py` — no el middleware — quien estampa `X-Request-ID` en la respuesta, para los dos casos (`ApplicationError`/`DomainError` y el fallback de `Exception`) desde el mismo lugar. El logging del traceback también se centralizó ahí (una sola vez por error 5xx, sin duplicar con el middleware).

**Límite de tamaño de subida.** `Settings.max_upload_size_mb` (default `20.0`) + propiedad `max_upload_size_bytes`. La validación vive en `ImageIntakeService.validate_and_store` (capa de aplicación), no en los routers: `get_image_intake_service` (en `dependencies.py`) inyecta `settings.max_upload_size_bytes` al construir el servicio, así que el router nunca lee `Settings` ni compara tamaños directamente — solo delega. Si `len(content)` excede el límite, se lanza `ImageTooLargeError` (nueva, en `application/exceptions.py`, deliberadamente **no** subclase de `InvalidImageError` porque mapea a 413, no a 400) antes de tocar el validador de imagen o el storage. Se comprueba antes que la discrepancia declarado/real de tamaño (Fase 2.5): si un archivo es grande Y además viene con un tamaño declarado incorrecto, el cliente se entera primero de que es demasiado grande, el problema más fundamental.

**Validación estricta de MIME/extensión/formato real.** `PillowImageValidator` ahora, tras decodificar la imagen, compara `image.format` (lo que Pillow detectó de verdad) contra el formato esperado tanto para el MIME declarado como para la extensión del archivo (mapas `MIME_TYPE_TO_PILLOW_FORMAT` / `EXTENSION_TO_PILLOW_FORMAT` en `application/ports/image_validator.py`, junto a `ALLOWED_MIME_TYPES`/`ALLOWED_EXTENSIONS` — una sola fuente de verdad). Un archivo `.png` que en realidad es un JPEG se rechaza aunque la extensión esté permitida, el MIME esté permitido, y Pillow lo decodifique sin error — porque ninguna de esas tres comprobaciones por separado detecta la mentira. `UploadFile.content_type` y el nombre de archivo son datos declarados por el cliente, nunca una prueba.

**Smoke test operativo.** `scripts/api_smoke_test.py` ejercita el camino feliz completo (`/health` → crear muestra → crear versión de modelo `mock` → subir imagen Petri → subir imagen micro → crear `AnalysisRun` → leerlo) contra un servidor **real** (no `TestClient`), usando `httpx` e imágenes JPEG/PNG generadas en memoria con Pillow — sin datasets externos. Se probó de verdad: se levantó `uvicorn` con una base SQLite temporal (ya que no hay Postgres disponible) y un directorio de storage temporal, se ejecutó el script contra `http://127.0.0.1:8123`, y completó los 7 pasos con éxito (código de salida 0) antes de detener el servidor y limpiar los archivos temporales. Sale con código 1 y un mensaje claro ante el primer paso que falle, incluida la falta de conexión al servidor.

**Revisión de `pyproject.toml`.** Se eliminó `pytest-cov` de `dev` (nunca se invocó `--cov` en ningún flujo documentado — mantenerlo declarado habría sido una dependencia no usada). Se añadió `testpaths = ["tests"]` a `[tool.pytest.ini_options]` para que `pytest` a secas (sin especificar `tests`) también funcione. No se agregaron *markers* de pytest para separar tests lentos/de integración: con 102 tests corriendo en ~2.7 s, esa separación no resuelve ningún problema real todavía — agregarla ahora habría sido complejidad sin necesidad concreta.

## 16. Fase 4 — motor de inferencia simulado, Prediction y transición de estado (implementada)

Objetivo: permitir tomar un `AnalysisRun` pendiente, ejecutar un motor de inferencia (hoy exclusivamente simulado), crear una `Prediction` y actualizar el estado del `AnalysisRun`, de forma transaccional. Sin Celery, sin IA real, sin `Prediction` inventada por fuera de este flujo.

**`class_probabilities` y SQLite: `PortableJSON`.** `PredictionModel.class_probabilities` usaba `sqlalchemy.dialects.postgresql.JSONB` directamente, lo que impedía crear la tabla `predictions` bajo SQLite (usada por `tests/integration/db/` y `tests/api/`) — por eso, desde la Fase 2, esa tabla estaba explícitamente excluida de los tests. Se creó `infrastructure/db/models/column_types.py` con `PortableJSON`, un `TypeDecorator` que resuelve a `JSONB` en PostgreSQL (`dialect.name == "postgresql"`) y a `JSON` genérico (soportado por SQLite) en cualquier otro dialecto. **No se tocó la migración `0001`**: el DDL que Alembic genera para PostgreSQL sigue siendo exactamente `class_probabilities JSONB` (verificado de nuevo con `alembic upgrade head --sql`), porque `PortableJSON` solo cambia de comportamiento fuera de PostgreSQL. `predictions` ya no está excluida de ningún conftest de test.

**`InferenceEnginePort` (`application/ports/inference_engine.py`).** Puerto abstracto: `process(*, analysis_run, petri_image, micro_image, model_version) -> InferenceOutput`. `InferenceOutput` es un dataclass con `predicted_label`, `confidence_score`, `class_probabilities`, `technical_observation`, `requires_human_review`. No importa FastAPI ni SQLAlchemy, y su docstring deja explícito que ninguna implementación puede afirmar capacidad diagnóstica o taxonómica real sin haberla validado.

**`MockInferenceEngine` (`ml/inference_engine/mock_inference_engine.py`).** Única implementación existente de `InferenceEnginePort`. Es **determinista** (usa `hashlib.sha256(analysis_run.id.bytes)` para elegir una de las 5 etiquetas preliminares — no hay aleatoriedad, no hay estado global), **no lee ni decodifica bytes de imagen** (no abre el archivo en `petri_image.file_path`/`micro_image.file_path`; no usa Pillow, OpenCV, Cellpose ni PyTorch), y sus confidence scores son deliberadamente moderados (0.55–0.65, nunca por encima de 0.75). `technical_observation` declara explícitamente "SIMULATED RESULT (mock inference engine)" y aclara que no tiene validez diagnóstica. Si la etiqueta es `inconclusive`, `requires_human_review=True` (reforzado además por el propio dominio, `Prediction.__post_init__`, como defensa en profundidad).

**Transiciones de estado en `AnalysisRun` (dominio).** Se añadieron `mark_processing()`, `mark_completed()`, `mark_needs_review()`, `mark_failed(error_message)` directamente en la entidad — no en el caso de uso ni en el repositorio — para que la regla de idempotencia sea imposible de saltarse desde cualquier punto de entrada futuro. `mark_processing()` solo tiene éxito si el estado actual es `pending`; los otros tres solo tienen éxito si el estado actual es `processing`. Cualquier otro intento lanza `InvalidAnalysisRunTransitionError` (nueva excepción de dominio). Esta es, literalmente, la regla de "no reprocesar un `AnalysisRun` ya completado/fallido/en revisión, salvo creando uno nuevo": no existe ningún camino de código que la esquive.

**`PredictionRepositoryPort` + `SqlAlchemyPredictionRepository`.** `add`, `get_by_analysis_run_id`, `get_by_id`. La relación 1:1 con `AnalysisRun` (`UniqueConstraint` en `analysis_run_id`, ya existente desde la Fase 1) se traduce en el repositorio: un `IntegrityError` en el insert se convierte en `DuplicatePredictionError` (409), nunca se propaga una excepción de SQLAlchemy hacia arriba.

**Mecanismo transaccional: `UnitOfWorkPort` extendido, no un flag nuevo.** `UnitOfWorkPort` (Fase 2.5) ganó dos atributos declarados en su contrato abstracto: `analysis_run_repository: AnalysisRunRepositoryPort` y `prediction_repository: PredictionRepositoryPort`, poblados por `SqlAlchemyUnitOfWork.__enter__` con instancias construidas sobre la sesión propia de la transacción y con `auto_commit=False` (parámetro nuevo en `SqlAlchemyAnalysisRunRepository`/`SqlAlchemyPredictionRepository`; con `auto_commit=False` sus escrituras hacen `flush()` en vez de `commit()`, así que los errores de integridad se detectan igual de inmediato, pero nada se hace durable hasta que el `UnitOfWork` llama a `commit()` una sola vez). Esto evita que `application/` tenga que importar SQLAlchemy para construir esos repositorios dentro de la transacción — el patrón es el mismo "UnitOfWork expone repositorios" descrito en la literatura de Clean Architecture/DDD en Python. `ProcessAnalysisRunUseCase` abre tres bloques `with self._unit_of_work as uow:` independientes:

1. Persistir `processing` (una sola escritura, atómica por sí sola).
2. *(si falla la inferencia)* Persistir `failed` + `error_message` (una sola escritura).
3. *(si la inferencia tiene éxito)* Crear la `Prediction` **y** persistir el estado final (`completed`/`needs_review`) **juntos**, en el mismo `commit()` — esta es la parte que la tarea pedía explícitamente que fuera transaccional, y es la única que de verdad necesita atomicidad multi-agregado (las otras dos son una sola fila cada una, atómicas por definición en cualquier base de datos).

Verificado con un test de integración real (`tests/integration/db/test_process_analysis_run_transaction.py`) que fuerza una `DuplicatePredictionError` dentro del bloque 3 y confirma que el cambio de estado que iba junto con ella tampoco se persiste — no es una simulación, es una transacción SQL real sobre SQLite.

**`ProcessAnalysisRunUseCase` (`application/use_cases/inference/process_analysis_run.py`).** Orquesta exactamente el flujo de la tarea: busca `AnalysisRun` (404 si no existe) → busca `PetriImage`/`MicroImage`/`ModelVersion` (404 si falta alguno, extremadamente improbable dado el FK, pero explícito) → reclamo atómico `claim_for_processing()` (409 si no estaba `pending`) → ejecuta `InferenceEnginePort` → si falla el procesamiento, marca el `AnalysisRun` como `failed` con `error_message` controlado y levanta `AnalysisProcessingError` (500 seguro, sin crear `Prediction`) → si tiene éxito, crea `Prediction`, decide `mark_completed()`/`mark_needs_review()` según `requires_human_review`, y persiste ambos atómicamente.

**Decisión corregida en Fase 4.6: un procesamiento fallido no es 200.** Si `MockInferenceEngine.process()` lanzara una excepción (no ocurre en la práctica, al ser puramente determinista y sin I/O, pero el camino existe y está probado con un motor de prueba que sí falla), el `AnalysisRun` queda `failed` con `error_message` seguro y el cliente recibe **500 `analysis_processing_failed`**. El detalle técnico se registra server-side y se conserva como causa de la excepción de aplicación; el cliente no recibe stack trace ni rutas, credenciales u otros detalles internos. Si el cliente necesita el estado operativo persistido, consulta `GET /api/v1/analysis-runs/{id}`.

**Endpoints nuevos** (`interfaces/api/v1/routers/analysis_runs.py`):

| Método | Ruta | Caso de uso | Notas |
|---|---|---|---|
| POST | `/api/v1/analysis-runs/{id}/process` | `ProcessAnalysisRunUseCase` | **200 OK solo si procesa correctamente** (no 201/202 — ver razonamiento abajo). 404 si no existe; 409 si no está `pending`; 409 `duplicate_prediction` si ya existe una predicción anómala; 500 `analysis_processing_failed` si falla el procesamiento tras el reclamo. |
| GET | `/api/v1/analysis-runs/{id}/prediction` | `GetPredictionForAnalysisRunUseCase` | Solo lectura. 404 si no hay `Prediction` todavía. |

**Por qué 200 y no 202 en el camino exitoso.** El procesamiento es síncrono: cuando una respuesta 200 llega, el trabajo ya terminó por completo (no hay Celery, nada queda "aceptado para después"). 202 sería engañoso. Tampoco 201: el sujeto principal del endpoint es la transición del `AnalysisRun` (un recurso que ya existe), no la creación de la `Prediction` — que es un efecto secundario —, de forma análoga a `POST /orders/{id}/cancel`. Los caminos fallidos no devuelven 200: se traducen a 409/500 según corresponda.

**Transparencia del origen simulado en la respuesta.** `AnalysisRunProcessRead` (nuevo schema) incluye un campo `disclaimer` siempre presente, con el texto "This result was produced by a simulated (mock) inference engine...". No es solo una nota en la documentación externa: el propio cuerpo de la respuesta JSON lo deja explícito, verificado por test.

**Mapeo de errores nuevo** (`error_handlers.py`): `InvalidAnalysisRunTransitionError` (dominio) → 409 `analysis_run_not_processable`; `DuplicatePredictionError` → 409 `duplicate_prediction`; `PredictionNotFoundError` → 404 `prediction_not_found`; `AnalysisProcessingError` → 500 `analysis_processing_failed` con mensaje genérico seguro.

**`dependencies.py`: motor de inferencia como una única función reemplazable.** `get_inference_engine() -> InferenceEnginePort` hoy simplemente hace `return MockInferenceEngine()`. Ningún otro punto de `application/` o `interfaces/` menciona `MockInferenceEngine` por nombre — sustituir el motor en el futuro (por uno real basado en PyTorch, o por un servicio externo) significa cambiar esa única función, no tocar el caso de uso, el router ni los tests que usan dobles de prueba.

## 17. Fase 4.5/4.6 — consistencia transaccional, idempotencia, recuperación y semántica HTTP de `/process` (implementada)

Objetivo: la Fase 4 dejó `ProcessAnalysisRunUseCase` con tres bloques `with self._unit_of_work as uow:` independientes (§16). Eso significa tres puntos de confirmación separados sin ninguna red de seguridad que los conecte: si algo fallaba genuinamente entre el bloque 1 (`processing`) y el bloque 3 (estado final + `Prediction`) — y no únicamente por una excepción del motor de inferencia, que era el único caso cubierto por un `try/except` — el `AnalysisRun` quedaba en `processing` para siempre, sin ningún camino de código que lo recuperara. Fase 4.5 cerró ese hueco y Fase 4.6 corrigió dos semánticas finales del endpoint: un procesamiento fallido no se reporta como `200 OK`, y una `DuplicatePredictionError` posterior al reclamo tampoco puede dejar el análisis en `processing`. Sigue sin existir Celery, IA real, PyTorch, dataset, frontend, autenticación ni taxonomía.

**Diagnóstico exacto del diseño de la Fase 4 (Tarea 1).** El flujo antiguo era: `analysis_run.mark_processing()` (en Python) → bloque uow #1 (`update()`, persiste `processing`) → `try: motor.process()` → si falla, bloque uow #2 (`mark_failed` + `update()`) y `return` → si tiene éxito, construir `Prediction`, `mark_completed()`/`mark_needs_review()` (en Python) → bloque uow #3 (`prediction_repository.add()` + `analysis_run_repository.update()` + `commit()`). Puntos de fallo específicos pedidos por la tarea:

1. **Antes de marcar `processing`** (durante las búsquedas de `AnalysisRun`/`PetriImage`/`MicroImage`/`ModelVersion`): sin efecto — nada se ha escrito todavía, la excepción (404) se propaga limpia.
2. **Después de marcar `processing`, durante la inferencia**: cubierto por el `try/except` original — pasaba a `failed` correctamente.
3. **Durante la creación de `Prediction`** (construcción del objeto en Python, p. ej. un `confidence_score` fuera de rango de un motor mal implementado): **NO estaba cubierto** — ocurre fuera del `try/except` original (que solo envolvía la llamada al motor), así que la excepción se propagaba sin marcar nada como `failed`: `AnalysisRun` quedaba en `processing` para siempre.
4. **Durante el cambio de estado final** (`uow.analysis_run_repository.update()` dentro del bloque 3, p. ej. un error de base de datos): **NO estaba cubierto** — el bloque 3 no tenía ningún `try/except` alrededor; la excepción se propagaba tal cual (un 500 genérico), y como el bloque 1 ya había hecho `commit()` de `processing` por separado, el `AnalysisRun` quedaba en `processing` para siempre.
5. **Por unicidad de `Prediction` duplicada** (`DuplicatePredictionError` dentro del bloque 3): mismo problema que el punto anterior — sin cobertura, `AnalysisRun` quedaba en `processing`.
6. **Carrera de doble procesamiento**: dos llamadas concurrentes a `/process` para el mismo `AnalysisRun` podían ambas leer el mismo `AnalysisRun` `pending` (cada una con su propia copia en memoria, cada una vía su propia sesión), ambas pasar la validación `mark_processing()` en su copia local, y ambas terminar compitiendo por crear una `Prediction` — la segunda fallaría con `DuplicatePredictionError`, pero sin ninguna garantía de *qué* orden ganaba ni de que la primera hubiera dejado el `AnalysisRun` en un estado consistente al momento de la carrera.

**Solución (Tareas 2 y 4): reclamo atómico + único bloque de recuperación.** Dos cambios, complementarios:

- **`AnalysisRunRepositoryPort.claim_for_processing(analysis_run_id) -> Optional[AnalysisRun]`** (nuevo método de puerto), implementado en `SqlAlchemyAnalysisRunRepository` como una única sentencia `UPDATE analysis_runs SET status='processing', started_at=NOW() WHERE id=:id AND status='pending'`, verificando `result.rowcount`. Si `rowcount == 0`, devuelve `None` (la fila no estaba `pending` — otra llamada ya la reclamó, o ya estaba en un estado final); si `rowcount == 1`, devuelve la entidad ya actualizada. **Esta es la Opción B pedida explícitamente por la tarea** (actualización condicional atómica) en vez de la Opción A (bloqueo pesimista `SELECT ... FOR UPDATE`): se eligió por ser portable entre SQLite (usado en todos los tests de este repo) y PostgreSQL sin ninguna rama de código específica por dialecto, mientras que `SELECT ... FOR UPDATE` no tiene el mismo comportamiento de bloqueo bajo SQLite. La garantía resultante: **como máximo una llamada puede transicionar un `AnalysisRun` dado de `pending` a `processing`** — cualquier otra, sea concurrente o posterior, obtiene `None` y el caso de uso responde 409, sin haber tocado el motor de inferencia ni el repositorio de `Prediction`. Detalle de implementación no trivial: un `UPDATE` a nivel de Core de SQLAlchemy no sincroniza el identity map del ORM, así que si el `AnalysisRun` ya había sido cargado en la misma sesión (p. ej. por el `get_by_id()` de existencia previo), hace falta `session.expire_all()` antes de releer la fila reclamada — de lo contrario se devolvería el objeto cacheado con el estado anterior a la reclamación. Verificado con un test de integración real (`tests/integration/db/test_sqlalchemy_analysis_run_repository.py::test_claim_for_processing_only_succeeds_once`).

- **`ProcessAnalysisRunUseCase.execute()` ya no abre tres bloques `uow` independientes para el camino post-reclamo.** El nuevo flujo: búsquedas de referencias (404) → `claim_for_processing()` (409 con mensaje adaptado al estado observado si falla) → **un único `try/except Exception` que envuelve todo lo que ocurre después del reclamo**: la llamada al motor, la construcción de `Prediction`, las transiciones `mark_completed()`/`mark_needs_review()`, y el bloque `uow` de `Prediction` + estado final. Cualquier excepción que escape de ese `try` — sin importar en qué línea ocurra — cae en `_handle_processing_failure()`, que fuerza el `AnalysisRun` a `failed` con `error_message` controlado y lo persiste en su **propia** transacción `uow`, separada de la que acaba de fallar. Un detalle real descubierto al escribir los tests: si `mark_completed()`/`mark_needs_review()` ya había mutado `analysis_run.status` en memoria antes de que fallara la escritura final, `mark_failed()` lo rechazaría (exige `processing`) — por eso `_handle_processing_failure()` primero repone `analysis_run.status = AnalysisStatus.PROCESSING` (el último estado realmente persistido, ya que la mutación en memoria y la escritura fallida pertenecían a la misma transacción abortada) antes de llamar a `mark_failed()`. Si la recuperación tiene éxito, el error original queda registrado y preservado como `__cause__` de `AnalysisProcessingError`, que la API traduce a 500 `analysis_processing_failed` con mensaje seguro. Si **incluso esa** escritura de recuperación falla (el escenario límite explícito), se registra un `logger.critical(...)` con el error original y el de la escritura de recuperación (nunca se descarta ninguno de los dos) y se lanza `AnalysisRunFinalizationError` encadenada (`raise ... from persist_error`) — el cliente recibe un 500 controlado, nunca una traza cruda ni una respuesta 200 fingiendo éxito.

- **Caso especial: `DuplicatePredictionError` durante la finalización.** Con el reclamo atómico en vigor, esta excepción debería ser estructuralmente imposible (nadie más puede estar "procesando" el mismo `AnalysisRun` a la vez). Si ocurriera de todos modos (p. ej. manipulación manual de la base de datos dejando una `Prediction` huérfana para un `AnalysisRun` que sigue `pending`), el caso de uso primero marca el `AnalysisRun` como `failed` con `error_message` controlado (`Prediction already exists for this analysis run`) y luego relanza un `DuplicatePredictionError` saneado, mapeado a 409 `duplicate_prediction`. Verificado con un test de integración real que inserta una `Prediction` huérfana antes de reclamar y confirma que la transacción de finalización completa (inserción de `Prediction` + cambio de estado) se revierte como un todo, que no se crea una segunda `Prediction`, y que la recuperación deja el `AnalysisRun` en `failed`, no en `processing` (`test_process_analysis_run_transaction.py::test_duplicate_prediction_during_finalization_marks_analysis_run_failed`).

**Idempotencia de `/process` (Tarea 3).** Los cuatro estados no-`pending` devuelven 409 `analysis_run_not_processable`, con un mensaje adaptado al estado observado en el momento del intento de reclamo (no al estado exacto en el instante de la respuesta, que podría haber cambiado por otra llamada concurrente — es solo un mensaje orientativo, la decisión 409/200 la toma únicamente el resultado atómico del `UPDATE`):

| Estado observado | Mensaje | Recomendación implícita |
|---|---|---|
| `processing` | "it is already being processed" | Esperar a que termine, no reintentar de inmediato. |
| `completed` / `needs_review` | "it has already been processed" | El resultado ya existe; usar `GET /prediction`. |
| `failed` | "it already failed previously; create a new AnalysisRun to retry" | Reintentar significa un `AnalysisRun` nuevo, nunca reabrir el fallido. |

Nunca se crea una segunda `Prediction` para el mismo `AnalysisRun` (garantizado en dos niveles: el `UniqueConstraint` de base de datos ya existente desde la Fase 1, y ahora también el reclamo atómico, que impide siquiera intentar una segunda ejecución del motor).

**`AnalysisRun.mark_processing()` (dominio) ya no es el mecanismo de concurrencia real, pero se conserva.** Sigue existiendo y sigue probado (`tests/unit/domain/test_analysis_run.py`) porque documenta la regla de negocio "`pending → processing` es la única transición de arranque válida" de forma independiente de cualquier base de datos — pero un chequeo en memoria no puede impedir que dos llamadas concurrentes, cada una con su propia copia del `AnalysisRun`, pasen esa validación al mismo tiempo. Por eso `ProcessAnalysisRunUseCase` ya no lo invoca directamente: usa `claim_for_processing()`, que aplica exactamente la misma regla como una única operación SQL condicional. La duplicación de la regla (una vez en la entidad, una vez en el `WHERE` del `UPDATE`) es intencional y prácticamente inevitable — la atomicidad solo puede garantizarla la base de datos, no un objeto en memoria.

**Logging de negocio (Tarea 6).** `ProcessAnalysisRunUseCase` usa un logger dedicado (`blueberry_microid.business.process_analysis_run`, stdlib `logging` — no una dependencia nueva, no acopla `application/` a ningún framework) con dos líneas de log por ejecución: una al reclamar exitosamente (`analysis_run_id`, `sample_id`, `model_version_id`, `initial_status="pending"`), y una al terminar (los mismos tres identificadores más `final_status`, `prediction_created`, `requires_human_review`, `error`). Los fallos intermedios se registran aparte, a nivel `ERROR` (con `exc_info` del error original) y, en el escenario límite, a nivel `CRITICAL`. **Nunca se registra contenido de imágenes** (ni siquiera las rutas de archivo se incluyen en estos logs de negocio). **`request_id` deliberadamente no se incluye en esta fase**: pasarlo limpiamente requeriría que `application/` conociera el contexto HTTP de `interfaces/`, lo cual violaría la regla de capas (§2 de CLAUDE.md); la correlación por `request_id` para estos logs de negocio queda pendiente de una fase futura que decida cómo transportarlo sin ese acoplamiento (p. ej. un parámetro explícito opcional en `execute()`, a evaluar más adelante).

**Mapeo de errores nuevo** (`error_handlers.py`): `AnalysisProcessingError` → 500 `analysis_processing_failed`; `AnalysisRunFinalizationError` → 500 `analysis_run_finalization_failed`; `DuplicatePredictionError` → 409 `duplicate_prediction`; `InvalidAnalysisRunTransitionError` → 409 `analysis_run_not_processable`; `AnalysisRunNotFoundError` → 404. Todo 5xx se registra con traza completa server-side y devuelve un mensaje seguro; `X-Request-ID` se conserva.

**Tests nuevos/actualizados (total 160).** Unitarios (`tests/unit/application/test_process_analysis_run_use_case.py`, con dobles de prueba en `fakes.py`: `FailingInferenceEngine`, `FailingAddPredictionRepository`, `UpdateFailingNTimesAnalysisRunRepository`): rechazo en cada uno de los cuatro estados no-`pending`; el reclamo solo tiene éxito una vez; un fallo del motor marca `failed`, no crea `Prediction`, levanta `AnalysisProcessingError` y registra el error original; un fallo en la creación de `Prediction` no deja el run en `processing`; un fallo en la escritura final intenta marcar `failed` y lo consigue; si **también** falla esa escritura de recuperación, se lanza `AnalysisRunFinalizationError`; no se crea una segunda `Prediction` tras un intento de reproceso; una `DuplicatePredictionError` marca `failed` y se relanza como conflicto controlado. Integración (`tests/integration/db/`, contra SQLite real): el reclamo atómico solo tiene éxito una vez a nivel de fila real; el flujo completo con un motor que falla deja el `AnalysisRun` realmente persistido como `failed`, nunca `processing`; una `Prediction` duplicada durante la finalización no crea una segunda `Prediction` y deja el estado persistido como `failed`, probado con rollback real, no simulado. API (`tests/api/test_process_analysis_run.py`, con helpers que reescriben estado o crean una predicción anómala directamente en la base de datos de prueba): `/process` sobre `processing` y sobre `failed` devuelven 409; `GET /prediction` repetido nunca crea una `Prediction`; un fallo del motor devuelve 500 `analysis_processing_failed`, no filtra detalles, conserva `X-Request-ID` y deja el `AnalysisRun` consultable como `failed`; un `DuplicatePredictionError` devuelve 409 `duplicate_prediction`, conserva `X-Request-ID`, no crea segunda `Prediction` y tampoco deja `processing`.

**Riesgos pendientes tras Fase 4.6.** (a) El `request_id` no viaja hasta el logging de negocio, como se explica arriba — aceptable por ahora, pero limita la correlación de logs en producción. (b) No se ha probado concurrencia real con hilos/procesos simultáneos contra SQLite o PostgreSQL (solo la garantía atómica a nivel de una sola fila, verificada secuencialmente) — la tarea explícitamente permite esta simplificación cuando no es viable montar un test de concurrencia real, pero sigue siendo una validación pendiente antes de un entorno productivo con tráfico concurrente genuino. (c) La migración de Alembic no cambia en esta fase (no se tocó ninguna columna ni tabla), así que su estado de validación contra PostgreSQL real sigue siendo el mismo ya documentado en `docs/development.md` §5 — sin novedad, pero sin resolver tampoco.

## 18. Fase 5 — revisión humana, auditoría y resultado final (implementada)

Objetivo: habilitar una revisión humana auditable sobre una `Prediction` existente, con historial y una única revisión final vigente por `AnalysisRun`, sin sobrescribir el resultado del motor simulado y sin ampliar el alcance del producto.

**Casos de uso (`application/use_cases/review/`).** `SubmitHumanReviewUseCase` valida que el `AnalysisRun` exista, que no esté `pending` ni `processing`, y que ya tenga una `Prediction`; luego crea un `HumanReview`. `GetFinalHumanReviewUseCase` devuelve la revisión final vigente o 404 si todavía no existe. `ListHumanReviewsUseCase` devuelve el historial cronológico del análisis.

**DTOs y puertos.** Se añadieron `SubmitHumanReviewRequest` y `HumanReviewDTO`, más `HumanReviewRepositoryPort` con `add`, `get_by_id`, `list_by_analysis_run_id`, `get_final_by_analysis_run_id` y `unset_final_reviews_for_analysis_run`.

**Repositorio SQLAlchemy.** `SqlAlchemyHumanReviewRepository` traduce `HumanReviewModel` a entidad de dominio y respeta el patrón `auto_commit`: fuera de UoW hace `commit()` por llamada; dentro de UoW hace `flush()` para que la transacción completa se confirme o revierta junta. El índice único parcial `uq_human_reviews_one_final_per_run` sigue siendo la última línea de defensa contra dos revisiones finales para el mismo análisis.

**Transacción de revisión final.** Si la revisión entrante tiene `is_final=True`, `SubmitHumanReviewUseCase` abre un único `UnitOfWork`, despromueve las revisiones finales anteriores (`is_final=False`), inserta la nueva revisión y llama a `commit()`. Si la inserción falla, el rollback revierte también la despromoción, por lo que la revisión final previa queda intacta. Este comportamiento está cubierto tanto con dobles en memoria como con una transacción SQL real sobre SQLite.

**Endpoints nuevos (`interfaces/api/v1/routers/human_reviews.py`).**

| Método | Ruta | Caso de uso | Notas |
|---|---|---|---|
| POST | `/api/v1/analysis-runs/{analysis_run_id}/reviews` | `SubmitHumanReviewUseCase` | 201 si crea la revisión; 404 si falta `AnalysisRun` o `Prediction`; 409 si el run todavía no es revisable; 422 si una revisión `corrected` no trae `corrected_label`. |
| GET | `/api/v1/analysis-runs/{analysis_run_id}/reviews` | `ListHumanReviewsUseCase` | Historial cronológico; lista vacía si el run existe pero aún no tiene revisiones. |
| GET | `/api/v1/analysis-runs/{analysis_run_id}/reviews/final` | `GetFinalHumanReviewUseCase` | 404 `human_review_not_found` si todavía no hay revisión final. |

**Alcance deliberadamente no ampliado.** La revisión humana no agrega frontend, autenticación, Celery, inferencia real, PyTorch, datasets, entrenamiento, métricas, taxonomía especie/género ni soporte para productos distintos de arándano. Las etiquetas corregidas siguen siendo las cinco categorías visuales preliminares del MVP.

**Tests nuevos (28).** Unitarios: validan decisiones `confirmed`/`corrected`/`marked_inconclusive`/`rejected_invalid_sample`, errores por run inexistente, prediction inexistente y run no revisable, despromoción de final anterior y rollback. Integración DB: cubre `add`/`get`/`list`/`final`, `unset_final_reviews_for_analysis_run`, duplicado final controlado y rollback real. API: cubre creación, final, historial, lista vacía, reemplazo de final, validación 422, 404/409 esperados, preservación de `Prediction`, ausencia de especie/género y conservación de `X-Request-ID`.

## 19. Fase 5.5 — saneamiento de proyecto, Git, reproducibilidad y validación final del MVP técnico (implementada)

Objetivo: esta fase no añade funcionalidad de negocio. Cierra deuda operativa acumulada durante las Fases 0–5 antes de abrir Celery, IA real o frontend: el repositorio no tenía control de versiones real, la carpeta raíz tiene un nombre mal escrito, PostgreSQL real seguía sin validarse, y no existía integración continua.

**Nombre de la carpeta raíz: documentado, no renombrado.** `D:\IndetificadorMicro` es el directorio de trabajo al que el entorno de esta sesión (Claude Code) está vinculado. Renombrarlo en caliente desde dentro de la propia sesión que lo tiene como `cwd` es una operación insegura: rompería la resolución de rutas relativas del harness a mitad de ejecución, con riesgo real de dejar la sesión en un estado inconsistente sin ningún beneficio funcional (el nombre de una carpeta en disco no afecta en absoluto al comportamiento del sistema). Por eso **no se ejecutó** el renombrado. Queda documentado como paso manual pendiente en `docs/development.md` § 14: renombrar la carpeta a `D:\BlueberryMicroID` fuera de cualquier sesión de Claude Code activa sobre ella (con el editor/terminal cerrados), y volver a abrir una sesión nueva apuntando a la ruta corregida. **Esto no afecta a ningún import ni ruta interna**: el paquete Python instalado en modo editable (`pip install -e .`) ya se llama correctamente `blueberry_microid` (`src/blueberry_microid/`), y ninguna ruta de importación, módulo o test depende del nombre de la carpeta raíz del repositorio — solo del `site-packages`/`.pth` que `pip install -e .` genera, que sigue siendo válido tras un `mv`/rename de carpeta seguido de una reinstalación (`pip install -e ".[dev]"` de nuevo, por seguridad, ya que la ruta absoluta cambia).

**Git: repositorio inexistente, ahora inicializado.** El directorio `.git/` presente antes de esta fase estaba vacío (sin `HEAD`, sin objetos, sin refs) — `git status`/`git rev-parse --is-inside-work-tree` confirmaban `fatal: not a git repository`, coincidiendo con el diagnóstico del usuario, no con un resumen previo de una sesión distinta que había asumido lo contrario. Se ejecutó `git init` (que reutiliza y completa el `.git/` ya presente sin destruir nada, ya que estaba vacío) y se fijó la rama por defecto a `main` (`git branch -m main`) para seguir la convención esperada por el harness y por el workflow de CI nuevo. La identidad de commit (`user.name`/`user.email`) ya estaba configurada globalmente en la máquina.

**`.gitignore` ampliado.** Además de las entradas ya existentes (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `*.egg-info/`, `.venv/`, `venv/`, `.env`, contenido de `storage/*_images/` salvo `.gitkeep`), se añadieron: `.coverage`/`.coverage.*`/`htmlcov/` (cobertura), `build/`/`dist/` (artefactos de empaquetado — se encontró y eliminó un `build/` real de 364 KB / 114 archivos generado en una fase anterior por una instalación/build previa), `*.db`/`*.sqlite`/`*.sqlite3` (bases SQLite temporales, por si algún flujo futuro las crea fuera de `tmp_path` de pytest), `*.log`/`logs/` (logs, aunque el logging estructurado actual solo escribe a stdout, no a archivo) y `.claude/settings.local.json` (configuración local de la herramienta, específica de esta máquina, análoga a `.vscode/settings.json` — no debe compartirse vía control de versiones).

**Limpieza de artefactos.** Se eliminaron todos los `__pycache__/` (decenas, uno por paquete), el `build/` huérfano mencionado arriba, y se verificó la ausencia de `.pytest_cache/`, `.coverage`, bases `*.sqlite*`/`*.db`, `*.log` y archivos sueltos en `storage/petri_images/`/`storage/micro_images/` (solo quedan los `.gitkeep` intencionales). No se tocó código fuente, documentación, ni los `.gitkeep` de las carpetas placeholder de `ml/` (`fusion/`, `micro_branch/`, `petri_branch/`, `model_registry/`, `preprocessing/`) ni `domain/repositories/`, que siguen vacías a propósito.

**Reproducibilidad verificada (sin recrear el entorno).** No se recreó `.venv` en esta fase para no arriesgar el entorno de la sesión activa, pero se verificó con `pip show` que las 11 dependencias pedidas explícitamente (FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic, Pydantic Settings, Pillow, python-multipart, psycopg, pytest, httpx) están declaradas en `pyproject.toml` **y** instaladas en el entorno actual con versiones dentro de los rangos declarados — no hay divergencia entre lo declarado y lo instalado.

**PostgreSQL real: seguimos sin validación positiva, confirmado de nuevo honestamente.** Se intentó `docker --version`/`docker compose version` (vía Bash y PowerShell): el comando `docker` no existe en este entorno (`command not found` / `CommandNotFoundException`), no solo "el daemon no responde" — Docker no está instalado o no está en el `PATH` de esta máquina/sesión. En consecuencia no se pudo ejecutar `docker compose up -d`. Se ejecutó igualmente `python scripts/check_postgres_migrations.py` contra el `DATABASE_URL` por defecto: falla exactamente como se esperaba, con `psycopg.errors.ConnectionTimeout` contra `localhost:5432` (IPv6 `::1` e IPv4 `127.0.0.1`, ambos con timeout). **No se sustituyó esta validación por SQLite** — SQLite sigue siendo, como en todas las fases anteriores, solo el sustituto de `tests/`, nunca una prueba de que las migraciones funcionan contra el dialecto PostgreSQL real. Este es un bloqueante real y explícito para cualquier despliegue, no una formalidad.

**CI básico (`.github/workflows/tests.yml`), nuevo.** Workflow mínimo con tres pasos: `actions/checkout@v4`, `actions/setup-python@v5` (Python 3.10), `pip install -e ".[dev]"` y `pytest -v`, disparado en `push`/`pull_request` sobre `main`. Deliberadamente **no** incluye: despliegue, un servicio Postgres en GitHub Actions, ni secrets — exactamente el alcance mínimo pedido. La validación contra PostgreSQL real queda fuera de este CI y documentada como mejora futura pendiente (añadir un `services: postgres:` en el job cuando se decida abordarla, no antes).

**Commit inicial: ver `docs/development.md` § 14 para el estado final exacto** (hash si se creó, o la razón explícita si no, según el resultado de `git status --short` en el momento de cerrar esta fase).

## 20. Fase 6 — validación real de PostgreSQL, Alembic y CI con base de datos real (implementada)

Objetivo: cerrar la brecha arrastrada desde la Fase 1 — el esquema solo se ejercitaba contra SQLite. Ahora existen tests que corren contra un PostgreSQL real y un job de CI dedicado configurado para ejecutarlos contra un contenedor de servicio PostgreSQL. No se añade funcionalidad de negocio: es puramente infraestructura de validación. Sin Celery, sin IA real, sin PyTorch, sin dataset, sin taxonomía, sin frontend.

**Diagnóstico del CI anterior (Tarea 1).** El workflow de la Fase 5.5 tenía un único job (`test`) que instalaba el proyecto y corría `pytest -v` contra SQLite. Validaba: comportamiento de dominio/aplicación/API y las tablas que SQLite sí puede representar. **No** validaba: que las migraciones Alembic apliquen contra PostgreSQL, ni los tipos/constraints exclusivos de PostgreSQL (`JSONB`, `ENUM` nativos, índice único parcial, `CHECK`, `UUID`). Faltaba: un servicio PostgreSQL en CI, un `DATABASE_URL` apuntándolo, y tests que se ejecuten contra él.

**CI con dos jobs (`.github/workflows/tests.yml`).** (1) `unit-and-api-tests`: instala y corre `pytest -v` sin `DATABASE_URL`, por lo que los tests exclusivos de PostgreSQL se saltan automáticamente. (2) `postgres-migrations`: levanta un `services: postgres:16` (`blueberry`/`blueberry`, base `blueberry_microid_test`, puerto 5432 con healthcheck `pg_isready`), define `DATABASE_URL=postgresql+psycopg://...`, ejecuta `python scripts/check_postgres_migrations.py` (aplica las migraciones y verifica reversibilidad), y luego `pytest -v -m postgres tests/integration/postgres`. Sin deploy, sin build de imagen Docker, sin secrets — las credenciales del workflow son valores desechables de una base efímera de CI, no secretos reales.

**Marcador `postgres` y gating por entorno.** Se registró el marcador `postgres` en `pyproject.toml`. Los tests bajo `tests/integration/postgres/` llevan `pytestmark = pytest.mark.postgres` y dependen de fixtures que hacen `pytest.skip` salvo que la **variable de entorno** `DATABASE_URL` esté puesta y empiece por `postgresql`. El gate lee `os.environ` directamente, **no** `Settings` (cuyo default ya es una URL PostgreSQL aunque no haya nada configurado) — así la condición es "¿alguien proporcionó explícitamente una base PostgreSQL?", no "¿el default parece PostgreSQL?". Consecuencia: en local sin PostgreSQL, los PostgreSQL-only tests se saltan (en Fase 7, `pytest -v` reporta 196 passed, 12 skipped); cuando el job de CI se ejecute en GitHub Actions, corren de verdad. En ningún caso se usa SQLite como sustituto de estos tests.

**Fixtures (`tests/integration/postgres/conftest.py`).** `migrated_engine` (scope de sesión) fija `os.environ["DATABASE_URL"]` y aplica las **migraciones Alembic reales** vía la API de Alembic (`command.downgrade(base)` → `command.upgrade(head)`) — es decir, un run verde prueba que las migraciones son válidas en PostgreSQL, no solo que `create_all` funcionaría. `pg_session` (scope de función) entrega una sesión y hace `TRUNCATE ... RESTART IDENTITY CASCADE` de las siete tablas tras cada test (con `rollback()` previo, para que un test que disparó un error de constraint —dejando su transacción abortada— no rompa el truncado).

**Tests PostgreSQL (12, `tests/integration/postgres/`).** `test_schema.py`: las siete tablas existen tras migrar; `class_probabilities` es `JSONB` real (round-trip de dict, operador `->>`, y `information_schema` reporta `jsonb`); los `ENUM` guardan el **valor** (`mock`, `pending`) y no el nombre del miembro Python; las columnas `UUID` devuelven `uuid.UUID` reales. `test_constraints.py`: el índice único parcial permite una sola review `is_final = true` por run pero múltiples históricas; el `CHECK` de `confidence_score` rechaza fuera de `[0,1]` y acepta `NULL`/en rango; el `CHECK` de `corrected_label` obliga a que exista cuando la decisión es `corrected`. Estos tests construyen filas vía los **modelos ORM** (no las entidades de dominio) a propósito, para probar que es la **base de datos** —y no la validación de la entidad— la que rechaza. `test_api_postgres_smoke.py`: flujo API completo con `TestClient` apuntando al PostgreSQL migrado y storage temporal — muestra → imágenes (generadas con Pillow) → AnalysisRun → procesamiento mock → Prediction → revisión humana final → consulta de la final. Solo motor mock, sin IA ni datasets.

**`scripts/check_postgres_migrations.py` reforzado (Tarea 3).** Ahora prefiere `DATABASE_URL` de entorno e imprime explícitamente qué fuente usa (`[0/4]`); si no está seteada, cae al default de `Settings` pero lo avisa de forma prominente (en CI debe estar seteada). Tras resolver la URL, la re-exporta a `os.environ["DATABASE_URL"]` antes de invocar `alembic`, garantizando que el subproceso de Alembic apunte exactamente a la misma base cuya conexión se acaba de verificar (evita el desajuste con el placeholder de `alembic.ini` en la ruta de fallback). Mantiene: rechazo si la URL no es PostgreSQL, `SELECT 1` con `connect_timeout` corto, `upgrade head`, `current`, y roundtrip `downgrade base`/`upgrade head` (salvo `--skip-roundtrip`); nunca imprime "SUCCESS" si algún paso falló.

**`alembic/env.py` revisado (Tarea 7), sin cambios.** Ya lee `DATABASE_URL` de entorno y sobrescribe `sqlalchemy.url`; no tiene default a SQLite; usa una ruta relativa calculada (`parents[1]/src`), no absoluta; no requiere un `.env` real; no imprime secretos. Correcto tal cual para CI y local.

**Estado real de PostgreSQL en este entorno.** Igual que en la Fase 5.5: esta máquina/sesión no tiene Docker (`docker: command not found`), así que los 12 tests PostgreSQL **no** se ejecutaron localmente — se reportan como `skipped` en local. Su validación real debe ocurrir en GitHub Actions, pero en Fase 6.5 todavía no se observó ningún run desde esta máquina: `main` sí fue subido a GitHub, pero no hay `gh` instalado y el API público de Actions respondió `404 Not Found`. No se finge que pasaron localmente ni en CI.

**Riesgos pendientes antes de Fase 7.** (a) La validación PostgreSQL depende de que el job de CI corra en GitHub Actions; en este entorno local sigue sin Docker y en Fase 6.5 el workflow fue subido, pero no se pudo observar el resultado desde esta máquina, así que no hay confirmación local ni de CI. (b) El job de CI usa `postgres:16` con credenciales de prueba; una futura fase que despliegue necesitará validar también contra la versión/configuración exacta de PostgreSQL de producción. (c) Sigue sin haber Celery, IA real ni frontend — fuera de alcance por diseño hasta que se aprueben.

## 21. Fase 6.5 — verificación real del workflow CI PostgreSQL (Estado B)

Objetivo: confirmar si el workflow de GitHub Actions realmente se ejecuta y pasa. No se implementó funcionalidad nueva: sin Celery, sin IA real, sin PyTorch, sin entrenamiento, sin datasets, sin frontend, sin autenticación y sin taxonomía microbiológica.

**Estado Git observado el 2026-07-02.** Rama actual: `main`. Último commit antes de documentar esta fase: `7535d6a Add PostgreSQL validation workflow`. `git status --short` no mostró archivos modificados al inicio de la verificación (solo warnings del sandbox por `safe.directory`/ignore global inaccesible). `git log --oneline -5` mostró `7535d6a` seguido de `b098eb6 Initial BlueberryMicroID MVP backend`.

**Remoto GitHub y push.** Al inicio `git remote -v` no devolvió ningún remoto configurado. Tras autorización explícita del usuario, se agregó `origin` con `https://github.com/JaimePergueza/BlueberryIdentifyID.git` y `git push origin main` terminó correctamente: `main -> main`.

**Estado del workflow.** Estado B: `.github/workflows/tests.yml` existe y define los jobs `unit-and-api-tests` y `postgres-migrations`, y la rama `main` fue subida al remoto. Aun así no se observó ningún run real de GitHub Actions desde este entorno: `gh --version` falla porque GitHub CLI no está instalado, y una consulta no autenticada a `https://api.github.com/repos/JaimePergueza/BlueberryIdentifyID/actions/runs?per_page=5` devolvió `404 Not Found`. PostgreSQL **no** queda validado en CI hasta que un run real termine exitosamente.

**Pasos manuales para completar la verificación.** Abrir el repositorio en GitHub, entrar a **Actions**, seleccionar `.github/workflows/tests.yml`, y confirmar que pasen ambos jobs: `unit-and-api-tests` y `postgres-migrations`. Si falla alguno, registrar aquí el run id o URL y el resumen del error antes de avanzar a Fase 7. Si pasan ambos, actualizar esta sección a Estado A con fecha, hash y run id/URL.

## 22. Fase 7 — procesamiento asíncrono con Celery + Redis usando el motor mock

Objetivo: ejecutar el análisis mock fuera del request HTTP sin cambiar las reglas de negocio ni introducir IA real. Esta fase agrega Celery como transporte de ejecución asíncrona, no un segundo motor de procesamiento. Sin IA real, sin PyTorch, sin entrenamiento, sin datasets, sin métricas inventadas, sin frontend, sin autenticación y sin taxonomía microbiológica.

**Diagnóstico del flujo síncrono reutilizado.** `ProcessAnalysisRunUseCase` ya concentra las reglas importantes: valida referencias, reclama `pending -> processing` con `AnalysisRunRepositoryPort.claim_for_processing()`, llama al `InferenceEnginePort`, crea `Prediction`, finaliza el `AnalysisRun`, y recupera fallos dejando el run en `failed`. Celery no duplica nada de eso: `process_analysis_run_task()` construye la infraestructura real y llama al mismo caso de uso.

**Configuración Celery/Redis.** `Settings` ahora incluye `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER`, `CELERY_TASK_EAGER_PROPAGATES`, `CELERY_TASK_TIME_LIMIT` y `CELERY_TASK_SOFT_TIME_LIMIT`. Los defaults locales son Redis en `localhost:6379` DB 0/1; no hay credenciales reales ni secretos. `pyproject.toml` declara solo `celery` y `redis` como dependencias nuevas.

**Celery app.** `infrastructure/tasks/celery_app.py` expone `celery_app`, lee `Settings`, usa cola `analysis`, serializa tareas/resultados como JSON, acepta solo JSON (no pickle), usa UTC y activa `task_track_started`. Los imports de tasks son explícitos.

**Task de procesamiento.** `infrastructure/tasks/analysis_tasks.py::process_analysis_run_task(analysis_run_id: str)` convierte el id a `UUID`, construye engine/session/repositories/`SqlAlchemyUnitOfWork` sin FastAPI, usa `MockInferenceEngine`, llama `ProcessAnalysisRunUseCase`, loguea inicio/éxito/fallo con `analysis_run_id`, y devuelve una estructura con `analysis_run_id`, `status`, `prediction_id` y `mock=true`. Si el caso de uso falla de forma controlada tras marcar el run como `failed`, la task refleja ese estado. Si ocurre un error inesperado, se relanza para que Celery marque la task como failed.

**Endpoint async.** `POST /api/v1/analysis-runs/{analysis_run_id}/process-async` valida que el `AnalysisRun` exista y esté `pending`, encola la task y responde `202 Accepted` con `task_id`, `"status": "queued"` y un mensaje. No ejecuta inferencia, no crea `Prediction`, no llama directamente a `MockInferenceEngine` y conserva `X-Request-ID`.

**Sin estado persistido `queued`.** No se agregó migración ni nuevo estado. `"queued"` es el estado operativo de la task en la respuesta HTTP; el `AnalysisRun` permanece `pending` hasta que el worker gana el claim y lo mueve a `processing`. Esto evita una migración prematura. Riesgo aceptado: dos requests pueden encolar dos tasks antes del claim; no crean doble `Prediction` porque `claim_for_processing()` sigue siendo la protección real.

**Consulta de task.** `GET /api/v1/tasks/{task_id}` devuelve `task_id`, `state` y un `result` seguro. En `FAILURE` no expone traceback. Este endpoint es auxiliar: Celery puede olvidar resultados según backend/configuración; la fuente durable es `GET /analysis-runs/{id}` y `GET /analysis-runs/{id}/prediction`.

**Endpoint síncrono preservado.** `POST /api/v1/analysis-runs/{id}/process` sigue existiendo para desarrollo y pruebas. El flujo recomendado para operación es `/process-async`; una fase futura podrá deprecarlo, protegerlo o reservarlo a tooling interno.

**Pruebas.** Se agregan tests unitarios para settings Celery, configuración JSON/no-pickle y task; tests API con task fake para demostrar que `/process-async` solo encola; y tests eager con SQLite de archivo para ejecutar la task real sin Redis, verificar `202`, estado final, `Prediction`, revisión humana posterior y duplicados sin segunda `Prediction`.

**Riesgos pendientes antes de Fase 7.5.** (a) Falta smoke real con un worker Celery separado y Redis real en esta máquina si Docker sigue no disponible. (b) El endpoint `/tasks/{task_id}` depende de la retención del result backend y no debe usarse como fuente de verdad. (c) Sigue pendiente observar un run verde de GitHub Actions desde esta sesión, según Fase 6.5. (d) No existe IA real ni procesamiento pesado todavía; Celery solo mueve el mock fuera del request.

## 23. Fase 7.5 — smoke operativo real con Redis + Celery worker

Objetivo: comprobar que el flujo asíncrono funciona con cola real, no solo con Celery eager mode. No se cambia lógica de negocio: el worker sigue llamando `process_analysis_run_task()`, que usa `ProcessAnalysisRunUseCase` y `MockInferenceEngine`. Sin IA real, sin PyTorch, sin entrenamiento, sin datasets, sin métricas inventadas, sin frontend, sin autenticación y sin taxonomía microbiológica.

**Diagnóstico de configuración.** `docker-compose.yml` ya define `postgres` y `redis` como servicios separados. `Settings` separa `DATABASE_URL` de `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`, y agrega `API_BASE_URL` para scripts operativos. `celery_app.py` configura JSON-only, cola `analysis` y Redis configurable; `analysis_tasks.py` no depende de FastAPI y conserva el camino por `ProcessAnalysisRunUseCase`.

**Script de smoke real.** `scripts/celery_smoke_test.py` asume que PostgreSQL, Redis, la API y el worker ya están corriendo. Ejecuta: `GET /health`, crea `Sample`, `ModelVersion mock`, imágenes Petri/micro generadas en memoria con Pillow, `AnalysisRun`, llama `POST /process-async`, obtiene `task_id`, consulta `GET /tasks/{task_id}` hasta `SUCCESS`, verifica que el `AnalysisRun` ya no esté `pending`, consulta `Prediction`, crea una `HumanReview` final y consulta la final. Falla con exit code 1 si algo no coincide o si la task no llega a `SUCCESS` dentro del timeout. No usa datasets ni imprime secretos.

**CI `celery-smoke`.** `.github/workflows/tests.yml` tiene un tercer job que levanta service containers efímeros de PostgreSQL 16 y Redis 7, instala dependencias, ejecuta `alembic upgrade head`, inicia un worker Celery real en background, inicia la API en background, y corre `python scripts/celery_smoke_test.py`. No hay deploy, no hay build de imagen Docker, no hay secrets, no hay IA real ni PyTorch.

**Fuente de verdad.** `GET /tasks/{task_id}` solo prueba que el backend de resultados real recibe el resultado de Celery. La fuente durable sigue siendo `AnalysisRun` y `Prediction`; el smoke verifica ambos después del `SUCCESS`.

**Riesgos pendientes antes de Fase 8.** (a) Si no se puede ejecutar Docker localmente, el smoke real queda validado por GitHub Actions, no por esta máquina. (b) El result backend de Celery sigue siendo auxiliar y puede tener retención limitada. (c) El worker real todavía procesa solo el mock determinista; una futura IA real requerirá otra fase de validación, no una extensión silenciosa de esta.

## 24. Fase 8 — dataset curado, ground truth y exportación de manifest

Objetivo: crear una capa formal para congelar datasets curados de
`AnalysisRun` revisados por expertos, derivar una etiqueta de referencia y
exportar un manifest reproducible para entrenamiento futuro. No se entrena
ningún modelo, no se calcula ninguna métrica, no se descarga dataset externo,
no se copia ninguna imagen, no se implementa IA real/PyTorch/frontend/auth, y
no se agrega taxonomía microbiológica.

**Diagnóstico de entidades existentes.** `Sample`, `PetriImage`,
`MicroImage`, `AnalysisRun`, `Prediction` y `HumanReview.is_final` ya
proporcionaban la trazabilidad necesaria: muestra de arándano, imagen de
caja Petri, imagen microscópica, ejecución concreta, predicción mock
preliminar y revisión humana final. Faltaba congelar una versión de dataset,
guardar sus items trazables, derivar una etiqueta de referencia desde la
revisión final y exportar un manifest determinista.

**Nuevas entidades.** `DatasetSnapshot` representa una versión congelada con
`name`, `version`, `selection_criteria`, `item_count`,
`label_distribution`, `created_by` y `notes`. Es inmutable: no existe caso de
uso de update. `DatasetItem` representa un item incluido o excluido dentro de
un snapshot y conserva FKs a `AnalysisRun`, `Sample`, `PetriImage`,
`MicroImage`, `Prediction` y `HumanReview` final. No copia imágenes ni borra
datos originales.

**Reglas de elegibilidad.** Un item entrenable requiere `AnalysisRun`
existente, `Prediction` existente, `HumanReview` final existente, Petri y
Micro existentes, y un estado distinto de `pending`/`processing`.
`Prediction` sola nunca es ground truth. `rejected_invalid_sample` queda
excluido del dataset entrenable. `marked_inconclusive` queda excluido por
default y solo entra si `include_inconclusive=true`. No se generan etiquetas
taxonómicas.

**Derivación de ground truth.** Si la revisión final es `confirmed`, la
etiqueta de referencia es `Prediction.predicted_label` porque el experto la
aceptó. Si es `corrected`, la etiqueta es `HumanReview.corrected_label`. Si
es `marked_inconclusive`, la etiqueta es `inconclusive` solo si se pidió
incluir no concluyentes. Si es `rejected_invalid_sample`, el caso queda fuera
del dataset entrenable. `Prediction` y `HumanReview` no se modifican.

**Persistencia.** La migración `0003_dataset_snapshots.py` crea
`dataset_snapshots` y `dataset_items`, con FKs a las tablas originales,
`JSONB` para criterios/distribución en PostgreSQL, reutilización del enum
`predicted_label` para `ground_truth_label`, y constraint único
`dataset_snapshot_id + analysis_run_id` para impedir duplicados dentro del
mismo snapshot. Las pruebas SQLite usan `PortableJSON`; las PostgreSQL
validan migración, tablas, FKs, JSONB y constraint único.

**Casos de uso y API.** `CreateDatasetSnapshotUseCase` selecciona candidatos,
aplica reglas, deriva ground truth, calcula `item_count` y
`label_distribution`, y guarda snapshot + items dentro de `UnitOfWork`.
`GetDatasetSnapshotUseCase`, `ListDatasetSnapshotsUseCase` y
`ListDatasetItemsUseCase` consultan DTOs. La API agrega:
`POST /api/v1/datasets/snapshots`, `GET /api/v1/datasets/snapshots`,
`GET /api/v1/datasets/snapshots/{id}`,
`GET /api/v1/datasets/snapshots/{id}/items` y
`GET /api/v1/datasets/snapshots/{id}/manifest`.

**Manifest.** `DatasetManifestExporter` devuelve JSON determinista ordenado
por `analysis_run_id`, con metadata del snapshot, distribución de etiquetas
y items que incluyen rutas de imagen, metadata básica Petri/Micro,
`ground_truth_label`, decisión de revisión fuente, etiqueta de predicción y
`final_review_id`. No incluye contenido binario, secretos, métricas de
modelo ni taxonomía.

**Riesgos pendientes antes de Fase 9.** El dataset queda preparado para
entrenamiento futuro, pero todavía falta definir protocolo externo de
curación, control de calidad de revisores, política de versionado semántico
de datasets, almacenamiento/descarga de manifests como artefactos, y
validación de cualquier modelo real en una fase separada. El motor sigue
siendo `MockInferenceEngine`.

## 25. Fase 9 — dataset release, particiones train/validation/test y control de fuga de datos (implementada)

Objetivo: la Fase 8 dejó el dataset curado como un `DatasetSnapshot` congelado, pero sin ningún mecanismo formal para generar particiones reproducibles de entrenamiento. Sin control explícito, dos imágenes de la misma muestra podrían terminar en particiones distintas (fuga de datos), y repetir el mismo experimento con distintos desarrolladores podría producir particiones diferentes sin ninguna razón declarada. Esta fase cierra esa brecha sin entrenar nada ni tocar el snapshot existente.

**Diagnóstico de `DatasetSnapshot`/`DatasetItem` (Tarea 1).** `DatasetItem` ya guarda `sample_id` **directamente** (no solo vía `analysis_run_id`) — exactamente el campo necesario para particionar sin joins adicionales. También guarda `ground_truth_label`, útil para calcular distribución de etiquetas por partición. `included=True` es la señal de que un item es apto para split (los excluidos no tienen ground truth confiable). Lo que faltaba documentar: `Sample.lot_code` existe en el dominio pero **no** se copia a `DatasetItem` — por lo que particionar por `sample_id` (como se implementó) previene fuga a nivel de muestra, pero no previene que dos `Sample`s del mismo lote terminen en particiones distintas. Se documenta como riesgo conocido, no se resuelve en esta fase (ver más abajo).

**Reglas de partición (Tarea 2).** (1) La partición ocurre exclusivamente a nivel de `sample_id`, nunca a nivel de imagen/item individual. (2) Todos los `DatasetItem`s del mismo `Sample` comparten partición — garantizado agrupando primero por `sample_id` antes de cualquier asignación. (3) El riesgo de fuga por `lot_code` queda documentado (aquí y en `docs/development.md` §18), no resuelto — resolverlo requeriría una estrategia de partición por lote, fuera de alcance de esta fase. (4) La división es determinista vía `random.Random(random_seed)`. (5) Ratios por defecto 70/15/15. (6) Configurables por request. (7) Validados: deben sumar 1.0 (tolerancia `1e-6`) y estar en `[0,1]`, si no `InvalidSplitRatiosError` (dominio) → 422. (8) Datasets pequeños no fallan: si una partición queda vacía, se registra un `WARNING` explícito vía `logging`, pero la operación completa igual. (9) No hay balanceo artificial de etiquetas — el único criterio es el ratio por muestra. (10) No se duplican imágenes ni bytes en ningún momento; solo se referencian ids ya existentes.

**Entidades `DatasetRelease` y `DatasetSplitItem` (Tarea 3, dominio).** `DatasetRelease` (`domain/entities/dataset_release.py`) es un dataclass congelado con `dataset_snapshot_id`, `name`, `version`, `split_strategy`, `random_seed`, `train_ratio`/`validation_ratio`/`test_ratio`, `item_count`/`train_count`/`validation_count`/`test_count`, `label_distribution`, `split_distribution`, `created_at`, `created_by`, `notes`. Su `__post_init__` llama a `validate_split_ratios()` (función de módulo, no método privado) — la misma función la usa `DatasetSplitter` **antes** de que exista un `DatasetRelease` al que asociarle la validación, evitando duplicar la regla en dos sitios con posibilidad de divergencia. `DatasetSplitItem` (`domain/entities/dataset_split_item.py`) referencia `dataset_release_id` + `dataset_item_id`, con `sample_id` y `ground_truth_label` desnormalizados para que las auditorías de fuga y el manifest no necesiten un join adicional. Nuevo enum `DatasetSplit` (`train`/`validation`/`test`) — categoría de ingeniería de datos, nunca una clase microbiológica.

**Modelos SQLAlchemy y migración `0004` (Tarea 4).** Tablas `dataset_releases` (FK a `dataset_snapshots`, `PortableJSON` para `label_distribution`/`split_distribution`, sin CHECK de suma de ratios a nivel de BD — la aritmética de punto flotante en SQL sería frágil; el dominio ya lo garantiza) y `dataset_split_items` (FK a `dataset_releases`, `dataset_items` y `samples`; `UniqueConstraint(dataset_release_id, dataset_item_id)`; columna `split` con el nuevo enum nativo `dataset_split` en PostgreSQL). El enum `dataset_split` es **nuevo** en esta migración — se declara con `create_type=False` y se crea/destruye explícitamente vía `.create(bind, checkfirst=True)`/`.drop(bind, checkfirst=True)`, igual que los enums originales de la migración `0001` (a diferencia de `predicted_label`/`review_decision`, reutilizados aquí con `create_type=False` y sin llamada a `.create()`, porque ya existen desde `0001`). Verificado con `alembic upgrade head --sql` y `alembic downgrade head:base --sql` contra el dialecto PostgreSQL antes de tocar ninguna base real.

**Puertos y repositorios (Tarea 5).** `DatasetReleaseRepositoryPort` (`add`, `get_by_id`, `list_by_dataset_snapshot_id`, `list_all`) y `DatasetSplitItemRepositoryPort` (`add_many`, `list_by_dataset_release_id`, `list_by_split`) — sin lógica de partición, solo persistencia. Implementaciones SQLAlchemy siguen el patrón `auto_commit` ya establecido; `SqlAlchemyDatasetSplitItemRepository.add_many()` traduce `IntegrityError` a `DuplicateDatasetSplitItemError`. `UnitOfWorkPort` se extendió con `dataset_release_repository`/`dataset_split_item_repository`.

**`DatasetSplitter` (Tarea 6, `application/services/dataset_splitter.py`).** Algoritmo: agrupar `DatasetItem`s por `sample_id` → ordenar los `sample_id` únicos por su forma de texto (nunca confiar en el orden accidental de la consulta SQL) → `random.Random(random_seed).shuffle()` sobre esa lista ya ordenada → cortar en tres segmentos con `int(total_samples * ratio)` para train/validation, y el resto para test (garantiza que la suma de conteos de muestra sea exactamente el total, incluso cuando los ratios no dividen exacto). Los conteos de **muestras** por partición son función solo de `total_samples` y los ratios — **no dependen del seed** (verificado en test); solo el *contenido* de cada partición depende del seed. Deliberadamente no se usa `sklearn` (no había justificación para una dependencia nueva pesada para tres líneas de aritmética determinista).

**Casos de uso (Tarea 7-8).** `CreateDatasetReleaseUseCase`: busca el snapshot (404 si no existe), lista sus `DatasetItem`s y filtra a `included=True` (409 `empty_dataset_snapshot` si el resultado es vacío), ejecuta `DatasetSplitter`, construye `DatasetRelease` + lista de `DatasetSplitItem`, y persiste ambos dentro de un único `UnitOfWork`. Nunca escribe en `DatasetSnapshot` ni en `DatasetItem` — solo los lee. `GetDatasetReleaseUseCase`, `ListDatasetReleasesUseCase`, `ListDatasetSplitItemsUseCase` son de solo lectura.

**Manifest de release (Tarea 9, `DatasetReleaseManifestExporter`).** Reutiliza `DatasetItemRepositoryPort.list_by_dataset_snapshot_id()` ya existente (indexado en memoria por id) en vez de ampliar el contrato del puerto con un `get_by_id()` nuevo solo para este caso de uso. Ordena determinísticamente por `(split, analysis_run_id, dataset_split_item.id)`. Exporta: metadata de la release (ratios, conteos, distribuciones), y por item: `split`, `analysis_run_id`, `sample_code`, rutas de imagen, `ground_truth_label`, `source_review_decision`, `prediction_label`, `final_review_id`. Sin binarios, sin secretos, sin métricas de modelo, sin taxonomía — mismo contrato de "solo metadata" que el manifest de snapshot de la Fase 8.

**Endpoints nuevos** (`interfaces/api/v1/routers/datasets.py`, mismo router que Fase 8):

| Método | Ruta | Caso de uso |
|---|---|---|
| POST | `/api/v1/datasets/releases` | `CreateDatasetReleaseUseCase` |
| GET | `/api/v1/datasets/releases` | `ListDatasetReleasesUseCase` |
| GET | `/api/v1/datasets/releases/{id}` | `GetDatasetReleaseUseCase` |
| GET | `/api/v1/datasets/releases/{id}/items` | `ListDatasetSplitItemsUseCase` |
| GET | `/api/v1/datasets/releases/{id}/manifest` | `DatasetReleaseManifestExporter` |

**Mapeo de errores nuevo:** `DatasetReleaseNotFoundError`→404, `EmptyDatasetSnapshotError`→409, `DuplicateDatasetSplitItemError`→409, `InvalidSplitRatiosError`→422.

**Tests nuevos (34).** Unitarios (24): validación de ratios (aceptación/rechazo, dentro y fuera de rango), determinismo con mismo seed (incluye insensibilidad al orden de entrada), partición distinta con seed distinto, todos los items de un mismo Sample en el mismo split, sin duplicados, dataset vacío falla (`ValueError` en el splitter, `EmptyDatasetSnapshotError` en el caso de uso), dataset pequeño no falla y registra warning, conteos de muestra independientes del seed, distribución de etiquetas/splits, snapshot/items no modificados, manifest determinista sin taxonomía. API (4): flujo completo con verificación de split/ground_truth/manifest/`X-Request-ID`, 404 por snapshot inexistente, 409 por snapshot vacío, 422 por ratios inválidos. PostgreSQL (6, `tests/integration/postgres/test_dataset_release_schema.py`): tablas creadas por la migración, constraint único `(dataset_release_id, dataset_item_id)`, `JSONB` real para `split_distribution`, enum `dataset_split` almacena el valor, FKs de `dataset_split_items` y `dataset_releases` aplicadas. El job `postgres-migrations` de CI ya ejecuta `pytest -m postgres tests/integration/postgres` sin cambios — recoge estos tests automáticamente.

**Riesgos pendientes antes de Fase 10.** (a) Fuga por `lot_code` documentada pero no resuelta — si en el futuro se requiere partición por lote, será una estrategia (`split_strategy`) nueva y explícita, no una modificación silenciosa de la actual. (b) No existe versionado semántico obligatorio de releases (nombre/versión son campos libres, sin unicidad forzada a nivel de BD). (c) Los 6 tests PostgreSQL de esta fase no se ejecutaron localmente (sin Docker en este entorno) — su validación real depende del job `postgres-migrations` en GitHub Actions. (d) Sigue sin existir entrenamiento real, IA real, ni taxonomía — fuera de alcance por diseño.

## 26. Fase 10 — estrategias avanzadas de partición y control de fuga por lote/origen (implementada)

Objetivo: la Fase 9 resolvía la fuga a nivel de `Sample` (`by_sample`), pero el riesgo de fuga por lote quedó documentado como pendiente en §25. Esta fase lo cierra parcialmente añadiendo dos estrategias de agrupación más estrictas — `by_lot` y `by_origin_lot` — sin entrenar ningún modelo ni tocar el motor mock.

**Diagnóstico (Tarea 1).** `DatasetSplitter` agrupaba exclusivamente por `item.sample_id` (el único campo de agrupación disponible en `DatasetItem`). `DatasetItem` **no** contiene `lot_code` ni `origin` — solo `Sample` los tiene, y `DatasetItem` únicamente referencia `sample_id`. `DatasetRelease.split_strategy` era un `str` libre (con valor por defecto `"random_by_sample"`, nunca validado contra ningún conjunto cerrado). Cambio mínimo necesario: (1) un enum cerrado de estrategias; (2) una forma de resolver `lot_code`/`origin` por `sample_id` sin ensanchar `DatasetItem`; (3) `DatasetSplitter` debía aceptar la estrategia y esa metadata externa para decidir la clave de agrupación. Riesgo identificado al modificar: cambiar `split_strategy` de `str` a enum rompe cualquier release existente cuyo valor no sea uno de los tres nuevos — de ahí la migración de compatibilidad de datos (ver más abajo).

**`SplitStrategy` (Tarea 2, `domain/enums/split_strategy.py`).** `BY_SAMPLE` (`sample_id`), `BY_LOT` (`Sample.lot_code`), `BY_ORIGIN_LOT` (`f"{origin}::{lot_code}"`). Regla explícita y no negociable: ante metadata incompleta, `by_lot`/`by_origin_lot` **fallan** (`DatasetSplitMetadataError` → 422), nunca degradan silenciosamente a `by_sample` — degradar ocultaría exactamente el riesgo de fuga que la estrategia más estricta pretendía prevenir.

**`DatasetRelease.split_strategy`: de `str` libre a `SplitStrategy` + `CHECK` (Tarea 3).** Se optó por un `CheckConstraint` sobre la columna `String(64)` existente (`split_strategy IN ('by_sample', 'by_lot', 'by_origin_lot')`), no por un tipo `ENUM` nativo de PostgreSQL — evita una migración `ALTER COLUMN ... TYPE ... USING` (con su complejidad y riesgo de bloqueo), y sigue el mismo patrón ya usado en este proyecto para `predictions.confidence_score` (value object en dominio + `CheckConstraint` en la tabla como respaldo, sin necesitar un tipo SQL especial). Migración `0005`: primero normaliza cualquier fila existente con `split_strategy = 'random_by_sample'` (el único valor que la Fase 9 llegó a escribir) a `'by_sample'` — semánticamente idénticos, ya que toda release de la Fase 9 agrupaba por `sample_id` — y luego añade el `CHECK`. Verificado offline con `alembic upgrade head --sql` y `alembic downgrade head:base --sql` contra el dialecto PostgreSQL. La entidad de dominio, el DTO de aplicación y el schema Pydantic pasan de `str` a `SplitStrategy` de forma coherente; el mapper ORM→entidad hace `SplitStrategy(model.split_strategy)` al leer, y el repositorio hace `.value` al escribir.

**`DatasetSplitter` generalizado (Tarea 4).** En vez de tres implementaciones paralelas, se introdujo una única función `_grouping_key(item, strategy, sample_metadata)` que resuelve la clave de agrupación según la estrategia — `by_sample` sigue usando `str(item.sample_id)` exactamente como antes (comportamiento verificado sin cambios en los 14 tests preexistentes), mientras que `by_lot`/`by_origin_lot` consultan un nuevo `SampleSplitMetadata` (dataclass mínimo con `sample_id`/`lot_code`/`origin`) indexado por `sample_id`. El resto del algoritmo (ordenar claves de grupo por su forma de texto, `random.Random(seed).shuffle`, cortar por `int(total*ratio)`) es exactamente el mismo para las tres estrategias — cero duplicación de la lógica de partición determinista. `strategy` tiene valor por defecto `SplitStrategy.BY_SAMPLE` en la firma de `split()`, así que ninguna llamada existente necesitó cambiar.

**Validación de metadata (Tarea 5).** Nueva excepción `DatasetSplitMetadataError(ApplicationError)`, lanzada por `DatasetSplitter` en cuanto encuentra un item cuyo `Sample` no tiene la metadata que la estrategia solicitada requiere (o cuyo `sample_metadata` ni siquiera fue provisto). Mapeada a `422 dataset_split_metadata_error` en `error_handlers.py`, con el mismo formato `{"error": {"code", "message"}}` del resto del sistema — el mensaje no expone nada sensible, solo el `sample_id` afectado y qué campo falta.

**`CreateDatasetReleaseUseCase` actualizado (Tarea 6).** Nueva dependencia: `SampleRepositoryPort`. Solo resuelve `sample_metadata` (un `get_by_id` por cada `sample_id` único referenciado) cuando `request.split_strategy != BY_SAMPLE` — evita el costo extra en el caso más común sin caer en optimización prematura para los demás. El resto del flujo (validar snapshot, filtrar items incluidos, ejecutar el splitter, construir `DatasetRelease` + `DatasetSplitItem`s, persistir todo dentro de un único `UnitOfWork`) no cambió de forma.

**Manifest ampliado (Tarea 7).** `DatasetReleaseManifestExporter` ahora incluye `split_strategy` a nivel de release y `sample_id`/`lot_code`/`origin` por item — un manifest, por sí solo, ya permite auditar qué unidad de prevención de fuga (Sample/lote/origen+lote) respeta esa release en concreto, sin consultar la base de datos aparte. Sigue sin binarios, secretos, taxonomía ni métricas de modelo.

**API y schemas (Tarea 8).** Sin cambios de rutas. `DatasetReleaseCreate`/`DatasetReleaseRead` (Pydantic) y `CreateDatasetReleaseRequest`/`DatasetReleaseDTO` (aplicación) pasan `split_strategy` de `str` a `SplitStrategy`, con default `BY_SAMPLE` — un valor de estrategia desconocido en el body ya no llega ni al caso de uso: Pydantic/FastAPI lo rechaza con su formato de error por defecto (`{"detail": [...]}`), consistente con la convención ya establecida en este proyecto para enums inválidos en el borde HTTP (ver CLAUDE.md §7). `X-Request-ID` no se vio afectado.

**DTOs/mappers/repos (Tarea 9).** `DatasetItemDTO`/`DatasetSplitItemDTO` no necesitaron ensancharse — la metadata de lote/origen se resuelve a través de `Sample`, nunca se duplica en `DatasetItem`. Se evaluó explícitamente ensanchar `DatasetItem` con `lot_code`/`origin` y se descartó: hubiera significado modificar una entidad que la Fase 9 declaró inmutable una vez congelada en un snapshot, y hubiera duplicado datos que ya viven en `Sample` (fuente única de verdad).

**Tests nuevos (33).** Unitarios del splitter (12, `test_dataset_splitter_strategies.py`): `by_sample` idéntico al comportamiento por defecto, `by_lot`/`by_origin_lot` agrupan correctamente, fallos de metadata (lot_code ausente, origin ausente, ambos, o `sample_metadata` no provisto en absoluto), determinismo con mismo seed, partición distinta con seed distinto, ratios inválidos, insensibilidad al orden de entrada, sin duplicados. Casos de uso (10, `test_create_dataset_release_use_case_strategies.py`): creación con cada una de las tres estrategias, rechazo por metadata incompleta en `by_lot`/`by_origin_lot`, persistencia de `split_strategy`, corrección de `split_distribution`/`label_distribution`, no-commit cuando falla la creación de `DatasetSplitItem`s (vía un fake que lanza en `add_many`), snapshot/items no modificados. API (8, `test_dataset_release_strategies.py`): estrategia por defecto `by_sample`, flujos completos `by_lot`/`by_origin_lot`, 422 por metadata incompleta en ambas estrategias estrictas, manifest con `split_strategy`/`lot_code`/`origin`, `X-Request-ID` preservado, ausencia de taxonomía. PostgreSQL (3 nuevos sobre los 6 de la Fase 9, `test_dataset_release_schema.py`): el `CHECK` rechaza un valor desconocido, persistencia real de `split_strategy='by_lot'` y `='by_origin_lot'`. El job `postgres-migrations` de CI recoge estos tests automáticamente sin cambios al workflow.

**Riesgos pendientes antes de Fase 11.** (a) Ninguna de las tres estrategias elimina el riesgo de fuga por completo — confusores como "mismo día de procesamiento" o "mismo técnico" no están modelados y requerirían una estrategia nueva y explícita si se necesitan. (b) Elegir una estrategia más estricta de lo que el dataset soporta puede vaciar particiones (`DatasetSplitter` ya registra un `WARNING`, pero no impide la operación). (c) Los 3 tests PostgreSQL nuevos de esta fase no se ejecutaron localmente (sin Docker) — dependen del job `postgres-migrations` en GitHub Actions. (d) Sigue sin existir entrenamiento real, IA real, PyTorch ni taxonomía — fuera de alcance por diseño.

## 27. Fase 11 — contrato de manifest y validación previa a entrenamiento futuro (implementada)

Objetivo: definir el borde de entrada para un entrenamiento futuro sin
entrenar nada todavía. Esta fase no cambia la lógica de negocio, no toca
`ProcessAnalysisRunUseCase`, no reemplaza `MockInferenceEngine`, no agrega
PyTorch, no descarga datasets externos, no calcula métricas de modelo y no
agrega taxonomía.

**Estructura ML.** Se conservaron las carpetas existentes de `ml/`
(`preprocessing`, `petri_branch`, `micro_branch`, `fusion`,
`inference_engine`, `model_registry`) y se agregaron subpaquetes de contrato:
`contracts`, `configs`, `validation`, `data`, `training` y `reports`. Esta
estructura deja explícito dónde vivirá una implementación futura sin mezclarla
con dominio, aplicación, API o tareas Celery.

**Contrato de entrada.** `TrainingManifest` y `TrainingManifestItem` modelan
el JSON exportado por `DatasetReleaseManifestExporter`: release/snapshot,
nombre, versión, estrategia de split, seed, ratios, conteos, distribución de
etiquetas/splits e items con `analysis_run_id`, `sample_id`, `sample_code`,
rutas Petri/micro, `ground_truth_label`, `source_review_decision`,
`prediction_label`, `final_review_id`, `lot_code` y `origin`. No contiene
bytes de imagen ni secretos.

**Configuración futura.** `TrainingConfig` registra intención de experimento
(`experiment_name`, `output_dir`, `model_family`, `fusion_strategy`, batch,
epochs, learning rate, seed, workers y umbrales mínimos). Es validación de
configuración, no un runner. Los `model_family` permitidos son nombres de
familias futuras y un `mock_baseline`; ninguno carga pesos ni instancia
PyTorch.

**Validación de manifest.** `ManifestValidator` produce
`ManifestValidationReport` con errores, warnings, conteos, distribución por
split/label, checks de fuga y recomendaciones. Reglas principales: todos los
splits (`train`, `validation`, `test`) deben existir; Petri y micro path no
pueden estar vacíos; las etiquetas siguen siendo solo las cinco categorías
visuales preliminares; `inconclusive` se excluye salvo permiso explícito;
duplicados de `analysis_run_id` o identidad de item son error; el mismo
`sample_id` no puede aparecer en más de un split; `by_lot` y `by_origin_lot`
se auditan con `lot_code`/`origin`; y los mínimos de tamaño son gates de
preparación, no métricas de rendimiento.

**Validación de rutas.** `ImagePathValidator` comprueba existencia de los
archivos referenciados sin abrir, decodificar, copiar ni transformar imágenes.
El validador no interpreta contenido visual y no afirma identificación
microbiológica.

**Carga y entrenamiento.** `DatasetLoaderPort` define `load_manifest`,
`validate_manifest` e `iter_items`; `JsonManifestDatasetLoader` implementa
solo lectura JSON determinista. `TrainerPort` centraliza la futura frontera de
entrenamiento, pero `train()` lanza `TrainingNotImplementedError` de forma
deliberada. `TrainingRunResult` existe como DTO de salida futura, sin métricas
inventadas.

**CLI.** `scripts/validate_training_manifest.py` carga un manifest JSON,
opcionalmente un config JSON, imprime un `ManifestValidationReport` en JSON y
sale `0` si es válido, `1` si hay errores de validación y `2` si no puede
cargar manifest/config. No toca FastAPI, PostgreSQL, Redis, Celery ni imágenes.

**Tests nuevos.** Unitarios de `ml/` cubren: manifiesto válido, splits vacíos,
paths faltantes, etiquetas/splits inválidos, duplicados, inclusión/exclusión
de `inconclusive`, requisito de split lot-aware, fuga por sample/lote/origen,
umbrales mínimos, validación de rutas, loader JSON, `TrainerPort` sin
implementación y códigos de salida del CLI. No hay tests de accuracy,
precision, recall ni F1 porque no existe evaluación de modelo.

**Riesgos pendientes antes de Fase 12.** (a) Aún no existe entrenamiento real:
la siguiente fase debe decidir explícitamente si seguirá solo validando datos o
si abrirá una implementación de entrenamiento. (b) Los mínimos de tamaño son
controles de preparación, no criterios científicos suficientes. (c) La fuga por
confusores no modelados (día, técnico, equipo, batch de medio) sigue pendiente.
(d) Si una futura fase agrega PyTorch u otra dependencia ML, debe justificarla,
probarla y mantener intacto el contrato de manifest validado aquí.

## 28. Fase 12 — ML Preflight Reports persistentes (implementada)

Objetivo: persistir el resultado de validar un `DatasetRelease` para
entrenamiento futuro, sin entrenar todavía. Esta fase no agrega IA real,
PyTorch, datasets externos, métricas de rendimiento, frontend, autenticación,
taxonomía ni tracking externo de experimentos.

**Entidades.** `TrainingPreflightRun` registra una ejecución de validación:
`dataset_release_id`, `status` (`passed`/`warning`/`failed`), `is_valid`,
`config` JSON, `summary` JSON, conteos por split, distribución de etiquetas,
`split_label_counts`, `leakage_checks`, recomendación, `created_at`,
`created_by` y `notes`. `TrainingPreflightIssue` registra cada error/warning
con `severity`, `code`, `message`, `field` e `item_ref` opcionales. Ninguna
entidad almacena imágenes, binarios, secretos, métricas de modelo o taxonomía.

**Persistencia.** Migración `0006_training_preflight_reports.py` crea
`training_preflight_runs` y `training_preflight_issues`, con FK a
`dataset_releases`, FK issue→run, `CHECK` para status/severity, `JSONB` en
PostgreSQL a través del patrón existente, e índices por `dataset_release_id`,
`created_at` y `preflight_run_id`. Los modelos SQLAlchemy usan
`PortableJSON`, por lo que los tests SQLite siguen funcionando.

**Puertos/repos/UoW.** Se agregaron `TrainingPreflightRunRepositoryPort` y
`TrainingPreflightIssueRepositoryPort`, más implementaciones SQLAlchemy con el
mismo patrón `auto_commit` de datasets. `SqlAlchemyUnitOfWork` expone ambos
repos para guardar run + issues de forma transaccional: si fallan los issues,
el run no queda persistido a medias.

**Caso de uso.** `CreateTrainingPreflightRunUseCase` reutiliza
`DatasetReleaseManifestExporter`, convierte a `TrainingManifest`, ejecuta
`ManifestValidator` con la `TrainingConfig` recibida y, solo si
`validate_image_paths=true`, ejecuta `ImagePathValidator`. No duplica reglas de
validación, no abre imágenes salvo comprobación de existencia de ruta, no
entrena y no modifica `DatasetRelease`, `DatasetSnapshot`, `DatasetItem`,
`Prediction` ni `HumanReview`. Un manifest inválido igualmente genera un run
persistido con `status=failed`.

**API.**

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/ml/preflight-runs` | Valida y persiste un preflight |
| GET | `/api/v1/ml/preflight-runs` | Lista runs |
| GET | `/api/v1/ml/preflight-runs/{id}` | Obtiene detalle + issues |
| GET | `/api/v1/ml/preflight-runs/{id}/issues` | Lista issues |
| GET | `/api/v1/datasets/releases/{id}/preflight-runs` | Historial por release |

**CLI.** `scripts/validate_training_manifest.py` sigue siendo standalone: no
persiste. Su ayuda ahora aclara que el historial auditable se obtiene por API.

**Tests nuevos.** Unitarios (8): estados `passed`/`warning`/`failed`, issues
por error/warning, persistencia de config y conteos, no filesystem cuando
`validate_image_paths=false`, detección de rutas faltantes cuando es `true`,
no mutación de release/items y rollback si falla la persistencia de issues.
API (2): flujo completo con 4 muestras revisadas, snapshot, release,
preflight, consulta de detalle/issues/historial y ausencia de métricas/taxonomía;
caso failed persistido. PostgreSQL (6): tablas, `CHECK` de status/severity,
JSONB, FK a release y FK issue→run.

**Riesgos pendientes antes de Fase 13.** (a) `passed` significa que gates
técnicos pasaron, no que el dataset sea científicamente suficiente. (b) Aún no
hay entrenamiento ni evaluación real. (c) Las rutas de imagen solo se verifican
si el caller lo pide. (d) Sigue pendiente modelar confusores adicionales si el
protocolo científico los requiere.
## 29. Fase 13 - baseline experimental de clase mayoritaria (implementada)

Objetivo: crear un baseline auditable sobre un `DatasetRelease` ya curado y
prevalidado, sin introducir IA real, PyTorch, TensorFlow, CNN, ViT,
entrenamiento de imagenes, datasets externos, frontend, autenticacion,
taxonomia ni cambios al `MockInferenceEngine`.

**Entidades.** `TrainingRun` registra una ejecucion experimental: release,
preflight, `run_kind=baseline`, `baseline_model_type=majority_class`, status,
configuracion, estado del baseline, metricas, resumen, timestamps, autor/notas
y error controlado si falla. `TrainingPrediction` registra una prediccion por
`DatasetSplitItem`, con `ground_truth_label`, `predicted_label`, split,
`is_correct` y referencias al item original. No copia imagenes ni crea
artefactos de modelo.

**Persistencia.** Migracion `0007_training_runs.py` crea `training_runs` y
`training_predictions`, con FKs a releases, preflights, split items y dataset
items; `JSONB` para config/estado/metricas/resumen; `CHECK` para status,
run kind, tipo de baseline, split y etiquetas preliminares permitidas; e
indice unico `(training_run_id, dataset_split_item_id)`.

**Baseline.** `MajorityClassBaselineTrainer` mira solo el split `train` para
elegir la etiqueta mayoritaria revisada. En empate usa el orden del enum
`PredictedLabel`, por lo que el resultado es determinista. Luego predice esa
misma etiqueta para `train`, `validation` y `test`.

**Metricas permitidas.** Solo se calculan metricas reales derivadas de las
`TrainingPrediction` persistidas: accuracy global, accuracy por split, soporte
por split, distribucion de etiquetas por split y matriz de confusion. No se
calcula precision, recall ni F1.

**Caso de uso.** `CreateBaselineTrainingRunUseCase` exige que el preflight no
este fallido y pertenezca al mismo release, reexporta/revalida el manifest, y
persiste todo transaccionalmente. Si la revalidacion falla, crea un
`TrainingRun` `failed` con los errores y sin predicciones. No llama Celery, no
lee imagenes y no modifica `DatasetRelease`, `DatasetSnapshot`, `DatasetItem`,
`Prediction`, `HumanReview` ni `MockInferenceEngine`.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/training-runs/baseline` | Crea un baseline majority-class |
| GET | `/api/v1/ml/training-runs` | Lista training runs |
| GET | `/api/v1/ml/training-runs/{id}` | Obtiene un run |
| GET | `/api/v1/ml/training-runs/{id}/predictions` | Lista predicciones, con filtro opcional `split` |
| GET | `/api/v1/datasets/releases/{id}/training-runs` | Historial por release |
| GET | `/api/v1/ml/preflight-runs/{id}/training-runs` | Historial por preflight |

**Riesgos pendientes antes de Fase 14.** (a) El baseline no prueba suficiencia
cientifica; solo sirve como referencia minima reproducible. (b) Las metricas
dependen del tamano y calidad del dataset curado. (c) Siguen pendientes
confusores no modelados por el protocolo. (d) Sigue sin existir IA real,
PyTorch, entrenamiento profundo, taxonomia ni frontend.

## 30. Fase 14 — Image Dataset Audit tecnico de archivos (implementada)

Objetivo: auditar tecnicamente los archivos Petri/micro referenciados por un
`DatasetRelease` antes de cualquier entrenamiento futuro con imagenes reales,
sin entrenar modelos, sin PyTorch/TensorFlow/CNN/ViT, sin tensores, sin
taxonomia y sin reemplazar `MockInferenceEngine`.

**Diagnostico previo (Tarea 1).** El manifest existente
(`DatasetReleaseManifestExporter`/`TrainingManifest`) ya traia
`petri_image_path`/`micro_image_path`, `sample_id`, `lot_code`, `origin`, pero
no `dataset_item_id`/`dataset_split_item_id` ni las dimensiones/tamano ya
persistidos en `PetriImage`/`MicroImage` (`width`, `height`,
`file_size_bytes`). `ImagePathValidator` (Fase 11) solo comprueba
`Path.exists()`, nunca abre Pillow — sigue existiendo sin cambios como gate
rapido de preflight; el audit tecnico de esta fase es una capa aparte, mas
profunda y persistente.

**Entidades.** `ImageDatasetAuditRun` registra: release, status
(`passed`/`warning`/`failed`), `is_passed` (true para passed/warning, false
para failed — igual semantica que `TrainingPreflightRun.is_valid`), conteos
totales/chequeados/fallidos por modalidad, `warning_count`/`error_count`,
`summary` y cuatro distribuciones JSON (formato, modo de color, dimension,
tamano en bytes). `ImageDatasetAuditIssue` registra un hallazgo por imagen:
severidad, modalidad (`petri`/`micro`), referencias opcionales a
`DatasetItem`/`DatasetSplitItem`, ruta, codigo, mensaje y `details` JSON. Nunca
guardan binarios ni contenido de imagen.

**Extension del manifest.** `TrainingManifestItem` gano seis campos opcionales
nuevos (`dataset_item_id`, `dataset_split_item_id`, `petri_width`,
`petri_height`, `petri_file_size_bytes`, `micro_width`, `micro_height`,
`micro_file_size_bytes`), poblados por `DatasetReleaseManifestExporter` desde
`PetriImage`/`MicroImage` ya cargados en el propio loop de export — sin
consultas adicionales. Esto permite que `ImageDatasetAuditor` dependa
unicamente de `TrainingManifest` + `ImageAuditConfig`, sin inyectar
`PetriImageRepositoryPort`/`MicroImageRepositoryPort`, y sin ampliar
`DatasetItem` con metadata de imagen (que seguiria viviendo solo en
`PetriImage`/`MicroImage`).

**`ImageAuditConfig`.** Configuracion tecnica independiente de
`TrainingConfig`: banderas para activar/desactivar cada validacion
(existencia, legibilidad, formato, dimensiones, modo de color, tamano en
bytes, deteccion de duplicados), umbrales de dimension/tamano de archivo,
formatos y modos de color permitidos, y deteccion de outliers de dimension.
Valida en `__post_init__` que los minimos sean positivos y que los maximos
(si existen) sean mayores que los minimos.

**`ImageDatasetAuditor` y severidad por diseno.** Abre cada imagen con
Pillow de forma liviana: `Image.open().verify()` en un handle para detectar
corrupcion, y una segunda apertura fresca para leer formato/dimensiones/modo
de color (mismo patron que `PillowImageValidator`, Fase 3.5) — nunca crea
tensores ni usa OpenCV/Cellpose. Diseno de severidad, documentado porque el
enunciado dejaba varios codigos a criterio de implementacion: `error`
(bloquea `passed`) para `image_empty_path`, `image_missing`,
`image_unreadable`, `image_format_mismatch` e `image_size_bytes_mismatch`
(el archivo en disco ya no coincide con el tamano registrado al subirlo —
senal de integridad, no de calidad); `warning` (no bloquea) para
`image_too_small`, `image_too_large` (dimension o tamano en bytes segun
`details.reason`), `image_unsupported_color_mode`, `image_metadata_missing`
(el registro de `PetriImage`/`MicroImage` nunca guardo width/height),
`image_dimension_outlier` (mediana de dimensiones por modalidad, umbral 3x) y
`image_duplicate_path`. Un `DatasetItem`/`DatasetSplitItem` con ruta
duplicada, imagen corrupta o formato no permitido nunca se oculta ni se
excluye silenciosamente — siempre genera un hallazgo persistido.

**Persistencia.** Migracion `0008_image_dataset_audit_reports.py` crea
`image_dataset_audit_runs` e `image_dataset_audit_issues`, con FK de runs a
`dataset_releases`, FK de issues a `image_dataset_audit_runs` y
opcionalmente a `dataset_items`/`dataset_split_items`, `CHECK` de
status/severity/modality, y columnas `JSONB` para summary/distribuciones/
`details`. Validada offline con `alembic upgrade head --sql` y
`alembic downgrade head:base --sql` contra el dialecto PostgreSQL.

**Caso de uso.** `CreateImageDatasetAuditRunUseCase` reexporta el manifest
via `DatasetReleaseManifestExporter` (igual patron que el preflight de la
Fase 12), ejecuta `ImageDatasetAuditor`, y persiste
`ImageDatasetAuditRun` + `ImageDatasetAuditIssue` en una unica transaccion
via `UnitOfWorkPort`. Nunca modifica `DatasetRelease`, `DatasetItem`,
`TrainingRun` ni los archivos de imagen; no usa Celery ni PyTorch.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/image-audits` | Ejecuta un audit tecnico de imagenes para un DatasetRelease |
| GET | `/api/v1/ml/image-audits` | Lista audits |
| GET | `/api/v1/ml/image-audits/{id}` | Obtiene un audit con sus issues |
| GET | `/api/v1/ml/image-audits/{id}/issues` | Lista issues de un audit |
| GET | `/api/v1/datasets/releases/{id}/image-audits` | Historial de audits por release |

**Pruebas.** 17 tests unitarios de `ImageDatasetAuditor` (passed/warning/
failed por causa, distribuciones, determinismo, no modifica archivos, no usa
tensores), 10 tests del caso de uso (persistencia, transaccionalidad,
config, listados, no-modificacion de release/item), 9 tests API (flujo
completo, config laxa vs. estricta, imagen faltante real via manifest,
X-Request-ID, ausencia de taxonomia/metricas), 8 tests PostgreSQL (tablas,
CHECKs, JSONB, FKs).

**Riesgos pendientes antes de Fase 15.** (a) Un audit `passed` certifica solo
aptitud tecnica basica del archivo — nunca calidad cientifica, suficiencia de
dataset ni validez microbiologica. (b) La deteccion de outliers de dimension
es una heuristica simple (mediana ± 3x), no un modelo estadistico robusto.
(c) `image_size_bytes_mismatch` solo detecta que el archivo cambio desde que
se registro su tamano — no explica la causa. (d) Sigue sin existir
entrenamiento real, PyTorch, TensorFlow, deep learning, dataset externo,
frontend ni taxonomia.

## 31. Fase 15 — extraccion de features no profunda (implementada)

Objetivo: extraer features tecnicas simples, reproducibles y auditables desde
los archivos Petri/micro de un `DatasetRelease` ya auditado, sin entrenar
modelos, sin PyTorch/TensorFlow/CNN/ViT y sin tensores de entrenamiento.

**Diagnostico previo (Tarea 1).** El manifest (`TrainingManifest`) ya traia
`dataset_item_id`/`dataset_split_item_id`/rutas Petri-micro desde la Fase 14,
suficiente para leer y referenciar imagenes sin ampliar el contrato de nuevo.
`ImageDatasetAuditRun.status` (Fase 14) es la unica senal de si un release
tiene imagenes tecnicamente aptas; esta fase la consume como precondicion en
vez de reimplementar sus checks. `PetriImage`/`MicroImage.width/height` no
son necesarios aqui porque las features de geometria se recalculan siempre
desde el archivo real, nunca desde el valor declarado en la fila.

**Dependencia nueva: numpy.** Se agrego `numpy>=1.24,<2.0` a `pyproject.toml`
(estaba disponible transitivamente en el entorno de desarrollo pero no
declarada, lo que la hacia invisible para una instalacion limpia en CI).
Se usa exclusivamente para aritmetica de arrays (media, desviacion estandar,
histograma, un Laplaciano por diferencias finitas via `np.roll`) — no es
PyTorch/TensorFlow, no crea tensores de entrenamiento ni participa en ningun
grafo de computo; es la misma categoria de herramienta que el modulo
`statistics` de Python, vectorizada para arrays de pixeles.

**Entidades.** `ImageFeatureExtractionRun` registra: release, audit de
origen, status (`completed`/`partial`/`failed`), `is_completed` (true para
completed/partial — el run corrio hasta el final — false solo para failed,
que representa un run que ni siquiera llego a ejecutar la extraccion),
config, conteos (total/procesados/fallidos, vectores totales y por
modalidad), summary y timestamps. `ImageFeatureVector` registra un vector
por imagen: run de origen, release, item, split-item, split, modalidad,
ruta, `features` JSON, `preprocessing` JSON (que se aplico realmente:
conversion a RGB, resize, dimensiones antes/despues) y una version de
extraccion (`v1`) para poder distinguir vectores calculados con una version
futura del algoritmo. Ninguna de las dos guarda binarios, tensores ni
metricas de clasificacion.

**Diseno de status (documentado porque el enunciado dejaba el criterio
abierto).** Cada imagen del manifest se intenta siempre — un fallo nunca
corta el procesamiento de las demas imagenes. Al final: si no hubo ningun
error, `completed`; si hubo al menos un error y
`fail_on_unreadable_image=true` (default), `failed`; si hubo al menos un
error y `fail_on_unreadable_image=false`, `partial`. Esto permite que un
run con imagenes parcialmente rotas siga produciendo vectores utiles para
las imagenes que si funcionaron, mientras la clasificacion del run avisa con
claridad si el conjunto completo es confiable o no.

**`ImageFeatureExtractionConfig`.** Configuracion tecnica independiente de
`TrainingConfig` e `ImageAuditConfig`: banderas para aceptar audits
`passed`/`warning`, conversion a RGB, resize opcional, y banderas para
activar/desactivar cada grupo de features. Valida en `__post_init__` que
`histogram_bins > 0` y que `resize_width`/`resize_height` sean positivos
cuando `resize_enabled=true`.

**`ImageFeatureExtractor` y features calculadas.** Vive en
`ml/preprocessing/image_feature_extractor.py` (el directorio ya existia,
reservado desde fases tempranas, vacio salvo un `.gitkeep`). Abre cada
imagen con el mismo patron de dos aperturas que `PillowImageValidator`
(`verify()` para corrupcion, reapertura para leer datos), y calcula:
geometria (`width`, `height`, `aspect_ratio`, `file_size_bytes` real via
`os.path.getsize`); intensidad (`mean`/`std`/`min`/`max_intensity` sobre la
imagen en escala de grises); color (`mean_r/g/b`, `std_r/g/b`,
`mean_saturation` via `Image.convert("HSV")`, solo si el modo final es
RGB/RGBA); nitidez (`laplacian_variance` via un Laplaciano de diferencias
finitas con `np.roll` — el borde de la imagen se envuelve en vez de rellenarse,
una simplificacion deliberada y documentada para una metrica "aproximada");
textura (`edge_density` por umbral de gradiente, `dark_pixel_ratio`,
`bright_pixel_ratio`); histograma (`grayscale_histogram` de N bins,
normalizado para sumar 1.0). Todo determinista, sin aleatoriedad.

**Caso de uso.** `CreateImageFeatureExtractionRunUseCase` sigue el mismo
patron que `CreateBaselineTrainingRunUseCase` (Fase 13) y
`CreateImageDatasetAuditRunUseCase` (Fase 14): busca el release, busca el
audit, valida pertenencia y status, reexporta el manifest, ejecuta el
extractor, y persiste run + vectores en una unica transaccion via
`UnitOfWorkPort`. Un audit `failed` nunca se acepta, sin importar la config;
un audit que no pertenece al release siempre se rechaza. Nunca modifica
`DatasetRelease`, `DatasetItem` ni `ImageDatasetAuditRun`.

**Persistencia.** Migracion `0009_image_feature_extraction.py` crea
`image_feature_extraction_runs` e `image_feature_vectors`, con FKs a
`dataset_releases`, `image_dataset_audit_runs`, `dataset_items` y
`dataset_split_items`, `CHECK` de status/modality/split, indice unico
`(feature_extraction_run_id, dataset_split_item_id, modality)`, y columnas
`JSONB` para config/summary/features/preprocessing. Todas las columnas con
`CHECK` usan `VARCHAR(32)` — no `VARCHAR(16)` — aplicando la leccion de la
Fase 14 (un valor deliberadamente invalido en un test de CHECK puede exceder
un ancho de columna demasiado angosto y disparar `StringDataRightTruncation`
antes de que el CHECK se evalue, algo que SQLite nunca revela porque ignora
la longitud de VARCHAR). Validada offline con `alembic upgrade head --sql` y
`alembic downgrade head:base --sql`.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/image-feature-extractions` | Ejecuta extraccion de features para un DatasetRelease + ImageDatasetAuditRun |
| GET | `/api/v1/ml/image-feature-extractions` | Lista extracciones |
| GET | `/api/v1/ml/image-feature-extractions/{id}` | Obtiene una extraccion con sus vectores |
| GET | `/api/v1/ml/image-feature-extractions/{id}/vectors` | Lista vectores, filtro opcional `modality`/`split` |
| GET | `/api/v1/datasets/releases/{id}/image-feature-extractions` | Historial por release |
| GET | `/api/v1/ml/image-audits/{id}/feature-extractions` | Historial por audit |

**Pruebas.** 16 tests unitarios de `ImageFeatureExtractor` (features por
tipo, determinismo, imagen faltante/corrupta, resize, no modifica archivos,
sin PyTorch, sin metricas de clasificacion), 12 tests del caso de uso
(aceptacion/rechazo de audit por status y pertenencia, persistencia,
transaccionalidad, listados), 11 tests API (flujo completo, filtros por
modalidad/split, listados por release/audit, casos de error de audit
failed/cruzado, X-Request-ID, ausencia de taxonomia/metricas), 9 tests
PostgreSQL (tablas, CHECKs, indice unico, JSONB, FKs).

**Riesgos pendientes antes de Fase 16.** (a) Las features son puramente
tecnicas — ninguna tiene significado microbiologico validado; no deben
interpretarse como indicadores de crecimiento, contaminacion ni genero/especie.
(b) `laplacian_variance`/`edge_density` son aproximaciones deliberadamente
simples (sin OpenCV), no equivalentes a implementaciones de vision por
computador certificadas. (c) No existe todavia normalizacion/escalado de
features entre imagenes de distinto tamano real — el resize es opcional y
nunca se aplica por defecto. (d) Sigue sin existir entrenamiento real,
PyTorch, TensorFlow, deep learning, dataset externo, frontend ni taxonomia.

## 32. Fase 16 - baseline clasico tabular sobre ImageFeatureVector (implementada)

Objetivo: entrenar un baseline clasico reproducible con features reales ya
extraidas (`ImageFeatureVector`), sin deep learning, sin PyTorch/TensorFlow,
sin cargar imagenes como tensores y sin reemplazar `MockInferenceEngine`.

**Diagnostico.** `ImageFeatureVector.features` ya contiene `X`: escalares y
histogramas pequenos de geometria/intensidad/color/nitidez/textura por
modalidad Petri/micro. `DatasetSplitItem.ground_truth_label` ya contiene `y`,
derivada de revision humana final por las fases de dataset curado; no se usa
`Prediction` como ground truth. El split se respeta por
`DatasetSplitItem.split` y por las referencias persistidas en cada vector.

**Config.** `TabularFeatureTrainingConfig` selecciona
`feature_extraction_run_id`, `model_type=logistic_regression_tabular`,
modalidades (`petri_only`, `micro_only`, `concatenate`), estandarizacion,
`max_iter`, `random_seed`, minimos de train/clases, `allow_inconclusive`,
`class_weight`, `solver` y `fail_on_missing_feature`. Valida que al menos una
modalidad sea usable y que no se pidan modelos profundos.

**FeatureMatrixBuilder.** Vive en `ml/training/feature_matrix_builder.py`.
Consume solo `ImageFeatureVector` + `DatasetSplitItem`; aplana JSON numerico
de forma deterministica, expande listas numericas pequenas como columnas,
prefija por modalidad (`petri__...`, `micro__...`), produce `X_train`,
`X_validation`, `X_test`, labels por split y referencias a items. Si falta una
modalidad requerida y `fail_on_missing_feature=true`, falla en vez de imputar
silenciosamente. No abre archivos de imagen.

**Trainer.** `ClassicalTabularBaselineTrainer` usa scikit-learn
`LogisticRegression` (con `StandardScaler` opcional). Ajusta solo con train;
validation/test se usan despues para prediccion y metricas. Metricas reales
persistidas: `accuracy_overall`, `accuracy_by_split`, `support_by_split`,
`label_distribution_by_split`, `confusion_matrix` y
`confusion_matrix_by_split`. Precision/recall/F1 quedan fuera de alcance.

**Persistencia.** Se reutilizan `TrainingRun` y `TrainingPrediction`. No se
crean tablas nuevas para predicciones ni se serializa el modelo. Migracion
`0010_classical_tabular_baseline.py` solo amplia el `CHECK`
`ck_training_runs_baseline_model_type` para aceptar
`logistic_regression_tabular`; el `baseline_state` guarda
`feature_extraction_run_id`, `feature_names`, labels de clase, si hubo scaler,
parametros basicos y conteo train.

**Caso de uso.** `CreateClassicalBaselineTrainingRunUseCase` exige:
`DatasetRelease` existente, `TrainingPreflightRun` no fallido y del mismo
release, `ImageFeatureExtractionRun` `completed` y del mismo release, y
features disponibles. Construye la matriz, entrena, persiste
`TrainingRun completed` + `TrainingPrediction`s en una transaccion. Fallos de
forma de datos entrenables (por ejemplo una sola clase en train) se persisten
como `TrainingRun failed` sin predicciones.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/training-runs/classical-baseline` | Crea baseline logistic-regression tabular desde `ImageFeatureVector` |

**Dependencia nueva.** `scikit-learn>=1.4,<2.0` se agrega a
`pyproject.toml` solo para este baseline tabular clasico. No es PyTorch,
TensorFlow ni deep learning.

**Riesgos pendientes antes de Fase 17.** (a) Logistic regression puede ser
inestable o poco informativa en datasets pequenos; sus metricas son reales
pero no evidencia cientifica definitiva. (b) No se persiste un artefacto de
modelo reproducible todavia; solo config/estado/metricas/predicciones. (c) La
calidad de features depende de la consistencia de captura y preprocesamiento.
(d) Sigue sin existir IA real de inferencia, deep learning, dataset externo,
frontend, autenticacion ni taxonomia.

## 33. Fase 17 - comparacion de TrainingRuns y baseline candidato (implementada)

Objetivo: comparar `TrainingRun` ya persistidos para una misma
`DatasetRelease` y registrar un candidato baseline preliminar, sin entrenar
modelos nuevos, sin recalcular predicciones y sin tocar imagenes.

**Diagnostico.** Fase 13 y Fase 16 ya persisten `TrainingRun.metrics` y
`TrainingPrediction`. La comparacion se apoya solo en esas metricas
persistidas (`accuracy_by_split` y `support_by_split`); no abre manifests,
no lee imagenes, no entrena, no consulta datasets externos y no cambia
`MockInferenceEngine`.

**Entidades.** `TrainingRunComparison` registra release, nombre, metrica
primaria (`accuracy`), split primario (`validation` o `test`), politica de
seleccion, candidato seleccionado opcional, summary JSON, warnings, autor y
notas. `TrainingRunComparisonEntry` registra una snapshot por run: rank,
modelo baseline, accuracies por split, support por split, gap de
generalizacion, snapshot de metricas y summary. Las filas conservan FK al
`TrainingRun` original; no copian predicciones ni imagenes.

**Reglas.** Solo se comparan al menos dos runs `completed` del mismo release.
Se rechazan runs sin metricas, sin accuracy del split primario o sin soporte
del split primario. El ranking es descendente por accuracy del split
seleccionado. En empate, `prefer_simpler_if_tie` prioriza
`majority_class` antes de `logistic_regression_tabular`; `no_auto_selection`
no marca candidato aunque guarde el ranking. Los warnings de bajo soporte son
advertencias auditables, no metricas nuevas ni aprobacion cientifica.

**Persistencia.** Migracion `0011_training_run_comparisons.py` crea
`training_run_comparisons` y `training_run_comparison_entries`, con FK a
`dataset_releases`/`training_runs`, CHECKs de metrica/split/politica/modelo,
JSONB para summary/warnings/snapshots, e indice unico
`(comparison_id, training_run_id)` para evitar duplicados.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/training-run-comparisons` | Crea una comparacion desde TrainingRuns completados |
| GET | `/api/v1/ml/training-run-comparisons` | Lista comparaciones, con filtro opcional `dataset_release_id` |
| GET | `/api/v1/ml/training-run-comparisons/{id}` | Obtiene una comparacion con entries |
| GET | `/api/v1/ml/training-run-comparisons/{id}/entries` | Lista entries rankeadas |
| GET | `/api/v1/datasets/releases/{id}/training-run-comparisons` | Historial por release |

**Riesgos pendientes antes de Fase 18.** (a) El candidato seleccionado es
preliminar: depende del tamano y calidad del split usado. (b) Accuracy por si
sola puede ocultar sesgos o clases minoritarias; precision/recall/F1 siguen
fuera de alcance hasta que se apruebe una fase especifica. (c) No existe aun
promocion de modelo ni artefacto reproducible de modelo. (d) Sigue sin existir
IA real de inferencia, deep learning, dataset externo, frontend, autenticacion
ni taxonomia.

## 34. Fase 18 - revision de referencias externas de vision microbiologica

Fase 18 es documental. Crea
`docs/references/microbiology_cv_landscape.md` como mapa tecnico-cientifico
para decidir que fuentes externas podrian orientar fases futuras, sin adoptar
codigo, datos, modelos ni dependencias.

El documento clasifica referencias como CSI-Microbes Identification
(referencia no resuelta), YOLOv5-style bacteria detection, MEMTrack, SinfNet
(referencia no resuelta), DIBaS, surveys/revisiones, deteccion de colonias en
Petri y clinical bacterial datasets. Para cada una separa utilidad en Petri,
micro, video/tracking, dependencia de deep learning, necesidad de dataset
externo, compatibilidad, riesgo principal y uso recomendado.

Conclusion de arquitectura: no hay fuente externa apta para adopcion inmediata
como codigo/modelo/dataset. La recomendacion para Fase 19 es un prototipo
clasico de segmentacion de colonias en Petri, antes de YOLO/deep learning,
porque el proyecto aun no tiene bounding boxes, mascaras ni dataset propio
suficiente para object detection o modelos profundos.

Fase 18 no modifica endpoints, casos de uso, entidades, repositorios,
migraciones, base de datos, workflow CI, `MockInferenceEngine` ni logica de
negocio. Sigue sin agregar PyTorch, TensorFlow, YOLO, CNN, ViT, deep learning,
dataset externo, frontend, autenticacion, taxonomia, MLflow, TensorBoard o
Weights & Biases.

## 35. Fase 19 - prototipo clasico de segmentacion Petri

Objetivo: detectar y persistir regiones candidatas geometricas en imagenes
Petri de un `DatasetRelease`, antes de cualquier YOLO/deep learning y sin
afirmar colonias reales ni taxonomia.

**Dependencia.** Se agrega `opencv-python-headless>=4.9,<4.11`, no la variante
con GUI. El rango evita OpenCV 4.13 porque exige `numpy>=2`, incompatible con
la restriccion existente `numpy<2.0`. OpenCV se usa solo para vision clasica:
lectura auxiliar, gris/color, blur, thresholding, morfologia, contornos,
bounding boxes y mediciones geometricas. No se usan OpenCV DNN, YOLO, pesos ni
modelos preentrenados.

**Config.** `PetriSegmentationConfig` permite solo
`algorithm=classical_threshold`; threshold `otsu`/`adaptive`/`manual`; filtros
por area, circularidad y borde; morfologia; `max_regions`; y version
`petri_classical_v1`. `save_debug_masks=true` se rechaza en esta fase para no
persistir mascaras ni rutas de artefactos no definidos.

**Servicio.** `ClassicalPetriSegmenter` consume `TrainingManifest` y procesa
solo `TrainingManifestItem.petri_image_path`. Ignora `micro_image_path`, no
modifica archivos, continua si una imagen falla y clasifica el run como
`completed`, `partial` o `failed`.

**Persistencia.** Migracion `0012_petri_segmentation.py` crea
`petri_segmentation_runs` y `petri_segmentation_regions`. `PetriSegmentationRun`
guarda release, audit opcional, status, config, conteos y summary.
`PetriSegmentationRegion` guarda una region candidata por contorno filtrado:
area, perimetro, centroide, bounding box, circularidad, solidez, intensidad
media, split y referencias a `DatasetItem`/`DatasetSplitItem`. Indice unico:
`(segmentation_run_id, dataset_split_item_id, region_index)`.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/petri-segmentations` | Ejecuta segmentacion Petri clasica para un DatasetRelease |
| GET | `/api/v1/ml/petri-segmentations` | Lista runs, con filtros opcionales |
| GET | `/api/v1/ml/petri-segmentations/{id}` | Obtiene un run con regiones |
| GET | `/api/v1/ml/petri-segmentations/{id}/regions` | Lista regiones candidatas, filtro opcional por split |
| GET | `/api/v1/datasets/releases/{id}/petri-segmentations` | Historial por release |
| GET | `/api/v1/ml/image-audits/{id}/petri-segmentations` | Historial por audit |

**Limites.** Una region candidata es solo un segmento geometrico aproximado,
no una colonia confirmada. Fase 19 no entrena modelos, no calcula metricas
microbiologicas, no usa PyTorch/TensorFlow/YOLO/CNN/ViT/deep learning, no
descarga datasets externos, no agrega frontend/autenticacion/taxonomia y no
reemplaza `MockInferenceEngine`.

## 36. Fase 20 - human review de regiones Petri

Objetivo: registrar revision humana de las `PetriSegmentationRegion`
candidatas (Fase 19) antes de usarlas para entrenar un futuro detector de
objetos (YOLO) o un modelo de segmentacion supervisada.

**Entidad.** `PetriRegionReview` (`domain/entities/petri_region_review.py`)
referencia `petri_segmentation_region_id`, `petri_segmentation_run_id`,
`dataset_release_id`, `dataset_item_id`, `dataset_split_item_id`,
`decision` (`PetriRegionReviewDecision`), `reviewer_id`/`reviewer_name`
opcionales, `confidence_score` opcional (valida `[0,1]` reutilizando el value
object `ConfidenceScore`), `is_final` (default `True`),
`corrected_bbox_x/y/width/height` opcionales (`width`/`height` deben ser
positivos si se proveen) y `corrected_notes`/`review_notes`. Nunca modifica
`PetriSegmentationRegion`: una correccion de bounding box vive solo en la
revision.

**Enum.** `PetriRegionReviewDecision` (`domain/enums/petri_region_review_decision.py`)
define exactamente `candidate_valid`, `candidate_false_positive`,
`candidate_uncertain`, `needs_resegmentation`. Ninguno implica taxonomia ni
diagnostico confirmado.

**Persistencia.** Migracion `0013_petri_region_reviews.py` crea
`petri_region_reviews` con FKs a `petri_segmentation_regions`,
`petri_segmentation_runs`, `dataset_releases`, `dataset_items` y
`dataset_split_items`; `CHECK` sobre `decision`, `confidence_score` (`[0,1]`)
y `corrected_bbox_width`/`corrected_bbox_height` (`> 0` si no son `NULL`); e
indice unico parcial `uq_petri_region_reviews_one_final_per_region` sobre
`petri_segmentation_region_id` donde `is_final = true` (mismo patron
cross-dialecto que `uq_human_reviews_one_final_per_run`, Fase 2.5).

**Puerto y repositorio.** `PetriRegionReviewRepositoryPort` expone `add`,
`get_by_id`, `list_by_region_id`, `list_by_segmentation_run_id`,
`list_by_dataset_release_id`, `get_final_by_region_id` y
`unset_final_for_region` — sin logica de decision. `PetriSegmentationRegionRepositoryPort`
se extendio con `get_by_id` (ausente hasta esta fase), necesario para que el
caso de uso valide la region antes de crear la revision.

**Caso de uso.** `SubmitPetriRegionReviewUseCase` busca la
`PetriSegmentationRegion` (404 `petri_segmentation_region_not_found` si no
existe), construye el `PetriRegionReview` (las validaciones de
`confidence_score`/bbox viven en el `__post_init__` de la entidad) y, dentro
de un unico `UnitOfWork`, si `is_final=True` despromueve la revision final
anterior de la region (`unset_final_for_region`) antes de insertar la nueva
— mismo patron "demote-then-add" que `SubmitHumanReviewUseCase` (Fase 5).
Nunca modifica `PetriSegmentationRegion`, `PetriSegmentationRun` ni
`DatasetRelease`.

**Consultas.** `GetPetriRegionReviewUseCase` (por id),
`GetFinalPetriRegionReviewUseCase` (revision final vigente de una region) y
`ListPetriRegionReviewsUseCase` (`by_region`/`by_segmentation_run`/`by_dataset_release`,
cada uno validando la existencia del recurso padre antes de listar).

**Manifest de anotaciones revisadas.** `PetriReviewedAnnotationManifestExporter`
(`application/services/petri_reviewed_annotation_manifest_exporter.py`)
exporta, para un `PetriSegmentationRun`, un JSON determinista (orden por
`petri_image_path`, `region_index`, id de revision) con `total_regions`,
`reviewed_regions`, `final_reviewed_regions`, `decision_distribution` y una
lista `annotations` — cada una con `original_bbox`, `corrected_bbox`
opcional y `effective_bbox` (la corregida si existe, si no la original).
Solo incluye revisiones finales por defecto; `include_non_final=true` agrega
las historicas. No genera formato YOLO ni archivos de labels — eso queda
fuera de alcance hasta una fase futura explicita. No incluye imagenes,
mascaras ni taxonomia.

**API.**

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/v1/ml/petri-regions/{region_id}/reviews` | Registra una revision humana de una region candidata |
| GET | `/api/v1/ml/petri-regions/{region_id}/reviews` | Historial de revisiones de una region |
| GET | `/api/v1/ml/petri-regions/{region_id}/reviews/final` | Revision final vigente de una region |
| GET | `/api/v1/ml/petri-segmentations/{segmentation_run_id}/region-reviews` | Revisiones por run de segmentacion |
| GET | `/api/v1/datasets/releases/{dataset_release_id}/petri-region-reviews` | Revisiones por DatasetRelease |
| GET | `/api/v1/ml/petri-segmentations/{segmentation_run_id}/reviewed-annotations-manifest` | Exporta el manifest de anotaciones revisadas |

**Limites.** `candidate_valid` no implica colonia confirmada ni
identificacion microbiologica. Fase 20 no entrena modelos, no usa
PyTorch/TensorFlow/YOLO/CNN/ViT/deep learning, no descarga datasets
externos, no agrega frontend/autenticacion/taxonomia, no usa Celery y no
reemplaza `MockInferenceEngine`.
## 37. Fase 21 - exportacion supervisada de anotaciones Petri

Objetivo: convertir `PetriRegionReview` finales sobre
`PetriSegmentationRegion` en formatos de anotacion supervisada para
entrenamiento futuro, sin entrenar modelos y sin copiar imagenes por defecto.

**Entidades.** `PetriAnnotationExportRun` representa una exportacion
persistida para un `DatasetRelease` + `PetriSegmentationRun`: formato
(`blueberry_manifest`, `coco_json`, `yolo_txt`), status (`completed`,
`partial`, `failed`), config, conteos, `output_manifest`, `summary`,
`created_by`/`notes` y `error_message`. `PetriAnnotationExportItem`
representa una anotacion exportada: referencia el run de exportacion, la
revision humana final, la region original, dataset item/split item, split,
ruta Petri, label generico, bbox, fuente de bbox (`corrected` u `original`)
y payload JSON. No guarda imagenes, mascaras ni taxonomia.

**Config y politicas.** `PetriAnnotationExportConfig` permite elegir formato
y filtro de decisiones. Por defecto `decision_filter=valid_only`, por lo que
solo `candidate_valid` se exporta como objeto positivo. `candidate_false_positive`,
`candidate_uncertain` y `needs_resegmentation` no son positivos entrenables
por defecto. Si existe bbox corregido y `include_corrected_bbox=true`, tiene
prioridad; si no, se usa el bbox original de segmentacion. `category_name`
permanece generico (`candidate_region`) y rechaza terminos taxonomicos o
diagnosticos.

**Exporter.** `PetriAnnotationExporter` es un servicio puro de aplicacion:
recibe un `PetriSegmentationRun`, regiones, reviews y config; ordena de forma
determinista; genera `output_manifest`; y construye `PetriAnnotationExportItem`.
No escribe archivos, no modifica imagenes, no crea mascaras y no lanza
Celery. El formato `yolo_txt` produce lineas de label en JSON con class id 0
y coordenadas normalizadas; requiere dimensiones de imagen y falla de forma
controlada si no puede obtenerlas. Esto no es un modelo YOLO.

**Persistencia.** Alembic `0014_petri_annotation_exports.py` crea
`petri_annotation_export_runs` y `petri_annotation_export_items`, con FKs a
`dataset_releases`, `petri_segmentation_runs`, `petri_region_reviews`,
`petri_segmentation_regions`, `dataset_items` y `dataset_split_items`; CHECKs
para formato/status/bbox_source/dimensiones; unique
`export_run_id + petri_region_review_id`; y JSONB para config, manifest,
summary y payloads.

**API.**

| Metodo | Ruta | Uso |
| --- | --- | --- |
| POST | `/api/v1/ml/petri-annotation-exports` | Crea una exportacion supervisada |
| GET | `/api/v1/ml/petri-annotation-exports` | Lista exportaciones |
| GET | `/api/v1/ml/petri-annotation-exports/{export_run_id}` | Detalle del run |
| GET | `/api/v1/ml/petri-annotation-exports/{export_run_id}/items` | Items exportados |
| GET | `/api/v1/ml/petri-annotation-exports/{export_run_id}/manifest` | Manifest JSON completo |
| GET | `/api/v1/datasets/releases/{dataset_release_id}/petri-annotation-exports` | Exportaciones por release |
| GET | `/api/v1/ml/petri-segmentations/{petri_segmentation_run_id}/annotation-exports` | Exportaciones por segmentacion |

Fase 21 no implementa YOLO como modelo, no entrena YOLO, no usa PyTorch,
TensorFlow, CNN, ViT ni deep learning, no descarga datasets externos, no
agrega frontend/autenticacion/taxonomia y no reemplaza `MockInferenceEngine`.
