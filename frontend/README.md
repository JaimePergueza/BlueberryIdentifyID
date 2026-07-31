# BlueberryMicroID Frontend

Interfaz React y TypeScript del MVP demostrable. Consume exclusivamente los
contratos HTTP de FastAPI y no contiene lógica microbiológica ni reglas de
clasificación propias.

## Stack

- React
- TypeScript estricto
- Vite
- React Router
- TanStack Query
- Vitest y Testing Library

## Recorrido implementado

1. Inicio de sesión.
2. Dashboard con actividad reciente.
3. Carga conjunta de imagen Petri e imagen microscópica.
4. Resultado preliminar explicable.
5. Revisión experta.
6. Historial paginado y filtrable.
7. Detalle consolidado de trazabilidad.

Las categorías se presentan en español y la interfaz diferencia siempre la
predicción automática de la decisión final humana.

## Desarrollo local

El backend debe estar activo en `http://127.0.0.1:8000`.

```bash
cd frontend
npm install
npm run dev
```

Vite inicia en `http://127.0.0.1:5173` y redirige `/api` y `/health` al
backend local. Esto evita configurar CORS durante el desarrollo.

Para apuntar a una API desplegada:

```text
VITE_API_BASE_URL=https://api.example.com
```

La URL no debe terminar en `/`. En producción se recomienda servir frontend y
API bajo el mismo origen o configurar explícitamente el proxy/reverse proxy en
la fase de despliegue.

## Calidad

```bash
npm run test
npm run build
npm run check
```

`npm run check` ejecuta las pruebas y después compila la aplicación. Las pruebas
críticas cubren:

- login correcto e incorrecto;
- token bearer y expiración de sesión;
- rutas protegidas y límites de rol;
- carga de las dos imágenes y navegación al resultado preliminar.

## Sesión

El token opaco y el usuario se almacenan en `sessionStorage`, por lo que no se
persisten entre sesiones completas del navegador. Cualquier respuesta `401`
limpia la sesión local y devuelve al usuario al acceso protegido.

El frontend nunca almacena contraseñas ni conoce los hashes mantenidos por el
backend.

## Estructura

```text
src/
├── components/   Componentes reutilizables y protección de rutas
├── lib/          Cliente HTTP, sesión, formatos y caché
├── pages/        Pantallas del recorrido del MVP
├── styles/       Sistema visual responsive
├── test/         Configuración de Vitest
└── types/        Contratos TypeScript de la API
```
