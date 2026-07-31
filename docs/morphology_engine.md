# Motor morfológico explicable 0.3.0

## Propósito

`PreliminaryTwoImageEngine 0.3.0` combina una fotografía macroscópica de caja
Petri con una imagen microscópica de la misma muestra. Su objetivo es producir
una **clasificación morfológica preliminar y trazable**, no identificar género o
especie ni emitir un diagnóstico.

Todas las predicciones requieren revisión humana. La predicción automática, sus
mediciones y la decisión del especialista se conservan por separado.

## Categorías preliminares

- `no_evident_growth`: no se observa crecimiento candidato suficiente en la captura;
- `suspicious_growth`: hay crecimiento candidato, pero la microscopía no aporta evidencia suficiente;
- `probable_fungal_growth`: la evidencia combinada presenta un patrón filamentoso compatible;
- `probable_bacterial_growth`: la evidencia combinada presenta un patrón celular no filamentoso compatible;
- `inconclusive`: calidad insuficiente, señales ambiguas o conflicto entre imágenes.

Estas categorías son visuales y amplias. No representan una etiqueta taxonómica.

## Evidencia macroscópica

El procesamiento de la caja Petri intenta aislar la placa y excluir el borde
externo. Después calcula:

- cantidad de regiones candidatas;
- cobertura candidata sobre el interior de la placa;
- área media de las regiones;
- circularidad media;
- irregularidad de bordes;
- variación de textura;
- saturación, tono e intensidad;
- nitidez de la captura.

Una región candidata no equivale automáticamente a una colonia confirmada. La
textura del medio, reflejos, condensación, residuos o iluminación irregular
pueden influir en la segmentación.

## Evidencia microscópica

El procesamiento intenta aislar el campo iluminado y calcula:

- densidad de bordes;
- cobertura de estructuras filamentosas;
- densidad del esqueleto morfológico;
- densidad de puntos de ramificación;
- proporción de componentes alargados;
- cantidad de componentes estructurales;
- variación de intensidad y nitidez;
- cobertura del campo analizado.

Estas señales describen estructuras visibles. No permiten por sí mismas afirmar
septación, género, especie, viabilidad o patogenicidad.

## Fusión de evidencia

El motor calcula tres puntuaciones auditables:

1. evidencia macroscópica de crecimiento;
2. evidencia microscópica filamentosa;
3. evidencia microscópica celular.

La regla aplicada, los valores utilizados y la categoría resultante se guardan
en `decision_trace`. La confianza está limitada deliberadamente a un máximo de
`0.65`, porque el motor todavía no ha sido calibrado contra un conjunto de datos
real, representativo y etiquetado por especialistas.

## Calidad de captura

Antes de interpretar las señales se registran indicadores de calidad:

- enfoque suficiente de Petri y microscopía;
- sobreexposición o subexposición de la caja;
- detección del límite de la placa;
- detección del campo microscópico;
- posible campo vacío o desenfocado;
- éxito o fallo de extracción de cada imagen.

Cuando una de las dos imágenes no puede procesarse de forma confiable, el motor
devuelve `inconclusive`.

## Datos necesarios para validación científica

Para avanzar desde categorías visuales hacia grupos, géneros o especies se debe
construir un dataset pareado. Cada muestra debería incluir:

- imagen Petri original;
- una o más imágenes microscópicas originales;
- medio de cultivo;
- temperatura y tiempo de incubación;
- aumento, tinción y método de preparación;
- origen y parte del arándano analizada;
- etiqueta confirmada y método de confirmación;
- especialista responsable;
- condiciones de captura;
- exclusiones o problemas de calidad.

Las particiones de entrenamiento, validación y prueba deben realizarse por
muestra o aislamiento, no por fotografía, para evitar fuga de información.

## Evaluación futura

La validación debe reportar, como mínimo:

- matriz de confusión;
- precisión, sensibilidad y especificidad por categoría;
- F1 macro y por clase;
- calibración de probabilidades;
- tasa de resultados no concluyentes;
- acuerdo entre especialistas;
- desempeño por medio, aumento y condición de captura.

La identificación a nivel de género o especie solo debe habilitarse después de
alcanzar criterios de aceptación definidos con microbiología y documentar las
limitaciones del conjunto de datos.

## Separación de responsabilidades

- El motor automático genera evidencia y una categoría preliminar.
- El especialista confirma, corrige, rechaza o marca como no concluyente.
- El administrador gestiona usuarios y, en etapas posteriores, versiones,
  datasets y evaluaciones.
- La aplicación conserva la trazabilidad de todos esos pasos.
