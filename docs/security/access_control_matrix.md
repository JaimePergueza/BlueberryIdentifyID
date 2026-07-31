# Política de autenticación y autorización del MVP

## Objetivo

Esta política clasifica todas las rutas de BlueberryMicroID antes de aplicar autenticación. El principio por defecto es **denegar acceso**: una ruta operativa que no esté clasificada explícitamente no debe quedar pública.

## Roles

| Rol | Alcance |
| --- | --- |
| `specialist` | Operación diaria del laboratorio: registrar muestras e imágenes, ejecutar el flujo oficial, consultar historial y detalle, y registrar revisiones humanas. |
| `admin` | Incluye todas las capacidades de `specialist`, además de gestión de usuarios, configuración técnica, gobierno de datos, evaluación y entrenamiento experimental. |

## Rutas públicas

| Ruta | Acceso | Motivo |
| --- | --- | --- |
| `GET /health` | Público | Comprobación de disponibilidad del servicio. No devuelve datos internos. |
| `POST /api/v1/auth/login` | Público | Intercambio de usuario y contraseña por un token de sesión. |
| `/docs`, `/redoc`, `/openapi.json` | Solo entornos distintos de `production` | Documentación interactiva para desarrollo y pruebas. En producción se deshabilita. |

Ninguna otra ruta es pública.

## Rutas autenticadas para `specialist` y `admin`

### Flujo oficial y trazabilidad

- `/api/v1/analysis/*`
- `/api/v1/analysis-runs/*`
- `/api/v1/analysis-runs/{id}/reviews*`
- `/api/v1/samples/*`
- `/api/v1/petri-images/*`
- `/api/v1/micro-images/*`

Estas rutas permiten cargar y consultar muestras, ejecutar análisis preliminares, revisar resultados y consultar el historial consolidado.

### Sesión del usuario

- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

Cada usuario puede consultar su propia identidad y revocar su sesión actual.

## Rutas exclusivas de `admin`

### Gestión de usuarios

- `/api/v1/admin/users/*`

Incluye creación, listado, activación, desactivación y cambios controlados de rol o contraseña. Nunca devuelve hashes de contraseña ni tokens almacenados.

### Configuración de modelos y evaluación

- `/api/v1/model-versions/*`
- `/api/v1/model-evaluation/*`

### Gobierno de datos, anotaciones y entrenamiento experimental

- `/api/v1/datasets/*`
- `/api/v1/ml/*`
- `/api/v1/training-runs/*`
- `/api/v1/training-run-comparisons/*`
- `/api/v1/image-audits/*`
- `/api/v1/image-features/*`
- `/api/v1/petri-segmentations/*`
- `/api/v1/petri-region-reviews/*`
- `/api/v1/petri-annotation-exports/*`
- `/api/v1/annotation-bundles/*`
- `/api/v1/annotation-quality-gates/*`
- `/api/v1/detection-training/*`
- `/api/v1/detection-training-readiness/*`
- `/api/v1/detection-training-environment/*`
- `/api/v1/detection-training-artifacts/*`
- `/api/v1/detection-training-execution/*`
- `/api/v1/tasks/*`

Estas rutas corresponden a configuración técnica, curación, auditoría, preparación de datasets y procesos experimentales. No forman parte de la operación diaria de un especialista.

## Reglas de autorización

1. `admin` hereda todas las capacidades de `specialist`.
2. Un usuario inactivo no puede iniciar sesión ni utilizar una sesión ya emitida.
3. Las sesiones tienen expiración, pueden revocarse mediante logout y se almacenan únicamente como hash irreversible del token.
4. Las contraseñas se almacenan con Argon2 mediante `pwdlib`; nunca en texto plano.
5. Las respuestas de autenticación usan errores genéricos para no revelar si un usuario existe.
6. La API responde `401` cuando no hay una sesión válida y `403` cuando el rol no tiene permiso.
7. El usuario administrador inicial se crea mediante un comando explícito que recibe la contraseña por variable de entorno o entrada segura; no se incluye ninguna contraseña por defecto en el repositorio.
8. En producción se exige HTTPS en la capa de despliegue. Un token bearer no debe enviarse por HTTP sin cifrado.

## Matriz resumida

| Grupo | Público | `specialist` | `admin` |
| --- | ---: | ---: | ---: |
| Salud | Sí | Sí | Sí |
| Login | Sí | Sí | Sí |
| Perfil y logout | No | Sí | Sí |
| Muestras, imágenes, análisis y revisión humana | No | Sí | Sí |
| Historial y detalle | No | Sí | Sí |
| Gestión de usuarios | No | No | Sí |
| Modelos, datasets, evaluación y entrenamiento | No | No | Sí |
| Documentación API | Solo no-producción | Sí en no-producción | Sí en no-producción |

## Criterio de pruebas

La implementación debe demostrar como mínimo:

- una petición anónima a cualquier ruta operativa recibe `401`;
- `specialist` puede completar el flujo de carga, consulta y revisión;
- `specialist` recibe `403` en rutas administrativas;
- `admin` puede acceder a todos los grupos;
- una sesión expirada, revocada o de usuario inactivo recibe `401`;
- `/health` y login siguen disponibles sin token;
- OpenAPI y documentación se deshabilitan cuando `ENVIRONMENT=production`.
