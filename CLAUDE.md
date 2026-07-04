# CLAUDE.md — Reglas de desarrollo para BlueberryMicroID

Este archivo define cómo debe comportarse cualquier sesión de desarrollo (humana o asistida por IA) sobre este repositorio. Es de lectura obligatoria antes de escribir código.

## 1. Qué es este proyecto (y qué NO es)

**BlueberryMicroID** es una **plataforma de apoyo al reconocimiento preliminar** de microorganismos asociados a **arándanos** (blueberry), mediante visión artificial multimodal que combina dos fuentes de imagen por muestra:

1. **Imagen de caja Petri** (referida en el código como "imagen macro" solo por su escala relativa a la microscópica): fotografía de la caja Petri donde se observa el crecimiento/colonia obtenida en laboratorio.
2. **Imagen microscópica**: fotografía obtenida por microscopio a partir de la muestra tomada de esa misma caja Petri.

**No es** un sistema de diagnóstico microbiológico definitivo. **No es** un identificador taxonómico (especie/género) validado clínicamente. **No** reemplaza el criterio de un experto en microbiología. Cualquier código, texto de UI, documentación o commit que sugiera lo contrario debe corregirse antes de fusionarse.

Reglas de alcance explícitas y no negociables:

- **La imagen "macro" es siempre y únicamente una fotografía de la caja Petri con el crecimiento del microorganismo.** Nunca es una fotografía del fruto (arándano) en sí, ni de su superficie, color o estado externo.
- **El sistema NO analiza la apariencia externa del arándano** (no hay clasificación de calidad de fruta, madurez, daño físico, etc. en este proyecto). Cualquier funcionalidad de ese tipo está fuera de alcance salvo que el usuario lo solicite explícitamente como un proyecto distinto.
- El producto inicial y único soportado es **arándano (blueberry)**. No generalizar a "cualquier fruta" sin instrucción explícita.
- La inferencia multimodal se basa exclusivamente en **imagen de caja Petri + imagen microscópica** de una misma muestra. Ninguna otra fuente de imagen es válida en el MVP.
- No confundir estos conceptos en nombres de variables, endpoints, tablas ni documentación.

## 2. Arquitectura obligatoria

El proyecto sigue Clean Architecture con 5 capas, ubicadas en `src/blueberry_microid/`:

| Capa | Carpeta | Puede importar de |
|---|---|---|
| domain | `domain/` | nada (capa más interna, sin dependencias externas) |
| application | `application/` | `domain/` únicamente |
| ml | `ml/` | `domain/` (entidades/value objects), nunca al revés |
| infrastructure | `infrastructure/` | `domain/`, `application/` (implementa sus puertos) |
| interfaces/api | `interfaces/` | `application/` (casos de uso), nunca directo a `infrastructure/` o `ml/` salvo vía inyección de dependencias |

Reglas duras:

- `domain/` no importa SQLAlchemy, FastAPI, PyTorch, OpenCV ni ninguna librería de infraestructura o ML. Son entidades y reglas de negocio puras (dataclasses/Pydantic simples, enums, excepciones de dominio).
- `application/` define **puertos** (interfaces abstractas, ej. `SampleRepository`, `InferenceEngine`, `ImageStorage`) en `application/ports/` y los **casos de uso** que los consumen. Nunca conoce implementaciones concretas.
- `infrastructure/` implementa esos puertos (repositorios SQLAlchemy, storage en disco/S3, config; desde Fase 7 también Celery para ejecutar el motor mock de forma asíncrona).
- `ml/` implementa el puerto `InferenceEngine` (u otros puertos de ML) pero vive separado de `infrastructure/` porque tiene un ciclo de vida distinto (modelos, pesos, versionado).
- `interfaces/api/` solo orquesta: recibe HTTP, valida con Pydantic, llama a un caso de uso de `application/`, devuelve respuesta. Cero lógica de negocio aquí.
- Nunca mezclar en un mismo archivo: endpoint + lógica de negocio + acceso a datos + inferencia. Si un archivo empieza a hacer más de una de estas cosas, se separa.
- `interfaces/api/v1/dependencies.py` es el **único** módulo permitido para construir repositorios SQLAlchemy, `LocalImageStorage` o `PillowImageValidator` e inyectarlos en un caso de uso. Los routers importan de ahí funciones `get_*_use_case`, nunca una clase de infraestructura directamente.

## 3. Separación macro / micro (no negociable)

El sistema es multimodal por diseño. En todo el código, nombres, tablas y endpoints:

- Usar `petri_image` / `PetriImage` para la imagen de caja Petri (imagen macro). En `ml/` la rama correspondiente se llama `petri_branch/`, **nunca** `macro_branch/` — ese nombre induce a pensar erróneamente en una foto del fruto.
- Usar `micro_image` / `MicroImage` (o `microscopy_image`) para la imagen microscópica. En `ml/` la rama correspondiente es `micro_branch/`.
- Nunca un tipo/entidad genérico llamado `Image` sin calificar de cuál de las dos se trata, salvo en una interfaz común muy explícita (ej. `SampleImage` abstracto del que heredan ambas).
- Toda muestra (`Sample`) debe poder rastrear su relación 1—N con `PetriImage` y `MicroImage`. No se permite un resultado de inferencia sin trazabilidad a las imágenes de origen ni sin saber exactamente qué `PetriImage` y qué `MicroImage` se usaron (ver `AnalysisRun`).
- **Transiciones de estado de `AnalysisRun` viven en la entidad, no en el caso de uso ni en el repositorio.** `mark_processing()`/`mark_completed()`/`mark_needs_review()`/`mark_failed(msg)` validan su propio origen permitido (`pending`→`processing`→estado final) y lanzan `InvalidAnalysisRunTransitionError` si no corresponde — esto es lo que hace imposible reprocesar un `AnalysisRun` ya terminado desde cualquier punto de entrada. Nunca dupliques esa validación de estado en un caso de uso; solo llama al método de la entidad y deja que lance si corresponde.
- **La transición `pending → processing` real (con garantía de concurrencia) no la hace `mark_processing()`.** Desde la Fase 4.5, `ProcessAnalysisRunUseCase` usa `AnalysisRunRepositoryPort.claim_for_processing(analysis_run_id)` — una única sentencia `UPDATE ... WHERE status = 'pending'` verificada por `rowcount` — porque un chequeo en memoria (`mark_processing()`) no puede impedir que dos llamadas concurrentes, cada una con su propia copia del `AnalysisRun`, pasen la validación al mismo tiempo. `mark_processing()` se conserva en la entidad como documentación/prueba de la regla de negocio en aislamiento, pero **ningún caso de uso nuevo debe depender de ella para garantizar exclusividad** — esa garantía solo puede darla una operación atómica de base de datos. Ver ARCHITECTURE.md §17.

## 4. Reglas sobre IA y modelos

- Desde la Fase 4 existe `InferenceEnginePort` (`application/ports/inference_engine.py`) y una única implementación, `MockInferenceEngine` (`ml/inference_engine/mock_inference_engine.py`): determinista (hash de `analysis_run.id`, sin aleatoriedad), **no lee ni decodifica bytes de imagen** (no abre `file_path`, no usa Pillow/OpenCV/Cellpose/PyTorch), y sus `confidence_score` nunca superan ~0.75. Cualquier motor nuevo (real o de terceros) debe implementar el mismo puerto, sin tocar `application/` ni `interfaces/` — el único punto que elige el motor es `interfaces/api/v1/dependencies.py::get_inference_engine()`.
- Todo resultado de inferencia debe registrar: modelo usado, versión del modelo (`ModelVersion` vía `AnalysisRun.model_version_id`), timestamp, nivel de confianza (si aplica). Nunca omitir esta trazabilidad "para simplificar".
- **Prohibido inventar métricas.** No escribir accuracy, precision, recall, F1 ni ninguna métrica de modelo que no provenga de una evaluación real documentada. Si no existe evaluación, el campo correspondiente debe quedar `null`/ausente, no un número de relleno.
- **Prohibido inventar taxonomía.** No generar nombres de especie/género de hongos o bacterias como si el sistema los hubiera identificado, y no afirmar identificación taxonómica exacta sin dataset, protocolo y validación de expertos. Las clases del MVP (`no_evident_growth`, `suspicious_growth`, `probable_fungal_growth`, `probable_bacterial_growth`, `inconclusive`) son categorías visuales amplias, no diagnósticos ni taxones. `MockInferenceEngine` nunca debe extenderse con nombres de especie/género, ni siquiera como "ejemplo" o "placeholder".
- Todo modelo debe ser versionado explícitamente (campo `model_version` o tabla `ModelVersion`). No se sobrescribe un modelo "en caliente" sin nueva versión.
- **Un procesamiento fallido en `/process` no devuelve 200 OK.** `ProcessAnalysisRunUseCase` envuelve en un único `try/except` todo lo que ocurre después de `claim_for_processing()` (la llamada al motor, la construcción de `Prediction`, la transacción final) y, ante cualquier excepción, primero marca el `AnalysisRun` como `failed` con `error_message` controlado en su propia transacción. Si la recuperación tiene éxito, levanta `AnalysisProcessingError` (→ 500 `analysis_processing_failed`, mensaje seguro, detalle técnico solo en logs). Si ocurre `DuplicatePredictionError`, también marca `failed` y relanza 409 `duplicate_prediction`, sin crear una segunda `Prediction`. **`processing` nunca debe quedar como estado permanente**: si hasta el intento de marcar `failed` fallara (el único escenario que de verdad no se puede autorreparar), se registra en `CRITICAL` con el error original preservado y se lanza `AnalysisRunFinalizationError` (→ 500 controlado, sin traza cruda al cliente) — ver ARCHITECTURE.md §17.

## 5. Revisión humana

- Desde la Fase 5, una predicción procesada puede recibir revisiones humanas por API: confirmar, corregir a una de las cinco etiquetas visuales permitidas, marcar como no concluyente o rechazar la muestra como inválida. No existe estado `pending_review` separado para `Prediction`: el estado operativo vive en `AnalysisRun` (`completed` o `needs_review`) y la auditoría vive en `HumanReview`.
- El resultado final que se considera "de referencia" para curación de dataset o reentrenamientos futuros es la revisión humana final, no la predicción cruda del modelo. Esto no implica que ya exista dataset, entrenamiento ni métricas.
- No se debe eliminar ni sobrescribir la predicción original al aplicar una corrección humana: ambas coexisten (auditoría). `SubmitHumanReviewUseCase` nunca muta `Prediction`.
- `HumanReview.is_final` marca cuál de las (potencialmente varias) revisiones de un `AnalysisRun` es la vigente; el resto son históricas. Como mucho una puede tener `is_final=True` por `AnalysisRun` — invariante aplicado a nivel de base de datos con un índice único parcial (`uq_human_reviews_one_final_per_run`), no solo en la entidad. `SubmitHumanReviewUseCase` despromueve cualquier revisión final anterior y añade la nueva final dentro de un único `UnitOfWork`; si la inserción falla, el rollback conserva la final anterior.

## 5.1. Dataset curado (Fase 8)

- `DatasetSnapshot` congela una versión de dataset para entrenamiento futuro; `DatasetItem` conserva referencias a `AnalysisRun`, `Sample`, `PetriImage`, `MicroImage`, `Prediction` y `HumanReview` final. No se copian imágenes ni se modifican datos originales.
- Un item entrenable requiere una revisión humana final. `Prediction` por sí sola nunca es ground truth, aunque el motor mock haya producido una etiqueta.
- Derivación permitida: `confirmed` usa `Prediction.predicted_label` porque el experto la aceptó; `corrected` usa `HumanReview.corrected_label`; `marked_inconclusive` solo entra si se solicita explícitamente; `rejected_invalid_sample` no entra como dato entrenable.
- El manifest de dataset contiene rutas y metadata básica, nunca bytes de imagen, secretos, métricas de modelo, especies, géneros ni taxonomía.
- Esta capa prepara datos trazables. No entrena modelos, no calcula accuracy/precision/recall/F1, no descarga datasets externos y no reemplaza `MockInferenceEngine`.

## 5.2. Dataset release y particiones train/validation/test (Fase 9)

- `DatasetRelease` congela una partición reproducible (train/validation/test) de un `DatasetSnapshot` ya existente; `DatasetSplitItem` registra el split de cada `DatasetItem` dentro de esa release. Ninguno de los dos modifica ni copia el `DatasetSnapshot`/`DatasetItem` original — solo los leen.
- **La partición es siempre a nivel de `Sample` (`sample_id`), nunca a nivel de `DatasetItem`/imagen individual.** Todo `DatasetItem` que comparta `sample_id` con otro debe terminar en el mismo split — esto es lo que previene la fuga de datos entre particiones. `DatasetSplitter` (`application/services/dataset_splitter.py`) es el único lugar autorizado para implementar esta regla; no dupliques la lógica de agrupación en un caso de uso o en un repositorio.
- **Riesgo de fuga por `lot_code`/`origin`: parcialmente mitigado desde la Fase 10, no eliminado.** La partición por `sample_id` sigue siendo el comportamiento por defecto (`by_sample`) y ya no es la única opción — ver §5.3 para `by_lot`/`by_origin_lot`. Ninguna de las tres estrategias elimina la fuga por completo (ej. confusión por fecha de procesamiento o técnico compartido sigue sin modelarse).
- **Determinismo obligatorio.** Dado el mismo `random_seed` y las mismas ratios, `DatasetSplitter` debe producir siempre la misma partición, sin importar el orden en que lleguen los `DatasetItem`s (nunca confiar en el orden de una consulta SQL). Los conteos de muestras por split (no el contenido) dependen solo de los ratios y el total de muestras, no del seed.
- Los ratios (`train_ratio`/`validation_ratio`/`test_ratio`) deben sumar 1.0 y estar en `[0,1]`; validarlos con `validate_split_ratios()` (dominio, `domain/entities/dataset_release.py`), nunca reimplementar la suma/tolerancia en otro sitio. Ratios inválidos son `InvalidSplitRatiosError` → 422 `invalid_split_ratios`, no un 400 genérico.
- Un dataset sin items incluidos (`included=True`) no puede generar una release: `EmptyDatasetSnapshotError` → 409. Un dataset pequeño (que deja algún split vacío) no debe fallar — debe generar la release igual y registrar un `WARNING` explícito vía `logging`, nunca fallar silenciosamente ni balancear artificialmente para evitar el split vacío.
- No usar `scikit-learn` ni otra dependencia de ML para este split — es aritmética determinista simple (agrupar, ordenar, `random.Random(seed).shuffle`, cortar por ratio). Si en el futuro se justifica una librería, debe declararse en `pyproject.toml` y justificarse en ARCHITECTURE.md, igual que cualquier otra dependencia nueva.
- El manifest de release (`DatasetReleaseManifestExporter`) sigue las mismas reglas que el manifest de snapshot: solo rutas y metadata, nunca binarios, secretos, métricas de modelo ni taxonomía. Añade `split` por item, nada más.
- Esta capa sigue sin entrenar modelos, sin calcular métricas de rendimiento, sin descargar datasets externos y sin reemplazar `MockInferenceEngine`.

## 5.3. Estrategias avanzadas de partición: `by_sample` / `by_lot` / `by_origin_lot` (Fase 10)

- `SplitStrategy` (`domain/enums/split_strategy.py`) define exactamente tres valores: `by_sample` (agrupa por `sample_id`, comportamiento heredado de la Fase 9), `by_lot` (agrupa por `Sample.lot_code`) y `by_origin_lot` (agrupa por la combinación `Sample.origin` + `Sample.lot_code`). `DatasetRelease.split_strategy` almacena uno de estos tres valores; a nivel de base de datos hay un `CHECK` (`ck_dataset_releases_split_strategy`), no un tipo `ENUM` nativo de PostgreSQL — mismo patrón que otros value objects validados en dominio con backstop en base de datos (ej. `confidence_score`).
- **`by_lot` es más estricto que `by_sample`; `by_origin_lot` es más estricto que `by_lot`.** Cada estrategia solo debe usarse cuando existe un riesgo real de que el agrupamiento más fino (`sample_id`) no baste: `by_lot` cuando varias `Sample`s de un mismo lote de producción podrían compartir condiciones de cultivo/captura; `by_origin_lot` cuando además el origen (proveedor/campo) puede introducir su propio sesgo compartido dentro de un lote.
- **Prohibido degradar silenciosamente a una estrategia más débil.** Si se pide `by_lot` y algún `Sample` referenciado por un `DatasetItem` no tiene `lot_code`, o se pide `by_origin_lot` y falta `lot_code` y/o `origin`, el caso de uso debe fallar con `DatasetSplitMetadataError` (`application/exceptions.py`) → 422 `dataset_split_metadata_error`. Nunca excluir el item silenciosamente, nunca caer de vuelta a `by_sample` sin que el llamador lo pida explícitamente — cualquiera de esas dos alternativas ocultaría un riesgo de fuga real en vez de exponerlo. Esta validación vive en `DatasetSplitter`/`_grouping_key()`, no duplicada en el caso de uso.
- **`DatasetItem` no se amplía con `lot_code`/`origin`.** Esos campos siguen viviendo únicamente en `Sample`. `CreateDatasetReleaseUseCase` resuelve la metadata necesaria vía `SampleRepositoryPort` (una consulta por `sample_id` único) solo cuando `split_strategy != by_sample`, y se la pasa a `DatasetSplitter` como un `dict[UUID, SampleSplitMetadata]` separado — nunca amplíes el propio `DatasetItem`/sus DTOs con estos campos para evitar acoplar el modelo de item al de partición.
- El manifest de release (`DatasetReleaseManifestExporter`) incluye `split_strategy`, y por item `sample_id`, `lot_code` y `origin`, para que un auditor pueda confirmar desde el manifest solo qué unidad de agrupamiento (muestra, lote, u origen+lote) respetaron realmente los splits. Sigue sin incluir binarios, secretos, métricas de modelo ni taxonomía.
- Una release existente de la Fase 9 con el valor libre `random_by_sample` se normaliza a `by_sample` en la migración de Alembic que añade el `CHECK` (Fase 10) — nunca se pierde ni se reinterpreta como otra estrategia.

## 5.4. Contratos ML previos a entrenamiento (Fase 11)

- `ml/contracts/`, `ml/configs/`, `ml/validation/`, `ml/data/`, `ml/training/` y `ml/reports/` existen para validar manifests de entrenamiento futuro, no para entrenar modelos. No agregues PyTorch, tensores, augmentations, dataloaders de imágenes reales ni loops de entrenamiento dentro de esta fase.
- `TrainingManifest` debe mapear el manifest de `DatasetReleaseManifestExporter`: splits, rutas Petri/micro, ground truth revisado, decisión de revisión, predicción original y metadata de `Sample` (`lot_code`/`origin`). No copies imágenes, no abras bytes de imagen y no exportes secretos.
- `ManifestValidator` es el gate antes de cualquier entrenamiento futuro: debe fallar por splits faltantes/vacíos, paths vacíos, etiquetas fuera de las cinco clases visuales preliminares, duplicados, fuga por `sample_id`, y fuga por lote/origen cuando el manifest declare `by_lot` o `by_origin_lot`. Los mínimos de tamaño son reglas de preparación, no métricas de modelo.
- `ImagePathValidator` solo comprueba existencia de archivos referenciados. No debe decodificar con Pillow/OpenCV ni inferir nada del contenido visual.
- `JsonManifestDatasetLoader` carga JSON y entrega `TrainingManifestItem`s; no debe devolver tensores ni leer imágenes. `TrainerPort.train()` debe seguir lanzando `TrainingNotImplementedError` hasta que una fase futura apruebe entrenamiento real explícitamente.
- El CLI `scripts/validate_training_manifest.py` imprime un reporte JSON y devuelve códigos de salida (`0` válido, `1` inválido, `2` error de carga/config). No debe conectar a FastAPI, PostgreSQL, Redis o Celery.
- Sigue prohibido afirmar taxonomía, especie/género, accuracy, precision, recall, F1 o cualquier resultado experimental que no exista.

## 5.5. ML Preflight Reports persistentes (Fase 12)

- `TrainingPreflightRun` y `TrainingPreflightIssue` persisten resultados de validación de manifests, no experimentos de entrenamiento. No agregues MLflow, TensorBoard, Weights & Biases ni otro tracker externo sin una fase aprobada.
- `CreateTrainingPreflightRunUseCase` debe reutilizar `DatasetReleaseManifestExporter`, `TrainingManifest`, `ManifestValidator` y opcionalmente `ImagePathValidator`. No dupliques reglas de validación en routers, repositorios o modelos SQLAlchemy.
- Status permitido: `failed` si hay errores, `warning` si no hay errores pero sí warnings, `passed` si no hay errores ni warnings. Un manifest inválido también se persiste como run `failed`; no conviertas la validación fallida en rollback salvo que falle la persistencia.
- `validate_image_paths=false` no debe tocar filesystem. `validate_image_paths=true` solo comprueba existencia de rutas; no abre, decodifica, copia ni transforma imágenes.
- Los repositorios de preflight solo persisten/listan. La operación run+issues debe seguir siendo transaccional vía `UnitOfWorkPort`.
- Un preflight `passed` no autoriza entrenamiento ni prueba suficiencia científica. Solo significa que los gates técnicos configurados pasaron.
- Sigue prohibido guardar imágenes, binarios, secretos, métricas de modelo, matriz de confusión, taxonomía, especie/género o cualquier resultado experimental inexistente.

## 6. Estándares de código Python

- Type hints obligatorios en toda función/método público. `mypy`-friendly (evitar `Any` salvo justificación).
- `domain/` y `application/` usan `dataclasses` estándar (entidades, DTOs, requests) — nunca Pydantic, para no acoplar esas capas a una librería de validación web. Pydantic se reserva para `interfaces/api/v1/schemas/` (frontera HTTP).
- Nombres explícitos en inglés para código (`sample`, `petri_image`, `micro_image`, `analysis_run`, `human_review`); comentarios y docs pueden estar en español si el equipo lo prefiere, pero mantener consistencia dentro de un mismo archivo.
- Sin código muerto, sin TODOs sin ticket asociado, sin `print()` (usar logging estructurado).
- Tests con Pytest para cada caso de uso de `application/` (con dobles de prueba en memoria, sin base de datos), pruebas de integración con SQLite para los repositorios en `infrastructure/db/repositories/`, y pruebas de API con `TestClient` en `tests/api/` (SQLite compartida vía `StaticPool` + storage temporal). Los tests de `ml/` deben validar el contrato del puerto, no la "precisión" del stub. `pytest` (sin argumentos) ya apunta a `tests/` vía `testpaths` en `pyproject.toml`.

## 7. Manejo de errores y validación

- Dos familias de excepciones, no una: `domain.exceptions` protege invariantes de entidades (ej. `sample_code` vacío); `application.exceptions` cubre fallos de orquestación que solo existen una vez que hay un repositorio o recurso externo de por medio (`SampleNotFoundError`, `DuplicateSampleCodeError`, `InvalidImageError`, etc.). Los casos de uso lanzan/dejan propagar ambas según corresponda.
- Desde la Fase 3, `interfaces/api/error_handlers.py` traduce ambas familias a `{"error": {"code": ..., "message": ...}}` con el status HTTP correspondiente (ver la tabla completa en ARCHITECTURE.md §14 y las adiciones de Fases 4–5: `InvalidAnalysisRunTransitionError`→409, `DuplicatePredictionError`→409, `PredictionNotFoundError`→404, `AnalysisProcessingError`→500, `AnalysisRunFinalizationError`→500, errores de revisión humana 404/409/422 según corresponda). Los errores de validación básica de Pydantic/FastAPI (campo faltante, enum inválido) siguen usando el formato por defecto de FastAPI (`{"detail": [...]}`) — solo las excepciones de dominio/aplicación usan el formato propio.
- **Gotcha de Starlette a recordar:** registrar un handler para la clase `Exception` a secas lo instala como fallback de `ServerErrorMiddleware`, que responde **y vuelve a lanzar** la excepción (para que `TestClient` la siga mostrando en desarrollo). Si solo registras ahí, tus excepciones propias se propagan como excepción Python en vez de devolver JSON. Hay que registrar también para las superclases concretas que sí quieres que respondan sin relanzar (`ApplicationError`, `DomainError`), y dejar `Exception` únicamente como red de seguridad para bugs no anticipados. En tests de API usar `TestClient(app, raise_server_exceptions=False)`.
- Todo endpoint valida entrada (Pydantic) y maneja errores de forma explícita (excepciones → códigos HTTP en la capa API, nunca al revés). La API nunca duplica una regla de negocio ya aplicada en `application/`: solo traduce entrada/salida e invoca el caso de uso.
- Rutas con un segmento literal y un path param en el mismo prefijo (ej. `/samples/by-code/{sample_code}` vs `/samples/{sample_id}`) deben registrarse con el segmento literal primero — FastAPI resuelve por orden de registro, y si el path param fuera primero, capturaría el segmento literal como su propio valor.
- Toda imagen cargada (Petri o micro) pasa por `ImageValidatorPort` antes de guardarse o persistirse: tamaño > 0, MIME permitido (`image/jpeg`, `image/png`, `image/tiff`), extensión permitida (`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`), decodificable por Pillow sin corrupción, **y** (desde la Fase 3.5) el formato real detectado por Pillow debe coincidir tanto con el MIME declarado como con la extensión — `UploadFile.content_type` y el nombre de archivo son datos que el cliente declara, no una prueba. Si algo de esto falla, se rechaza con `InvalidImageError`; no se intenta "arreglar" la imagen de forma silenciosa.
- **Nunca confiar en un `file_size_bytes` declarado por el llamador.** Todo caso de uso que reciba bytes de imagen debe calcular `len(content)` y usar ese valor como fuente de verdad; si el llamador declaró un tamaño distinto, se rechaza con `InvalidImageError` antes de tocar storage o base de datos (ver `ImageIntakeService`).
- **Límite de subida siempre desde `Settings`, nunca hardcodeado.** `MAX_UPLOAD_SIZE_MB` (default 20) se inyecta en `ImageIntakeService` vía `dependencies.py`; si `len(content)` lo excede, se lanza `ImageTooLargeError` (→ 413) antes de validar formato o tocar storage. Es una excepción distinta de `InvalidImageError` (400) porque el archivo puede ser perfectamente válido, solo que grande.
- `ImageStoragePort` nunca confía en el nombre de archivo original para construir la ruta final (riesgo de colisión/path traversal): el nombre final siempre es un UUID nuevo, conservando solo la extensión si es una de las permitidas.
- **Nunca dejar un archivo huérfano.** Si `ImageStoragePort.save()` tiene éxito pero la persistencia en base de datos falla después, el caso de uso debe llamar a `ImageStoragePort.delete()` (vía `ImageIntakeService.cleanup()`) antes de relanzar el error original. Si el borrado compensatorio también falla, envolver ambos errores en `ImageStorageCompensationError` encadenada (`raise ... from original_error`) — nunca ocultar el error original.
- Cada repositorio SQLAlchemy gestiona su propia transacción (`commit` por llamada) — **salvo** dentro de un `UnitOfWorkPort`, donde los repositorios expuestos por `uow` usan `auto_commit=False` (hacen `flush()`, no `commit()`) para que todas sus escrituras se confirmen juntas con un único `uow.commit()`. Desde la Fase 4, `ProcessAnalysisRunUseCase` agrupa la creación de `Prediction` junto con el cambio de estado final del `AnalysisRun`; desde la Fase 5, `SubmitHumanReviewUseCase` agrupa la despromoción de reviews finales previas y la inserción de la nueva final. Usa este mismo patrón (extender `UnitOfWorkPort` con los repositorios que necesites como atributos, no importar SQLAlchemy en el caso de uso) si un caso de uso futuro necesita escribir más de un agregado de forma atómica.
- **Idempotencia y anti-doble-procesamiento vía reclamo atómico (Fase 4.5).** Cualquier caso de uso que transicione un recurso de un estado inicial a "en proceso" antes de un trabajo potencialmente lento/fallible debe usar una actualización condicional a nivel de base de datos (`UPDATE ... WHERE <condición del estado inicial>`, verificando `rowcount`) en vez de "leer en Python, validar en la entidad, escribir" — ese patrón de lectura-modificación-escritura no impide que dos llamadas concurrentes pasen la validación en memoria al mismo tiempo. Ver `AnalysisRunRepositoryPort.claim_for_processing()` como referencia y ARCHITECTURE.md §17 para el razonamiento completo (por qué la Opción B — actualización condicional — se prefirió sobre el bloqueo pesimista `SELECT ... FOR UPDATE`, que no se comporta igual bajo SQLite).
- Nunca hardcodear rutas absolutas ni credenciales. Toda configuración (`DATABASE_URL`, rutas de storage, `MAX_UPLOAD_SIZE_MB`, `LOG_LEVEL`/`LOG_FORMAT`, etc.) se lee vía `infrastructure/config/settings.py` (`pydantic-settings`), nunca directamente de `os.environ` disperso por el código.
- **Todo request tiene un `request_id`** (de `X-Request-ID` si el cliente lo envía, generado si no), guardado en `request.state.request_id` por `RequestLoggingMiddleware` y estampado en la respuesta (éxito o error) como header `X-Request-ID`. Todo error 5xx se loguea en servidor con traza completa (`exc_info`); el cliente nunca ve esos detalles, solo un `code` y un mensaje genérico. No usar `print()`: usar `logging` (ver `infrastructure/logging/`), nunca un servicio externo.

## 8. Qué evitar en esta etapa

- No añadir frontend ni dashboard.
- No entrenar ni integrar modelos reales de PyTorch, ni añadir OpenCV/Cellpose al motor de inferencia. `MockInferenceEngine` es, y debe seguir siendo hasta que se apruebe explícitamente lo contrario, la única implementación de `InferenceEnginePort` — determinista, sin leer contenido real de imagen.
- Celery ya existe desde Fase 7, pero solo como transporte para ejecutar el mismo `ProcessAnalysisRunUseCase` con `MockInferenceEngine` fuera del request HTTP. No crear un segundo camino de procesamiento, no duplicar reglas, no leer imágenes para diagnóstico y no usar Celery para entrenamiento, IA real o lógica microbiológica nueva. `POST /analysis-runs/{id}/process` sigue existiendo para desarrollo/pruebas; el flujo operativo recomendado es `POST /analysis-runs/{id}/process-async`.
- No añadir autenticación (ni básica ni compleja) hasta que se apruebe explícitamente esa fase.
- No añadir CORS a la API salvo que el usuario lo pida explícitamente como preparación documentada para un frontend futuro — no se agrega "por si acaso".
- No introducir pgvector/búsqueda vectorial hasta que exista una necesidad concreta del MVP.
- No crear abstracciones especulativas ("por si en el futuro soportamos otra fruta") sin que el usuario lo pida explícitamente.
- No añadir dependencias nuevas al stack sin reflejarlas en `pyproject.toml` y justificarlas en `ARCHITECTURE.md`.
- No hacer que un caso de uso en `application/` importe SQLAlchemy, Pillow, FastAPI o cualquier detalle de infraestructura directamente — siempre a través de un puerto inyectado en el constructor. `Depends(...)` no debe aparecer fuera de `interfaces/`.
- No afirmar que una migración de Alembic "fue validada" si solo se ejecutó en modo offline (`--sql`) o contra SQLite. Solo cuenta como validada si `alembic upgrade head` (o `scripts/check_postgres_migrations.py`, que hace exactamente eso más una verificación de reversibilidad) corrió contra una instancia real de PostgreSQL y reportó éxito. Desde la Fase 6 existe el job `postgres-migrations` de GitHub Actions (contra un contenedor `postgres:16`), pero desde Fase 6.5 no debe decirse "validado en CI" hasta observar un run verde real: `main` fue subido al remoto GitHub autorizado, pero esta máquina no tiene `gh` y el API no autenticado de Actions devolvió `404 Not Found`. Si además NO se pudo correr localmente (p. ej. sin Docker en la máquina de desarrollo), decirlo explícitamente y distinguir "workflow creado/subido", "validado en CI" y "validado localmente" — nunca afirmar que los tests PostgreSQL pasaron en local si solo se saltaron.
- **Tests que requieren PostgreSQL real (Fase 6).** Van en `tests/integration/postgres/`, llevan `pytestmark = pytest.mark.postgres` (marcador registrado en `pyproject.toml`), y deben saltarse solo/mediante el gate por la variable de entorno `DATABASE_URL` (leída de `os.environ`, no de `Settings`, porque el default de `Settings` ya es una URL PostgreSQL). Nunca usar SQLite como sustituto ahí — su razón de existir es exactamente lo que SQLite no puede validar (`JSONB`, `ENUM` nativos, índice único parcial, `CHECK`, `UUID`, migraciones reales). Los tests rápidos (SQLite) no deben fallar cuando no hay PostgreSQL local.
- **Celery async (Fase 7/7.5).** La app Celery debe vivir en `infrastructure/tasks/celery_app.py`, leer `Settings`, aceptar solo JSON (no pickle) y usar la cola `analysis`. Las tasks deben vivir cerca de infraestructura, construir dependencias sin FastAPI y llamar casos de uso existentes; `process_analysis_run_task` debe usar `ProcessAnalysisRunUseCase`, `SqlAlchemyUnitOfWork`, repositorios SQLAlchemy reales y `MockInferenceEngine`. Los tests rápidos deben usar eager mode (`CELERY_TASK_ALWAYS_EAGER=true`) y no requerir Redis real; el smoke operativo real debe vivir en `scripts/celery_smoke_test.py` y usar Redis + worker reales sin reemplazar la fuente de verdad (`AnalysisRun`/`Prediction`) por el result backend de Celery.
- No instalar/actualizar dependencias del proyecto directamente en un entorno Python global compartido con otras herramientas sin verificar antes si hay conflictos de versiones (ver ARCHITECTURE.md §14, incidente con `starlette`/`sse-starlette`). Preferir un entorno virtual dedicado (`python -m venv .venv`) cuando sea posible.
- No renombrar la carpeta raíz del repositorio (`D:\IndetificadorMicro` → `D:\BlueberryMicroID`) desde dentro de una sesión de Claude Code que la tenga como directorio de trabajo — es una operación insegura para el harness. El renombrado es un paso manual documentado en `docs/development.md` (Prerequisites) y ARCHITECTURE.md §19; el paquete Python (`blueberry_microid`) ya está correctamente nombrado y no depende de esta carpeta.
- El workflow de CI (`.github/workflows/tests.yml`) tiene jobs para `unit-and-api-tests`, `postgres-migrations` y, desde Fase 7.5, `celery-smoke` (PostgreSQL + Redis reales como service containers, worker Celery real, API real y `scripts/celery_smoke_test.py`). No añadir deploy, build de imagen Docker ni secrets a este workflow sin que el usuario lo pida explícitamente; las credenciales de servicios en el YAML son valores desechables de entornos efímeros de CI, no secretos.

## 9. Antes de cada sesión de desarrollo

1. Releer este archivo y `ARCHITECTURE.md`.
2. Verificar en qué fase del MVP se está trabajando (ver `docs/`).
3. Desde la Fase 5.5, el repositorio tiene control de versiones real (`git init` ejecutado, rama por defecto `main`). Ejecutar `git status --short` antes de empezar a modificar código para no confundir cambios propios con trabajo en curso preexistente sin commitear.
4. No avanzar de fase sin validación del usuario si la tarea implica una decisión arquitectónica nueva.
## 10. Majority-class baseline experimental (Fase 13)

- `TrainingRun` y `TrainingPrediction` persisten baselines auditables, no modelos de IA real. `baseline_model_type` permite `majority_class` y, desde Fase 16, `logistic_regression_tabular`; `run_kind` sigue siendo `baseline`.
- El baseline solo puede usar labels revisadas del manifest/release: selecciona la clase mayoritaria del split `train` y predice esa misma etiqueta preliminar para `train`, `validation` y `test`. En empate, el desempate debe ser determinista y documentado.
- Requiere un `TrainingPreflightRun` no fallido y perteneciente al mismo `DatasetRelease`; el manifest se revalida antes de persistir el experimento. Si la revalidacion falla, se persiste un `TrainingRun` con `status=failed` y sin predicciones.
- Las metricas permitidas son solo las derivadas de las `TrainingPrediction` del baseline: accuracy overall, accuracy por split, soporte por split, distribucion de etiquetas por split y matriz de confusion. Sigue prohibido precision, recall y F1.
- Esta es la excepcion estrecha a la regla general de no escribir metricas: las cifras se calculan directamente desde predicciones persistidas y ground truth revisado, nunca son relleno ni afirmacion de IA real.
- No abrir ni decodificar imagenes, no crear tensores, no usar PyTorch/TensorFlow/CNN/ViT/deep learning, no entrenar redes, no descargar datasets externos, no lanzar Celery y no reemplazar `MockInferenceEngine`.
- Los endpoints viven bajo `/api/v1/ml/training-runs` y deben conservar `X-Request-ID`; los endpoints de historial por release/preflight solo listan runs existentes.

## 11. Image Dataset Audit tecnico (Fase 14)

- `ImageDatasetAuditRun` e `ImageDatasetAuditIssue` persisten una auditoria tecnica de los archivos Petri/micro referenciados por un `DatasetRelease` (existencia, legibilidad, formato, dimensiones, modo de color, coherencia de metadata) — no es evaluacion microbiologica ni preflight logico de manifest. `TrainingPreflightRun` (Fase 12) valida la estructura del manifest (splits, labels, fuga por sample/lote); `ImageDatasetAuditRun` valida los archivos de imagen en si. Son capas independientes: un audit de imagenes no requiere un preflight previo, y viceversa.
- `ImageDatasetAuditor` (`ml/validation/image_dataset_auditor.py`) usa Pillow de forma liviana (`Image.open().verify()` para corrupcion, una segunda apertura para formato/dimensiones/modo de color) sobre las rutas del `TrainingManifest` — nunca crea tensores, nunca usa PyTorch/TensorFlow/OpenCV/Cellpose, nunca copia ni modifica los archivos.
- Severidad fija por diseno: `image_empty_path`, `image_missing`, `image_unreadable`, `image_format_mismatch` e `image_size_bytes_mismatch` son `error` (bloquean un audit `passed`); `image_too_small`, `image_too_large`, `image_unsupported_color_mode`, `image_metadata_missing`, `image_dimension_outlier` e `image_duplicate_path` son `warning` (no bloquean). Un audit es `failed` si hay al menos un error, `warning` si no hay errores pero si warnings, `passed` si no hay ninguno — igual que `TrainingPreflightStatus`.
- `TrainingManifestItem` se extendio con `dataset_item_id`, `dataset_split_item_id`, `petri_width/height/file_size_bytes` y `micro_width/height/file_size_bytes` (poblados por `DatasetReleaseManifestExporter` desde `PetriImage`/`MicroImage`) para que `ImageDatasetAuditor` opere solo sobre `TrainingManifest` + `ImageAuditConfig`, sin depender directamente de repos de imagenes ni ampliar `DatasetItem`.
- `ImageAuditConfig` (`ml/configs/image_audit_config.py`) es una configuracion tecnica separada de `TrainingConfig`: umbrales de tamano/dimension/formato/modo de color, nunca hiperparametros de entrenamiento.
- `CreateImageDatasetAuditRunUseCase` reutiliza `DatasetReleaseManifestExporter` (igual que el preflight) y persiste `ImageDatasetAuditRun` + `ImageDatasetAuditIssue` en una unica transaccion via `UnitOfWorkPort`. Nunca modifica `DatasetRelease`, `DatasetItem` ni los archivos de imagen.
- Un audit `passed` certifica solo aptitud tecnica basica de los archivos (se abren, tienen formato/dimension/color razonables) — no es una prueba de calidad cientifica ni de que el dataset sea suficiente para entrenar.
- Los endpoints viven bajo `/api/v1/ml/image-audits` y `/api/v1/datasets/releases/{id}/image-audits`, y deben conservar `X-Request-ID`. Sigue prohibido taxonomia, metricas de modelo, entrenamiento real, PyTorch/TensorFlow y Celery en esta capa.

## 12. Extraccion de features no profunda (Fase 15)

- `ImageFeatureExtractionRun` e `ImageFeatureVector` persisten features tecnicas simples (geometria, intensidad, color, nitidez aproximada, textura, histograma) extraidas de los archivos Petri/micro de un `DatasetRelease` — no es auditoria de archivos (eso es `ImageDatasetAuditRun`, Fase 14) ni preflight de manifest (Fase 12). Son tres capas independientes que se acumulan antes de cualquier entrenamiento real: preflight (estructura del manifest) -> audit (aptitud tecnica de los archivos) -> feature extraction (vectores tecnicos reproducibles).
- `numpy` se agrego como dependencia explicita (`pyproject.toml`) para esta fase: calculos estadisticos simples (media, desviacion estandar, histograma, Laplaciano por diferencias finitas) sobre arrays 2D/3D. No es PyTorch/TensorFlow ni ninguna libreria de deep learning; es aritmetica de arrays, misma categoria que el modulo `statistics` de Python pero vectorizada.
- `ImageFeatureExtractor` (`ml/preprocessing/image_feature_extractor.py`) usa solo Pillow + numpy: `Image.open().verify()` para corrupcion (mismo patron que `PillowImageValidator` e `ImageDatasetAuditor`), luego una reapertura para leer pixeles como array. Nunca usa OpenCV, nunca crea un tensor de entrenamiento, nunca modifica el archivo original. Cada imagen del manifest se intenta siempre — un fallo nunca corta el procesamiento del resto; `fail_on_unreadable_image` solo decide si el estado agregado del run es `failed` (true, por defecto) o `partial` (false) cuando hay errores.
- `TrainingManifestItem` se extendio con `dataset_item_id`/`dataset_split_item_id` ya poblados desde la Fase 14; esta fase no le agrega campos nuevos — reutiliza exactamente el mismo contrato.
- `CreateImageFeatureExtractionRunUseCase` exige un `ImageDatasetAuditRun` que pertenezca al mismo `DatasetRelease` y cuyo status sea aceptable segun `ImageFeatureExtractionConfig.require_audit_passed`/`allow_audit_warning` — un audit `failed` nunca se acepta, sin excepcion, independientemente de la config. No modifica `DatasetRelease`, `DatasetItem` ni `ImageDatasetAuditRun`.
- Un `DatasetItem` genera hasta dos `ImageFeatureVector` (uno por modalidad); el indice unico `(feature_extraction_run_id, dataset_split_item_id, modality)` en base de datos es el que hace cumplir ese "hasta dos, nunca duplicados".
- Las features son solo escalares y un histograma pequeno (N bins configurables, default 16) — nunca arrays de pixeles completos, nunca binarios de imagen.
- Los endpoints viven bajo `/api/v1/ml/image-feature-extractions`, `/api/v1/datasets/releases/{id}/image-feature-extractions` y `/api/v1/ml/image-audits/{id}/feature-extractions`, y deben conservar `X-Request-ID`. Sigue prohibido taxonomia, metricas de clasificacion, entrenamiento real, PyTorch/TensorFlow/deep learning y Celery en esta capa.

## 13. Baseline clasico tabular con features reales (Fase 16)

- `logistic_regression_tabular` es un baseline clasico/tabular sobre `ImageFeatureVector`, no IA profunda. Usa scikit-learn solo para `LogisticRegression`/`StandardScaler`; no agrega PyTorch, TensorFlow, CNN, ViT, tensores de imagen, OpenCV, MLflow, TensorBoard ni W&B.
- `FeatureMatrixBuilder` solo consume `ImageFeatureVector` persistidos y `DatasetSplitItem`. Aplana features numericas JSON de forma deterministica, prefija por modalidad (`petri__...`, `micro__...`), expande histogramas pequenos y respeta estrictamente `train`/`validation`/`test`.
- El `y` del entrenamiento sale solo de `DatasetSplitItem.ground_truth_label`, derivado de revision humana final. Nunca usar `Prediction` como ground truth ni inferir especies/generos.
- `ClassicalTabularBaselineTrainer` ajusta solo con train; validation/test se usan solo para prediccion y metricas. Metricas permitidas: accuracy, soporte, distribuciones de labels y matrices de confusion. Precision, recall y F1 siguen fuera de alcance.
- `CreateClassicalBaselineTrainingRunUseCase` requiere `DatasetRelease`, `TrainingPreflightRun` no fallido y `ImageFeatureExtractionRun` `completed` del mismo release. `partial`/`failed` no entrenan por defecto. Si train tiene una sola clase o faltan features requeridas, persistir fallo controlado o devolver conflicto documentado; nunca entrenar silenciosamente con datos invalidos.
- Persistir en `TrainingRun`/`TrainingPrediction` existentes. No guardar pickle, arrays grandes, imagenes, secretos ni nuevos artefactos binarios.
- Endpoint: `POST /api/v1/ml/training-runs/classical-baseline`; debe conservar `X-Request-ID` y no usar Celery.

## 14. Comparacion de TrainingRuns (Fase 17)

- `TrainingRunComparison` y `TrainingRunComparisonEntry` comparan runs ya
  persistidos; no entrenan, no recalculan predicciones y no abren imagenes.
- Solo se aceptan `TrainingRun` `completed` de la misma `DatasetRelease`, con
  metricas persistidas suficientes (`accuracy_by_split` y `support_by_split`).
- La unica metrica primaria soportada es `accuracy`, sobre split
  `validation` o `test`. No agregar precision, recall, F1 ni metricas nuevas
  sin fase explicita.
- La seleccion de baseline candidato es preliminar y auditable. Empates
  pueden resolverse por simplicidad (`majority_class` antes de
  `logistic_regression_tabular`) si la politica lo pide; `no_auto_selection`
  guarda ranking sin candidato.
- Los endpoints viven bajo `/api/v1/ml/training-run-comparisons` y
  `/api/v1/datasets/releases/{id}/training-run-comparisons`, conservan
  `X-Request-ID`, y no usan Celery.
- Sigue prohibido agregar PyTorch, TensorFlow, CNN, ViT, deep learning, raw
  image tensors, datasets externos, frontend, autenticacion, taxonomia,
  trackers externos o reemplazar `MockInferenceEngine` en esta capa.

## 15. Revision de referencias externas (Fase 18)

- `docs/references/microbiology_cv_landscape.md` es un mapa documental de
  adopcion tecnica para proyectos/datasets externos de vision microbiologica.
  No es codigo productivo, no cambia endpoints y no autoriza integraciones.
- Las referencias externas se tratan como insumos de decision: Petri colony
  detection puede orientar un futuro prototipo clasico; YOLOv5-style detection
  requiere bounding boxes y una fase explicita; MEMTrack requiere video o
  time-lapse; DIBaS/clinical datasets son benchmarks o literatura, no datos
  para mezclar directamente con el dataset propio; CSI-Microbes/SinfNet quedan
  como referencias no resueltas hasta verificar fuente primaria y licencia.
- No copiar codigo externo, no descargar datasets externos, no ejecutar
  notebooks externos, no agregar dependencias, no integrar modelos/pesos y no
  afirmar taxonomia.
- La recomendacion documentada para Fase 19 es un prototipo clasico de
  segmentacion/conteo de colonias en Petri, antes de YOLO/deep learning,
  porque el proyecto aun no tiene anotaciones de objetos ni dataset propio
  suficiente para modelos profundos.

## 16. Segmentacion clasica Petri (Fase 19)

- `ClassicalPetriSegmenter` procesa solo `petri_image_path` de un
  `TrainingManifest`; nunca toca `micro_image_path`.
- OpenCV esta permitido solo como `opencv-python-headless` y solo para vision
  clasica: conversion de color/gris, blur, thresholding, morfologia,
  contornos/componentes, bounding boxes y mediciones geometricas. Prohibido
  OpenCV DNN, YOLO, modelos preentrenados, PyTorch, TensorFlow, CNN, ViT y
  deep learning.
- `PetriSegmentationRun` y `PetriSegmentationRegion` guardan resultados
  tecnicos persistentes. Una "region candidata" no es una colonia confirmada,
  no es una prediccion microbiologica y nunca debe presentarse como
  diagnostico.
- No guardar mascaras ni binarios de imagen en base de datos. No modificar
  imagenes originales. No agregar taxonomia, frontend, autenticacion,
  datasets externos, entrenamiento ni reemplazo de `MockInferenceEngine`.

## 17. Human Review de regiones Petri (Fase 20)

- `PetriRegionReview` registra la revision humana de una `PetriSegmentationRegion`
  candidata detectada por el segmentador clasico (Fase 19). Nunca modifica la
  region original: una correccion de bounding box, si existe, vive solo en la
  fila de la revision (`corrected_bbox_x/y/width/height`), nunca en
  `PetriSegmentationRegionModel`.
- `PetriRegionReviewDecision` define exactamente cuatro valores:
  `candidate_valid`, `candidate_false_positive`, `candidate_uncertain`,
  `needs_resegmentation`. Ninguno de los cuatro es una identificacion
  taxonomica ni una confirmacion de colonia real — `candidate_valid` solo
  significa que la region parece un candidato de anotacion util a futuro.
- **"Revision final vigente"** sigue el mismo patron que `HumanReview` (Fase 5):
  `is_final=True` marca la revision que actualmente aplica para una region; a
  lo sumo una puede ser final por `petri_segmentation_region_id` a la vez,
  aplicado con un indice unico parcial (`uq_petri_region_reviews_one_final_per_region`)
  y por `SubmitPetriRegionReviewUseCase`, que despromueve la final anterior e
  inserta la nueva final en un unico `UnitOfWork`.
- `PetriReviewedAnnotationManifestExporter` exporta un manifest JSON
  determinista de regiones revisadas (solo finales por defecto,
  `include_non_final=True` agrega historicas) con `original_bbox`,
  `corrected_bbox` opcional y `effective_bbox` (la corregida si existe, si no
  la original). No es un formato de exportacion YOLO ni genera archivos de
  labels — eso queda fuera de alcance hasta una fase futura explicita.
- Los endpoints viven bajo `/api/v1/ml/petri-regions/{region_id}/reviews`,
  `/api/v1/ml/petri-segmentations/{segmentation_run_id}/region-reviews`,
  `/api/v1/datasets/releases/{dataset_release_id}/petri-region-reviews` y
  `/api/v1/ml/petri-segmentations/{segmentation_run_id}/reviewed-annotations-manifest`,
  y conservan `X-Request-ID`. Sigue prohibido YOLO, PyTorch, TensorFlow,
  entrenamiento real, datasets externos, taxonomia y reemplazo de
  `MockInferenceEngine` en esta capa.
## 18. Exportacion supervisada de anotaciones Petri (Fase 21)

- `PetriAnnotationExportRun` y `PetriAnnotationExportItem` convierten reviews
  finales de `PetriSegmentationRegion` en formatos de anotacion supervisada:
  `blueberry_manifest`, `coco_json` y `yolo_txt`.
- `yolo_txt` significa solo lineas de label representadas en JSON. No
  implementes ni entrenes YOLO, no agregues pesos, dependencias, detectores,
  pipelines de entrenamiento ni archivos de labels escritos por defecto.
- `PetriAnnotationExporter` debe usar solo reviews finales por defecto y
  exportar solo `candidate_valid` como positivo entrenable por defecto.
  `candidate_false_positive`, `candidate_uncertain` y `needs_resegmentation`
  no son positivos por defecto.
- La categoria debe permanecer generica: `candidate_region`. No usar bacteria,
  fungi, colony, genus, species, diagnostico ni taxonomia como labels.
- El bbox corregido tiene prioridad si existe; si no, se usa el bbox original
  de `PetriSegmentationRegion`. Nunca mutar la region, la review ni las
  imagenes originales.
- No copiar imagenes por defecto, no guardar binarios ni mascaras, no lanzar
  Celery, no entrenar modelos, no usar PyTorch/TensorFlow/CNN/ViT/deep
  learning, no descargar datasets externos, no agregar frontend/autenticacion
  y no reemplazar `MockInferenceEngine`.

## 19. Annotation Export Bundle (Fase 22)

- `AnnotationBundleRun` y `AnnotationBundleFile` empaquetan una
  `PetriAnnotationExportRun` ya persistida en un bundle auditable para uso
  futuro. No crean anotaciones nuevas y no modifican export runs, reviews,
  segmentaciones ni imagenes originales.
- `AnnotationBundleConfig.copy_images` debe seguir rechazado en esta fase.
  El comportamiento por defecto es `dry_run=true`: planificar y persistir los
  archivos esperados sin escribir en disco.
- El writer solo puede generar archivos de texto/JSON/YAML: README,
  `blueberry_manifest.json`, `coco_annotations.json`, labels YOLO `.txt`,
  `dataset.yaml` y `manifest.json`. YOLO significa formato de labels, nunca
  modelo, detector, pesos, entrenamiento ni dependencia.
- El validator revisa geometria de bboxes, splits, formatos derivados,
  existencia opcional de imagenes y terminos prohibidos en label/nombre/
  categoria. Mantener la categoria generica `candidate_region`.
- Endpoints bajo `/api/v1/ml/annotation-bundles`,
  `/api/v1/datasets/releases/{id}/annotation-bundles` y
  `/api/v1/ml/petri-annotation-exports/{id}/annotation-bundles`, con
  `X-Request-ID`.
- Sigue prohibido entrenar modelos, usar PyTorch/TensorFlow/CNN/ViT/deep
  learning, copiar o descargar datasets externos, agregar frontend,
  autenticacion, taxonomia, diagnostico, Celery en este flujo o reemplazar
  `MockInferenceEngine`.

## 20. Supervised Annotation Quality Gate (Fase 23)

- `AnnotationQualityGateRun` valida tecnicamente un `AnnotationBundleRun`
  antes de cualquier entrenamiento futuro. No entrena, no evalua modelos y no
  convierte el bundle en evidencia cientifica definitiva.
- `AnnotationQualityGateIssue` persiste hallazgos con severidad `error` o
  `warning`; errores bloquean el gate, warnings no bloquean. Guardar solo
  metadata y referencias, nunca imagenes ni contenido completo de archivos.
- `AnnotationQualityGateValidator` puede revisar estado del bundle, archivos
  esperados, Blueberry manifest, COCO JSON, labels YOLO como texto,
  `dataset.yaml`, splits, categorias genericas, bboxes, duplicados, soporte
  minimo e imagenes sin anotaciones. No abrir imagenes completas ni modificar
  archivos originales.
- Status: `passed` sin errores ni warnings; `warning` sin errores y con
  warnings; `failed` con errores bloqueantes. `passed` no significa
  diagnostico, taxonomia, validez cientifica ni performance de modelo.
- Endpoints bajo `/api/v1/ml/annotation-quality-gates`,
  `/api/v1/datasets/releases/{id}/annotation-quality-gates` y
  `/api/v1/ml/annotation-bundles/{id}/quality-gates`, con `X-Request-ID`.
- Sigue prohibido YOLO como modelo, entrenar YOLO, PyTorch, TensorFlow, CNN,
  ViT, deep learning, datasets externos, frontend, autenticacion, taxonomia,
  diagnostico, MLflow/TensorBoard/W&B y reemplazar `MockInferenceEngine`.

## 21. Object Detection Training Contract & YOLO Dry-Run (Fase 24)

- `DetectionTrainingRun` es solo un plan persistido de un futuro intento de
  entrenamiento de detector; `status=planned` nunca significa que existe un
  modelo entrenado, pesos reales ni que se ejecuto YOLO. No se entrena
  nada en esta fase.
- `DetectionTrainingIssue` guarda hallazgos de la planificacion (`error`,
  `warning`, `info`) con codigos como `quality_gate_not_passed`,
  `dataset_yaml_missing`, `yolo_labels_missing`, `no_training_executed`,
  `external_weights_requested`. Nunca guarda pesos, imagenes ni labels
  completos.
- `ObjectDetectionTrainerPort.plan_training()` es un contrato de solo
  planificacion: nunca ejecuta subprocess, nunca importa `ultralytics` ni
  `torch`, nunca descarga nada y nunca escribe pesos. `YoloDryRunTrainer` es
  la unica implementacion: valida que `AnnotationBundleRun.status=completed`
  y (si `require_quality_gate_passed=true`) que `AnnotationQualityGateRun.status=passed`,
  valida presencia de `dataset.yaml` y de labels YOLO segun
  `DetectionTrainingConfig`, y genera `command_preview` (un JSON con el
  comando YOLO que se ejecutaria, nunca ejecutado) y `expected_outputs`
  (rutas planeadas de pesos/metricas/predicciones, nunca creadas en disco).
- `CreateDetectionTrainingRunUseCase` exige que el `AnnotationQualityGateRun`
  referenciado pertenezca al `AnnotationBundleRun` referenciado; si no,
  `DetectionTrainingNotAllowedError` (409). Nunca modifica
  `AnnotationBundleRun` ni `AnnotationQualityGateRun`. Persiste
  `status=planned` si todo es valido, `status=blocked` si faltan
  prerequisitos (con issues explicando por que), `status=failed` solo ante
  un error interno de planificacion.
- `DetectionTrainingAlgorithm` solo admite `yolo_dry_run` y
  `DetectionTrainingMode` solo admite `dry_run` en esta fase — no se agregan
  `yolo_train` ni modos reales todavia.
- `allow_external_weights=true` nunca descarga nada: solo registra la
  intencion en `DetectionTrainingConfig` y agrega un warning
  `external_weights_requested`.
- Endpoints bajo `/api/v1/ml/detection-training-runs`,
  `/api/v1/datasets/releases/{id}/detection-training-runs`,
  `/api/v1/ml/annotation-bundles/{id}/detection-training-runs` y
  `/api/v1/ml/annotation-quality-gates/{id}/detection-training-runs`, con
  `X-Request-ID`.
- Sigue prohibido entrenar YOLO, instalar `ultralytics`, importar `torch`,
  PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar pesos
  externos, datasets externos, frontend, autenticacion, taxonomia,
  diagnostico, MLflow/TensorBoard/W&B, GPU obligatoria y reemplazar
  `MockInferenceEngine`.

## 22. Detection Training Readiness Report (Fase 25)

- `DetectionTrainingReadinessReport` evalua si un `DetectionTrainingRun`
  dry-run (Fase 24) esta tecnicamente listo para una futura fase de
  entrenamiento real; nunca entrena nada, nunca ejecuta YOLO y
  `is_ready=true` nunca significa validez cientifica ni modelo entrenado —
  solo que los gates tecnicos configurados pasaron. `DetectionTrainingReadinessIssue`
  guarda hallazgos (`error`/`warning`/`info`) con codigos fijos (p. ej.
  `detection_training_not_planned`, `quality_gate_not_passed`,
  `insufficient_train_images`, `ultralytics_not_installed`,
  `no_training_executed`); nunca guarda imagenes, pesos ni labels completos.
- `DetectionTrainingReadinessDecision` tiene exactamente seis valores
  (`ready_for_training`, `needs_more_annotations`, `blocked_by_quality`,
  `blocked_by_environment`, `blocked_by_contract`,
  `blocked_by_configuration`); `DetectionTrainingReadinessStatus` tiene
  `ready`/`warning`/`blocked`/`failed`. A diferencia de `DetectionTrainingRun`
  (Fase 24), un reporte puede quedar `status=warning` con `is_ready=true`:
  warnings no bloqueantes (p. ej. `copy_images_disabled`,
  `training_executor_missing` cuando no es requerido) no impiden la
  disponibilidad tecnica.
- `DetectionTrainingReadinessEvaluator` (`application/services/`) es puramente
  una inspeccion de metadata ya persistida: nunca importa `ultralytics` ni
  `torch`, nunca llama `subprocess`, nunca consulta GPU real y nunca modifica
  archivos. Para `require_ultralytics_installed`/`require_torch_installed`/
  `require_gpu`, la regla es literal: si el config los exige, el evaluador
  bloquea siempre con `blocked_by_environment` porque no existe forma segura
  de confirmarlos sin instalar/importar esas dependencias — nunca lo intenta.
  Cuando coexisten varias categorias de error bloqueante, la prioridad de
  decision es contrato > calidad > entorno > configuracion > datos.
- `DetectionTrainingReadinessConfig` (`ml/configs/`) trae minimos de datos por
  split (`min_train_images`, etc.) con default `require_minimum_data=true`;
  si no existe `AnnotationQualityGateRun` asociado, el evaluador no puede
  determinar conteos por split y emite un unico issue generico
  (`insufficient_total_images`, severidad `error` si `strict_mode=true` si no
  `warning`) en vez de inventar conteos.
- `CreateDetectionTrainingReadinessReportUseCase` nunca modifica
  `DetectionTrainingRun`, `AnnotationBundleRun` ni `AnnotationQualityGateRun`;
  revalida su existencia, ejecuta el evaluador y persiste reporte + issues en
  una unica transaccion via `UnitOfWorkPort`. Un fallo interno de evaluacion
  se convierte en un reporte `status=failed`/`decision=blocked_by_contract`
  persistido (mismo patron que `CreateDetectionTrainingRunUseCase`), nunca en
  una excepcion sin persistir.
- Endpoints bajo `/api/v1/ml/detection-training-readiness-reports`,
  `/api/v1/ml/detection-training-runs/{id}/readiness-reports`,
  `/api/v1/datasets/releases/{id}/detection-training-readiness-reports`,
  `/api/v1/ml/annotation-bundles/{id}/detection-training-readiness-reports` y
  `/api/v1/ml/annotation-quality-gates/{id}/detection-training-readiness-reports`,
  con `X-Request-ID`.
- Sigue prohibido entrenar YOLO, instalar `ultralytics`, importar `torch`,
  PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar pesos o
  datasets externos, frontend, autenticacion, taxonomia, diagnostico,
  MLflow/TensorBoard/W&B, GPU obligatoria y reemplazar `MockInferenceEngine`.

## 23. Training Environment Specification (Fase 26)

- `DetectionTrainingEnvironmentSpec` especifica/evalua el entorno donde
  correria un futuro entrenamiento real para un `DetectionTrainingRun` ya
  con `DetectionTrainingReadinessReport` (Fase 25); `is_environment_ready=true`
  nunca significa que se aprovisiono un entorno real, que se instalo
  `ultralytics`/`torch`, ni que se ejecuto entrenamiento.
  `DetectionTrainingEnvironmentIssue` guarda hallazgos `error`/`warning`/`info`
  con codigos fijos (`python_version_mismatch`, `ultralytics_not_installed`,
  `gpu_not_available`, `external_weights_not_allowed`,
  `ci_training_not_allowed`, `output_dir_not_specified`,
  `no_training_executed`, `environment_check_safe_only`, etc.); ninguna de
  las dos entidades guarda binarios, pesos, imagenes ni labels completos.
- `DetectionTrainingEnvironmentDecision` tiene exactamente siete valores
  (`environment_ready`, `needs_manual_setup`,
  `blocked_by_missing_requirements`, `blocked_by_policy`,
  `blocked_by_unsupported_platform`, `blocked_by_storage_policy`,
  `blocked_by_dependency_policy`); `DetectionTrainingEnvironmentStatus` tiene
  `ready`/`warning`/`blocked`/`failed`. Igual que en Fase 25, un spec puede
  quedar `status=warning` con `is_environment_ready=true`.
- `DetectionTrainingEnvironmentEvaluator` (`application/services/`) solo usa
  chequeos seguros y no invasivos: `sys.version_info` para Python,
  `platform.system()` para SO, `importlib.util.find_spec(...)` para
  detectar disponibilidad de `ultralytics`/`torch` **sin importarlos**,
  `pathlib` para existencia/ubicacion de `artifact_output_dir` **sin
  escribir archivos por defecto**, y `os.environ` solo para detectar
  variables de CI (`CI`, `GITHUB_ACTIONS`) de forma informativa. Nunca llama
  `subprocess`, nunca consulta GPU/CUDA real, nunca instala ni descarga
  nada. `require_gpu=true`/`require_cuda=true` siempre bloquean
  (`blocked_by_missing_requirements`) porque no existe forma segura de
  confirmarlos sin comandos externos — nunca lo intenta.
- **`allow_ci_training=true` es siempre un error bloqueante**
  (`ci_training_not_allowed`, `blocked_by_policy`) porque CI nunca debe
  entrenar. Detectar que la evaluacion misma corre dentro de un entorno CI
  (`CI`/`GITHUB_ACTIONS` presentes) solo genera un **warning** informativo
  con el mismo codigo — nunca bloquea por si solo — porque ejecutar esta
  evaluacion desde un job de CI (como este propio pipeline de tests) no
  implica que un futuro entrenamiento real vaya a correr ahi.
- `CreateDetectionTrainingEnvironmentSpecUseCase` exige que el
  `DetectionTrainingReadinessReport` referenciado pertenezca al
  `DetectionTrainingRun` referenciado; si no,
  `DetectionTrainingEnvironmentNotAllowedError` (409). Nunca modifica
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport` ni
  `AnnotationBundleRun`. Persiste spec + issues en una unica transaccion via
  `UnitOfWorkPort`; un fallo interno de evaluacion se convierte en un spec
  `status=failed` persistido, nunca en una excepcion sin persistir.
- Endpoints bajo `/api/v1/ml/detection-training-environment-specs`,
  `/api/v1/ml/detection-training-runs/{id}/environment-specs`,
  `/api/v1/ml/detection-training-readiness-reports/{id}/environment-specs`,
  `/api/v1/ml/annotation-bundles/{id}/detection-training-environment-specs`
  y `/api/v1/datasets/releases/{id}/detection-training-environment-specs`,
  con `X-Request-ID`.
- Sigue prohibido entrenar YOLO, instalar `ultralytics`, importar `torch`,
  PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar pesos o
  datasets externos, ejecutar entrenamiento en CI, requerir GPU obligatoria,
  crear pesos `.pt`/`.onnx`/`.h5`, frontend, autenticacion, taxonomia,
  diagnostico, MLflow/TensorBoard/W&B y reemplazar `MockInferenceEngine`.

## 24. Training Artifact Policy & Registry (Fase 27)

- `DetectionTrainingArtifactPolicy` define/valida una politica de
  artefactos para un futuro entrenamiento real de un `DetectionTrainingRun`
  ya con `DetectionTrainingReadinessReport` (Fase 25) y
  `DetectionTrainingEnvironmentSpec` (Fase 26); `is_policy_ready=true` nunca
  significa que existe un peso real, que se entreno un modelo, ni que un
  artefacto fue efectivamente escrito en disco — solo que los gates
  tecnicos de politica configurados pasaron.
  `DetectionTrainingArtifactRecord` representa un artefacto planificado (o,
  en una fase futura explicita, uno real) sin guardar nunca su contenido
  binario; `DetectionTrainingArtifactIssue` guarda hallazgos
  (`error`/`warning`/`info`) con codigos fijos (p. ej.
  `output_dir_inside_repo`, `artifact_extension_forbidden`,
  `model_weight_in_repo_not_allowed`, `gitignore_does_not_exclude_weights`,
  `actual_artifact_registration_not_allowed_yet`, `no_training_executed`,
  `planned_artifact_only`); ninguna de las tres entidades guarda pesos,
  imagenes ni labels completos.
- `DetectionTrainingArtifactPolicyDecision` tiene exactamente siete valores
  (`artifact_policy_ready`, `needs_external_storage`,
  `blocked_by_repo_storage`, `blocked_by_missing_output_dir`,
  `blocked_by_forbidden_extension`, `blocked_by_policy_violation`,
  `blocked_by_environment`); `DetectionTrainingArtifactPolicyStatus` tiene
  `ready`/`warning`/`blocked`/`failed`. Igual que en Fases 25-26, una
  policy puede quedar `status=warning` con `is_policy_ready=true`, pero
  `is_policy_ready=true` exige siempre `decision=artifact_policy_ready`.
- `DetectionTrainingArtifactPolicyConfig` (`ml/configs/`) nunca crea
  `artifact_root_dir` por defecto (`require_artifact_root_dir=true` solo
  exige que se declare, no lo crea), nunca escribe archivos de artefactos,
  y `allow_actual_artifact_registration=false` por defecto — un artefacto
  `actual_*` nunca se registra sin autorizacion explicita, y esta fase no
  expone ningun mecanismo para crear uno real. `forbidden_extensions`
  incluye por defecto `.pt`/`.pth`/`.onnx`/`.h5`/`.ckpt`/`.pb`/`.tflite`.
- `DetectionTrainingArtifactPolicyEvaluator` (`application/services/`)
  recibe `DetectionTrainingRun`, `DetectionTrainingEnvironmentSpec`,
  `AnnotationBundleRun`+archivos y la config — **deliberadamente no recibe
  `DetectionTrainingReadinessReport`** porque ninguna de sus reglas de
  negocio depende de un campo de esa entidad (solo del `status`/`decision`
  del `EnvironmentSpec`); la verificacion de que el readiness report
  pertenece al run y de que el environment spec pertenece al readiness
  report vive en el caso de uso, nunca duplicada en el evaluador. El
  evaluador solo usa chequeos seguros y de solo lectura: `pathlib` para
  ubicacion de `artifact_root_dir` **sin escribir nada**, lectura de
  `.gitignore` si existe **sin modificarlo nunca**. Nunca llama
  `subprocess`, nunca importa `torch`/`ultralytics`, nunca instala
  dependencias, nunca descarga nada, nunca calcula un checksum real (no
  existen artefactos reales que hashear), nunca crea un archivo de pesos.
  Si un `expected_output` planificado (`weights_path_planned`,
  `metrics_path_planned`, `predictions_path_planned`, `run_dir_planned`)
  apunta dentro del repositorio con una extension de `forbidden_extensions`,
  bloquea (`blocked_by_repo_storage`/`blocked_by_forbidden_extension`)
  antes de aceptar la politica; un artefacto planificado fuera del repo se
  registra como `DetectionTrainingArtifactRecord` con
  `artifact_state=planned`, nunca `registered`/`missing` (esos estados
  solo aplicarian a artefactos reales de una fase futura).
- **`CreateDetectionTrainingArtifactPolicyUseCase` verifica tres relaciones
  de pertenencia antes de evaluar**: el `DetectionTrainingReadinessReport`
  referenciado debe pertenecer al `DetectionTrainingRun` referenciado, el
  `DetectionTrainingEnvironmentSpec` referenciado debe pertenecer al mismo
  run, y ese environment spec debe pertenecer a ese mismo readiness report
  — si cualquiera de las tres relaciones no se cumple,
  `DetectionTrainingArtifactPolicyNotAllowedError` (409). Nunca modifica
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport` ni
  `DetectionTrainingEnvironmentSpec`. Persiste policy + records + issues en
  una unica transaccion via `UnitOfWorkPort`; un fallo interno de
  evaluacion se convierte en una policy `status=failed` persistida, nunca
  en una excepcion sin persistir.
- Endpoints bajo `/api/v1/ml/detection-training-artifact-policies`,
  `/api/v1/ml/detection-training-runs/{id}/artifact-policies`,
  `/api/v1/ml/detection-training-readiness-reports/{id}/artifact-policies`,
  `/api/v1/ml/detection-training-environment-specs/{id}/artifact-policies`,
  `/api/v1/ml/annotation-bundles/{id}/detection-training-artifact-policies`
  y `/api/v1/datasets/releases/{id}/detection-training-artifact-policies`,
  con `X-Request-ID`.
- Sigue prohibido entrenar YOLO, instalar `ultralytics`, importar `torch`,
  PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar pesos o
  datasets externos, copiar o modificar imagenes, escribir artefactos o
  crear pesos reales `.pt`/`.pth`/`.onnx`/`.h5`/`.ckpt`, subir binarios al
  repositorio, ejecutar entrenamiento en CI, requerir GPU obligatoria,
  frontend, autenticacion, taxonomia, diagnostico, MLflow/TensorBoard/W&B y
  reemplazar `MockInferenceEngine`.

## 25. Git Ignore & Training Safety Guardrails (Fase 28)

- `.gitignore` incluye, ademas de las reglas previas (cache de Python,
  entornos virtuales, DB local, imagenes de storage), un bloque explicito de
  guardrails de entrenamiento: extensiones de pesos/modelos
  (`*.pt`/`*.pth`/`*.onnx`/`*.h5`/`*.ckpt`/`*.pb`/`*.tflite`) y carpetas de
  salida (`runs/`, `training_outputs/`, `training_artifacts/`,
  `model_artifacts/`, `checkpoints/`, `weights/`, `mlruns/`, `wandb/`,
  `tensorboard/`, `lightning_logs/`, `predictions/`, `inference_outputs/`,
  `evaluation_outputs/`, `experiments/`, `.local_training/`). Esta lista es
  la unica fuente de verdad manual del repositorio; nunca se genera ni se
  edita por codigo.
- `blueberry_microid.ml.configs.training_safety_defaults` centraliza
  `default_forbidden_extensions()`/`default_required_gitignore_patterns()` —
  **unica fuente de verdad programatica**, compartida entre
  `DetectionTrainingArtifactPolicyConfig` (Fase 27, evaluacion por-policy) y
  el nuevo `RepositorySafetyConfig` (Fase 28, escaneo de todo el
  repositorio). Cambiar la lista de patrones requeridos se hace una sola vez
  ahi; nunca se duplica el literal en ninguno de los dos configs.
- `RepositorySafetyValidator` (`ml/validation/repository_safety_validator.py`)
  es un chequeo de solo lectura e independiente de cualquier
  `DetectionTrainingRun`/`DetectionTrainingArtifactPolicy` persistido: lee
  `.gitignore` del repo (sin escribirlo nunca) y, opcionalmente, valida una
  lista de rutas candidatas (paths absolutos) contra extensiones prohibidas
  y ubicacion relativa al repo. Vive en `ml/` (no en `application/`) porque
  no depende de ningun puerto ni orquesta un caso de uso — es una utilidad
  reutilizable tanto por un futuro caso de uso como por el CLI standalone.
  Nunca importa `torch`/`ultralytics`, nunca llama `subprocess`, nunca crea
  ni modifica archivos.
- `scripts/check_repository_safety.py` es un CLI standalone (mismo patron
  que `scripts/validate_training_manifest.py`) que imprime un reporte JSON y
  devuelve `0` si el repositorio es seguro o `1` si falta algun patron de
  `.gitignore` o hay una ruta candidata violatoria. No se conecta a FastAPI,
  PostgreSQL, Redis ni Celery, y no requiere ningun `DetectionTrainingRun`
  previo — es intencionalmente el chequeo mas barato posible antes de un
  futuro entrenamiento real.
- El test `tests/unit/ml/test_repository_safety_validator.py::test_real_repository_gitignore_is_safe`
  valida el `.gitignore` **real** del repositorio (no uno sintetico en
  `tmp_path`) contra `RepositorySafetyConfig()` por defecto; corre dentro del
  job `unit-and-api-tests` existente, sin agregar un job de CI nuevo ni
  instalar dependencias adicionales — el guardrail de CI para esta fase es
  literalmente ese test.
- Esta fase no agrega entidades ni tablas nuevas: es higiene de repositorio,
  no un nuevo agregado de dominio. No modifica `DetectionTrainingArtifactPolicy`/
  `Record`/`Issue` de la Fase 27 mas alla de reapuntar sus valores por
  defecto al modulo compartido de Fase 28.
- Sigue prohibido entrenar YOLO, instalar `ultralytics`, importar `torch`,
  PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar pesos o
  datasets externos, copiar o modificar imagenes, guardar binarios en base
  de datos, subir artefactos binarios al repositorio, ejecutar entrenamiento
  en CI, requerir GPU obligatoria, frontend, autenticacion, taxonomia,
  diagnostico, MLflow/TensorBoard/W&B y reemplazar `MockInferenceEngine`.

## 26. Training Execution Gate & Manual Runner Scaffold (Fase 29)

- `DetectionTrainingExecutionRun` es una puerta de ejecucion persistida para
  un futuro intento de entrenamiento real, manual y separado de este
  sistema; `status=ready_to_execute` nunca significa que se entreno un
  modelo — solo que todos los prerequisitos configurados pasaron y que un
  humano tendria que disparar el entrenamiento el mismo, fuera de este
  codigo. `is_executable` es siempre `False` en esta fase (invariante de la
  entidad: construir una con `is_executable=True` lanza `ValueError`,
  porque no existe ningun mecanismo que le de sentido a ese valor todavia).
  `DetectionTrainingExecutionIssue` guarda hallazgos `error`/`warning`/`info`
  con codigos fijos (`detection_training_not_planned`,
  `readiness_report_missing`, `readiness_not_ready`,
  `environment_spec_missing`, `environment_not_ready`,
  `artifact_policy_missing`, `artifact_policy_not_ready`,
  `repository_safety_failed`, `ci_execution_blocked`,
  `manual_confirmation_missing`, `manual_confirmation_invalid`,
  `training_execution_disabled`, `command_preview_missing`,
  `expected_outputs_missing`, `artifact_root_not_safe`,
  `real_runner_not_implemented`, `no_training_executed`,
  `taxonomy_not_allowed`); ninguna de las dos entidades guarda pesos,
  imagenes ni labels completos.
- `DetectionTrainingExecutionStatus` tiene exactamente cuatro valores
  (`blocked`, `manual_required`, `ready_to_execute`, `failed`) —
  deliberadamente **sin** `running`/`completed`/`trained`/`model_created`,
  porque esta fase nunca ejecuta nada. `DetectionTrainingExecutionDecision`
  tiene nueve valores (`blocked_by_prerequisites`, `blocked_by_ci`,
  `blocked_by_repository_safety`, `blocked_by_artifact_policy`,
  `blocked_by_environment`, `blocked_by_readiness`,
  `blocked_by_configuration`, `manual_confirmation_required`,
  `ready_for_manual_execution`). `DetectionTrainingExecutionMode` solo
  admite `scaffold_only`/`manual_gate` — nunca un modo de ejecucion real.
- `DetectionTrainingExecutionConfig` (`ml/configs/`) tiene
  `enable_real_training=false` y `dry_run_only=true` como rieles de
  seguridad, no como feature flags: `enable_real_training=true` o
  `dry_run_only=false` siempre bloquean con `training_execution_disabled`,
  nunca desbloquean ejecucion. `require_manual_confirmation=true` exige que
  `manual_confirmation_text` coincida exactamente con
  `required_confirmation_text` (por defecto "I understand this will only
  create a scaffold and will not train a model"); si falta o no coincide,
  `status=manual_required`. Si coincide pero
  `allow_ready_to_execute_status=false`, el status maximo alcanzable sigue
  siendo `manual_required` — nunca `ready_to_execute` sin autorizacion
  explicita de la config.
- `DetectionTrainingExecutionGateEvaluator` (`application/services/`) recibe
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport`,
  `DetectionTrainingEnvironmentSpec`, `DetectionTrainingArtifactPolicy` y un
  `RepositorySafetyReport` ya calculado (nunca instancia
  `RepositorySafetyValidator` el mismo — eso lo hace el caso de uso, mismo
  patron de composicion que otros evaluadores). Valida: el run debe estar
  `planned`/`is_runnable=true` con `command_preview`/`expected_outputs`
  segun config; el readiness report debe ser `ready_for_training`; el
  environment spec debe ser `environment_ready`; el artifact policy debe
  ser `artifact_policy_ready`; el repositorio debe pasar
  `RepositorySafetyValidator` y `artifact_policy.storage_policy` no debe
  marcar `artifact_root_dir_inside_repo=true`. Detecta CI via
  `os.environ.get("CI")`/`os.environ.get("GITHUB_ACTIONS")` y bloquea con
  `ci_execution_blocked` si `block_in_ci=true`. Siempre agrega los issues
  informativos `no_training_executed` y `real_runner_not_implemented`.
  Nunca llama `subprocess`, nunca importa `torch`/`ultralytics`, nunca
  instala dependencias, nunca modifica archivos ni crea pesos.
- `ManualYoloTrainingRunnerScaffold` (`application/services/`) toma una
  `DetectionTrainingExecutionGateEvaluation` ya calculada y produce un
  `execution_plan` JSON con `preconditions`, `manual_steps`,
  `command_preview` (copiado tal cual del run, nunca ejecutado),
  `output_expectations`, `artifact_policy_reminders`, `rollback_notes`,
  `safety_notes`, `prohibited_actions` y un `checklist`. Nunca ejecuta el
  comando, nunca crea archivos, nunca importa `torch`/`ultralytics`, nunca
  llama `subprocess` — es texto/JSON puro derivado de la evaluacion.
- **`CreateDetectionTrainingExecutionRunUseCase` verifica seis relaciones de
  pertenencia** antes de evaluar: readiness pertenece al run,
  environment_spec pertenece al run, environment_spec pertenece al
  readiness report, artifact_policy pertenece al run, artifact_policy
  pertenece al readiness report, y artifact_policy pertenece al
  environment_spec — si cualquiera falla,
  `DetectionTrainingExecutionRunNotAllowedError` (409). El caso de uso
  instancia `RepositorySafetyValidator` directamente (mismo patron que
  `CreateImageDatasetAuditRunUseCase` instancia `ImageDatasetAuditor`), pasa
  el reporte al evaluador, y enriquece `execution_plan` con
  `ManualYoloTrainingRunnerScaffold` antes de persistir. Nunca modifica
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport`,
  `DetectionTrainingEnvironmentSpec` ni `DetectionTrainingArtifactPolicy`.
  Persiste run + issues en una unica transaccion via `UnitOfWorkPort`; un
  fallo interno de evaluacion se convierte en un execution run
  `status=failed` persistido, nunca en una excepcion sin persistir.
- Endpoints bajo `/api/v1/ml/detection-training-execution-runs`,
  `/api/v1/ml/detection-training-runs/{id}/execution-runs`,
  `/api/v1/ml/detection-training-readiness-reports/{id}/execution-runs`,
  `/api/v1/ml/detection-training-environment-specs/{id}/execution-runs`,
  `/api/v1/ml/detection-training-artifact-policies/{id}/execution-runs`,
  `/api/v1/ml/annotation-bundles/{id}/detection-training-execution-runs` y
  `/api/v1/datasets/releases/{id}/detection-training-execution-runs`, con
  `X-Request-ID`.
- Sigue prohibido entrenar YOLO, ejecutar YOLO, ejecutar comandos de
  entrenamiento, llamar `subprocess`, instalar `ultralytics`, importar
  `torch`, PyTorch, TensorFlow, CNN, ViT, deep learning real, descargar
  pesos o datasets externos, ejecutar entrenamiento en CI, requerir GPU
  obligatoria, crear pesos reales `.pt`/`.onnx`/`.h5`/`.pth`/`.ckpt`, copiar
  o modificar imagenes, guardar binarios en base de datos, subir artefactos
  binarios al repositorio, frontend, autenticacion, taxonomia, diagnostico,
  MLflow/TensorBoard/W&B y reemplazar `MockInferenceEngine`.
## 30. Manual Training Runbook & Operator Checklist (Fase 30)

- Fase 30 es documentacion operativa preventiva para una futura ejecucion
  manual de entrenamiento de deteccion. No implementa runner real, no
  ejecuta entrenamiento, no cambia FastAPI/Celery/Redis/PostgreSQL y no
  modifica la logica de negocio.
- `docs/training/manual_training_runbook.md` documenta proposito, alcance,
  limites, prerequisitos, validacion de entorno/repositorio/
  `artifact_root_dir`, interpretacion de `command_preview`, checklist,
  evidencias, registro posterior de artefactos, errores, rollback, acciones
  prohibidas y cierre.
- `docs/training/operator_checklist.md` contiene casillas Markdown para el
  operador y criterios explicitos para no continuar.
- `docs/training/artifact_registration_protocol.md` describe el registro
  futuro metadata-only de artefactos: paths/URI, tipo, estado, tamano,
  `checksum_sha256`, fecha, training run y policy. No guarda pesos, imagenes,
  labels completos ni binarios en DB.
- `docs/training/rollback_protocol.md` cubre fallos futuros, pesos
  incompletos, artefactos dentro del repo, `artifact_root_dir` roto, dataset
  mismatch, metricas invalidas, labels incorrectos y trazabilidad de
  artefactos `deleted`/`ignored`.
- `docs/training/prohibited_actions.md` prohibe entrenar en CI, subir pesos
  a Git, guardar pesos en DB, modificar imagenes originales, cambiar labels
  despues del quality gate sin nuevo bundle, usar taxonomia, afirmar
  diagnostico, descargar pesos sin policy, instalar dependencias pesadas sin
  environment spec, ejecutar `command_preview` sin revision, ignorar artifact
  policy/repository safety, reemplazar `MockInferenceEngine` y mezclar
  datasets externos sin evaluacion formal.
- `scripts/check_training_docs.py` valida los seis documentos y sus secciones
  minimas. Es read-only, sin dependencias externas; no importa
  `torch`/`ultralytics`, no llama `subprocess`, no modifica archivos y no
  ejecuta entrenamiento.
- Los gates que el runbook exige revisar son `AnnotationBundleRun`
  `completed`, `AnnotationQualityGateRun` `passed`, `DetectionTrainingRun`
  `planned`, `DetectionTrainingReadinessReport` `ready`,
  `DetectionTrainingEnvironmentSpec` `ready`,
  `DetectionTrainingArtifactPolicy` `ready`, `RepositorySafetyValidator`
  passed/safe y `DetectionTrainingExecutionRun` `manual_required` o
  `ready_to_execute`.
- `ready_to_execute` sigue sin significar que hubo entrenamiento; solo indica
  que la puerta manual configurada paso y que una persona aun tendria que
  ejecutar un procedimiento en una fase futura y separada.
- Sigue prohibido entrenar YOLO, ejecutar YOLO, instalar `ultralytics`,
  importar `torch`, usar PyTorch/TensorFlow/CNN/ViT/deep learning real,
  descargar pesos o datasets externos, ejecutar entrenamiento en CI, crear
  pesos `.pt`/`.onnx`/`.h5`/`.pth`/`.ckpt`, copiar/modificar imagenes,
  guardar binarios en DB, subir artefactos binarios al repo, frontend,
  autenticacion, taxonomia, diagnostico, herramientas externas de tracking y
  reemplazar `MockInferenceEngine`.

## 31. Local Experimental YOLO Training Runner (Fase 31)

- Fase 31 permite entrenamiento YOLO real solo por runner local/manual,
  nunca en CI, nunca automatico y nunca desde FastAPI/Celery.
- `pyproject.toml` agrega el extra opcional `training` con
  `ultralytics>=8.3,<9.0`; CI no debe instalar ese extra ni requerir GPU.

## 32. Local YOLO Training Smoke Test (Fase 32)

- Fase 32 permite instalar localmente el extra `training` y validar import de
  `ultralytics`, pero GitHub Actions sigue sin entrenar y sin instalar ese
  extra.
- `scripts/run_local_yolo_training.py --dry-run-validation-only` debe validar
  los mismos gates que una ejecucion real: execution run `ready_to_execute`,
  artifact policy ready, registro real permitido, `dataset.yaml` del bundle,
  `base_model_path` externo, `artifact_root_dir` externo, confirmacion manual
  exacta y `RepositorySafetyValidator`.
- El modo `dry-run-validation-only` no importa `ultralytics`, no entrena, no
  crea pesos, no registra metadata y no guarda binarios.
- La validacion local de Fase 32 cerro como Cierre B: se instalo `training` y
  se valido import, pero no se ejecuto entrenamiento porque faltaban
  PostgreSQL local, execution run persistido, artifact policy ready y
  `dataset.yaml` generado.
- `LocalYoloTrainingRunner` es el unico modulo que puede importar
  `ultralytics`, y lo hace lazy dentro de `run()` despues de validar no CI,
  confirmacion manual exacta, execution run `ready_to_execute`, artifact
  policy ready, permiso de registro actual, dataset YAML, artifact root
  externo, base model local externo y `RepositorySafetyValidator`.
- El runner no llama `subprocess`; usa la API Python de `ultralytics`.
- `RunLocalYoloTrainingUseCase` registra solo metadata en
  `DetectionTrainingArtifactRecord`: path, relative path, extension, size,
  `checksum_sha256`, kind, state y `training_execution_run_id`; no guarda
  bytes de pesos, imagenes, labels completos ni binarios en DB.
- `scripts/run_local_yolo_training.py` es CLI local/manual; requiere
  `--manual-confirmation-text`, `--artifact-root-dir` y `--base-model-path`.
- Sigue prohibido entrenamiento en CI, entrenamiento automatico, datasets
  externos, descargas de pesos sin policy, outputs dentro del repo, pesos en
  Git, binarios en DB, modificar imagenes originales, taxonomia, diagnostico,
  frontend, autenticacion, MLflow/TensorBoard/W&B y reemplazar
  `MockInferenceEngine`.
