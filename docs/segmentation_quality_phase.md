# Fase: segmentación verificable y control de calidad

## Objetivo

Permitir que el especialista compruebe visualmente qué regiones utilizó el
motor y evitar conclusiones cuando la captura no cumple condiciones mínimas.

## Alcance

- detectar y representar el límite de la caja Petri;
- representar regiones candidatas de colonia;
- detectar y representar el campo microscópico;
- representar componentes filamentosos y puntos de ramificación;
- guardar coordenadas normalizadas y trazables junto con la predicción;
- mostrar las superposiciones sobre las imágenes protegidas;
- calcular un estado de calidad `accepted`, `warning` o `rejected`;
- forzar `inconclusive` cuando falla una condición bloqueante;
- conservar la revisión humana obligatoria.

## Fuera de alcance

- identificación de género o especie;
- diagnóstico;
- uso de una máscara automática como ground truth;
- entrenamiento con imágenes no confirmadas;
- asumir que una región candidata equivale a una colonia real.
