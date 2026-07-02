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
│   │   ├── tasks/                  # Celery tasks (fase futura, todavía vacío/sin consumidor)
│   │   ├── config/                 # Settings (pydantic-settings): DATABASE_URL, MAX_UPLOAD_SIZE_MB, LOG_LEVEL/LOG_FORMAT...
│   │   └── logging/                 # configure_logging, RequestLoggingMiddleware, formatters (Fase 3.5)
│   │
│   ├── ml/
│   │   ├── preprocessing/          # Normalización, resize, denoise (caja Petri y microscopía) — todavía vacío
│   │   ├── petri_branch/            # Extracción de features de la imagen de caja Petri — todavía vacío
│   │   ├── micro_branch/            # Extracción de features de la imagen microscópica — todavía vacío
│   │   ├── fusion/                   # Fusión tardía de features macro+micro — todavía vacío
│   │   ├── inference_engine/          # MockInferenceEngine (Fase 4) — implementación del InferenceEnginePort
│   │   └── model_registry/             # Metadata/versionado de modelos — todavía vacío
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
├── docker-compose.yml       # PostgreSQL + Redis (Redis reservado, sin uso todavía)
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

**Los pasos 1–6 ya están expuestos por HTTP** (Fase 3 para 1–4, Fase 4 para 5, Fase 5 para 6 — ver § 14, § 16 y § 18). El paso 5 corre hoy de forma **síncrona** dentro del propio request HTTP (`POST /analysis-runs/{id}/process`), sin preprocesamiento real de imágenes ni fusión de features — el motor es una simulación determinista (ver § 16). Celery y la ejecución asíncrona quedan para cuando exista un motor real cuyo costo de cómputo lo justifique. La revisión humana no sobrescribe la `Prediction`: agrega registros `HumanReview` auditables y marca una revisión final vigente.

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

## 8. Procesamiento asíncrono (futuro)

- Redis está provisionado por `docker-compose.yml`, pero ningún código lo consume todavía.
- Celery, tareas como `run_inference_task(...)`, preprocesamiento pesado o reentrenamiento quedan fuera del alcance actual.
- La API no encola jobs: `POST /api/v1/analysis-runs/{id}/process` sigue siendo síncrono.

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
- `POST /api/v1/analysis-runs` únicamente registra una solicitud de análisis en estado `pending` — no ejecuta nada. Desde la Fase 4, `POST /api/v1/analysis-runs/{id}/process` sí ejecuta un motor de inferencia y crea una `Prediction`, pero ese motor es **exclusivamente `MockInferenceEngine`**: una simulación determinista que nunca abre ni analiza el contenido real de las imágenes, no usa PyTorch/OpenCV/Cellpose, y no tiene validez diagnóstica — ver § 16. Sigue sin encolarse nada a Celery (el procesamiento es síncrono, dentro del propio request HTTP).

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

**Marcador `postgres` y gating por entorno.** Se registró el marcador `postgres` en `pyproject.toml`. Los tests bajo `tests/integration/postgres/` llevan `pytestmark = pytest.mark.postgres` y dependen de fixtures que hacen `pytest.skip` salvo que la **variable de entorno** `DATABASE_URL` esté puesta y empiece por `postgresql`. El gate lee `os.environ` directamente, **no** `Settings` (cuyo default ya es una URL PostgreSQL aunque no haya nada configurado) — así la condición es "¿alguien proporcionó explícitamente una base PostgreSQL?", no "¿el default parece PostgreSQL?". Consecuencia: en local sin PostgreSQL, `pytest -v` reporta 188 passed, 12 skipped (nunca falla por no tener base); cuando el job de CI se ejecute en GitHub Actions, corren de verdad. En ningún caso se usa SQLite como sustituto de estos tests.

**Fixtures (`tests/integration/postgres/conftest.py`).** `migrated_engine` (scope de sesión) fija `os.environ["DATABASE_URL"]` y aplica las **migraciones Alembic reales** vía la API de Alembic (`command.downgrade(base)` → `command.upgrade(head)`) — es decir, un run verde prueba que las migraciones son válidas en PostgreSQL, no solo que `create_all` funcionaría. `pg_session` (scope de función) entrega una sesión y hace `TRUNCATE ... RESTART IDENTITY CASCADE` de las siete tablas tras cada test (con `rollback()` previo, para que un test que disparó un error de constraint —dejando su transacción abortada— no rompa el truncado).

**Tests PostgreSQL (12, `tests/integration/postgres/`).** `test_schema.py`: las siete tablas existen tras migrar; `class_probabilities` es `JSONB` real (round-trip de dict, operador `->>`, y `information_schema` reporta `jsonb`); los `ENUM` guardan el **valor** (`mock`, `pending`) y no el nombre del miembro Python; las columnas `UUID` devuelven `uuid.UUID` reales. `test_constraints.py`: el índice único parcial permite una sola review `is_final = true` por run pero múltiples históricas; el `CHECK` de `confidence_score` rechaza fuera de `[0,1]` y acepta `NULL`/en rango; el `CHECK` de `corrected_label` obliga a que exista cuando la decisión es `corrected`. Estos tests construyen filas vía los **modelos ORM** (no las entidades de dominio) a propósito, para probar que es la **base de datos** —y no la validación de la entidad— la que rechaza. `test_api_postgres_smoke.py`: flujo API completo con `TestClient` apuntando al PostgreSQL migrado y storage temporal — muestra → imágenes (generadas con Pillow) → AnalysisRun → procesamiento mock → Prediction → revisión humana final → consulta de la final. Solo motor mock, sin IA ni datasets.

**`scripts/check_postgres_migrations.py` reforzado (Tarea 3).** Ahora prefiere `DATABASE_URL` de entorno e imprime explícitamente qué fuente usa (`[0/4]`); si no está seteada, cae al default de `Settings` pero lo avisa de forma prominente (en CI debe estar seteada). Tras resolver la URL, la re-exporta a `os.environ["DATABASE_URL"]` antes de invocar `alembic`, garantizando que el subproceso de Alembic apunte exactamente a la misma base cuya conexión se acaba de verificar (evita el desajuste con el placeholder de `alembic.ini` en la ruta de fallback). Mantiene: rechazo si la URL no es PostgreSQL, `SELECT 1` con `connect_timeout` corto, `upgrade head`, `current`, y roundtrip `downgrade base`/`upgrade head` (salvo `--skip-roundtrip`); nunca imprime "SUCCESS" si algún paso falló.

**`alembic/env.py` revisado (Tarea 7), sin cambios.** Ya lee `DATABASE_URL` de entorno y sobrescribe `sqlalchemy.url`; no tiene default a SQLite; usa una ruta relativa calculada (`parents[1]/src`), no absoluta; no requiere un `.env` real; no imprime secretos. Correcto tal cual para CI y local.

**Estado real de PostgreSQL en este entorno.** Igual que en la Fase 5.5: esta máquina/sesión no tiene Docker (`docker: command not found`), así que los 12 tests PostgreSQL **no** se ejecutaron localmente — se reportan como `skipped` en local. Su validación real debe ocurrir en GitHub Actions, pero en Fase 6.5 todavía no se observó ningún run porque el repositorio local no tiene remoto GitHub configurado. No se finge que pasaron localmente ni en CI.

**Riesgos pendientes antes de Fase 7.** (a) La validación PostgreSQL depende de que el job de CI corra en GitHub Actions; en este entorno local sigue sin Docker y en Fase 6.5 no hay remoto GitHub, así que no hay confirmación local ni de CI. (b) El job de CI usa `postgres:16` con credenciales de prueba; una futura fase que despliegue necesitará validar también contra la versión/configuración exacta de PostgreSQL de producción. (c) Sigue sin haber Celery, IA real ni frontend — fuera de alcance por diseño hasta que se aprueben.

## 21. Fase 6.5 — verificación real del workflow CI PostgreSQL (Estado B)

Objetivo: confirmar si el workflow de GitHub Actions realmente se ejecuta y pasa. No se implementó funcionalidad nueva: sin Celery, sin IA real, sin PyTorch, sin entrenamiento, sin datasets, sin frontend, sin autenticación y sin taxonomía microbiológica.

**Estado Git observado el 2026-07-02.** Rama actual: `main`. Último commit antes de documentar esta fase: `7535d6a Add PostgreSQL validation workflow`. `git status --short` no mostró archivos modificados al inicio de la verificación (solo warnings del sandbox por `safe.directory`/ignore global inaccesible). `git log --oneline -5` mostró `7535d6a` seguido de `b098eb6 Initial BlueberryMicroID MVP backend`.

**Remoto GitHub.** `git remote -v` no devolvió ningún remoto configurado. Por eso no se ejecutó `git push origin main`: no existe `origin`, no hay URL de GitHub que confirmar y no se debe inventar un remoto ni crear un repositorio externo sin autorización explícita.

**Estado del workflow.** Estado B: `.github/workflows/tests.yml` existe y define los jobs `unit-and-api-tests` y `postgres-migrations`, pero no se observó ningún run real de GitHub Actions. PostgreSQL **no** queda validado en CI hasta que un run real termine exitosamente.

**Pasos manuales para completar la verificación.**

```bash
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

Después, abrir el repositorio en GitHub, entrar a **Actions**, seleccionar `.github/workflows/tests.yml`, y confirmar que pasen ambos jobs: `unit-and-api-tests` y `postgres-migrations`. Si falla alguno, registrar aquí el run id o URL y el resumen del error antes de avanzar a Fase 7. Si pasan ambos, actualizar esta sección a Estado A con fecha, hash y run id/URL.
