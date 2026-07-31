# Motor morfológico explicable 0.4.1

## Propósito

`PreliminaryTwoImageEngine 0.4.1` combina una fotografía macroscópica de caja
Petri con una imagen microscópica de la misma muestra. Su objetivo es producir
una **clasificación morfológica preliminar, verificable y trazable**, no
identificar género o especie ni emitir un diagnóstico.

Todas las predicciones requieren revisión humana. La predicción automática, sus
mediciones, sus regiones visualizadas, la versión exacta del motor y la decisión
del especialista se conservan por separado.

## Cambios de la versión 0.4.1

La versión 0.4.1 corrige dos limitaciones observadas con capturas reales:

- en Petri, medios oscuros con colonias grandes, texturizadas o parcialmente
  conectadas ya no se descartan silenciosamente como una única máscara extensa;
- en microscopía, los componentes pequeños sin suficiente soporte, las cajas
  redundantes y los píxeles de ramificación contiguos se filtran o consolidan
  antes de mostrarse.

El extractor Petri usa una segunda segmentación conservadora basada en contraste
local, distancia de color LAB, desviación de intensidad y textura local. Cuando
una región grande puede separarse, aplica transformación de distancia y
watershed. Si existe señal visual fuerte pero no se pueden obtener regiones
confiables, se activa un conflicto de segmentación y el resultado se bloquea
como `inconclusive`; nunca se interpreta automáticamente como ausencia de
crecimiento.

Los análisis creados con versiones anteriores permanecen inmutables y conservan
la versión con la que fueron procesados.

## Categorías preliminares

- `no_evident_growth`: no se observa crecimiento candidato suficiente en una captura aceptada;
- `suspicious_growth`: hay crecimiento candidato, pero la microscopía no aporta evidencia suficiente;
- `probable_fungal_growth`: la evidencia combinada presenta un patrón filamentoso compatible;
- `probable_bacterial_growth`: la evidencia combinada presenta un patrón celular no filamentoso compatible;
- `inconclusive`: calidad insuficiente, señales ambiguas, conflicto de segmentación o conflicto entre imágenes.

Estas categorías son visuales y amplias. No representan una etiqueta taxonómica.

## Evidencia macroscópica

El procesamiento de la caja Petri intenta aislar la placa mediante detección de
círculo central y una alternativa basada en contornos. Después excluye el borde
externo y calcula:

- cantidad de regiones candidatas;
- cobertura candidata sobre el interior de la placa;
- fracción de señal visual candidata antes del filtrado final;
- área media de las regiones;
- circularidad media;
- irregularidad de bordes;
- variación de textura;
- saturación, tono e intensidad;
- nitidez de la captura;
- presencia de crecimiento grande o confluente refinado;
- conflicto entre señal visual y regiones segmentadas.

Una región candidata no equivale automáticamente a una colonia confirmada. La
textura del medio, reflejos, condensación, residuos o iluminación irregular
pueden influir en la segmentación.

## Evidencia microscópica

El procesamiento intenta aislar el campo iluminado y calcula:

- densidad de bordes;
- cobertura de estructuras filamentosas;
- densidad del esqueleto morfológico;
- densidad de puntos de ramificación consolidados;
- proporción de componentes alargados;
- cantidad de componentes estructurales con soporte suficiente;
- variación de intensidad y nitidez;
- cobertura del campo analizado.

La superposición limita los elementos visuales a los componentes y eventos de
ramificación más respaldados. Estas señales describen estructuras visibles. No
permiten por sí mismas afirmar septación, género, especie, viabilidad o
patogenicidad.

## Visualización verificable

La versión 0.4.1 guarda coordenadas normalizadas junto con la predicción:

- límite detectado de la caja Petri;
- polígonos y cajas de regiones candidatas;
- límite detectado del campo microscópico;
- cajas consolidadas de componentes estructurales y filamentosos;
- puntos de ramificación agrupados.

La interfaz superpone esas marcas sobre las imágenes protegidas y permite
mostrarlas u ocultarlas. También presenta la fracción de señal candidata, el
estado de crecimiento confluente y cualquier conflicto de segmentación. Las
marcas son evidencia de lo que procesó el motor; no son anotaciones expertas ni
ground truth.

Las coordenadas se guardan en `feature_summary.petri.visualization` y
`feature_summary.micro.visualization`, con `coordinate_space=normalized`. Esto
permite reproducir la superposición aunque cambie el tamaño de presentación.

## Puerta de calidad

Antes de fusionar evidencia se calcula un estado:

- `accepted`: no se detectan condiciones bloqueantes ni advertencias;
- `warning`: la captura puede interpretarse, pero presenta problemas no bloqueantes;
- `rejected`: no debe interpretarse morfológicamente.

Son condiciones bloqueantes:

- fallo de extracción de cualquiera de las imágenes;
- imposibilidad de aislar el límite de la caja Petri;
- imposibilidad de aislar el campo microscópico;
- sobreexposición o subexposición extrema de Petri;
- campo microscópico aparentemente vacío o sin información suficiente;
- contraste o textura compatible con crecimiento en Petri sin regiones que puedan separarse de forma confiable.

El desenfoque moderado, el crecimiento confluente refinado y las segmentaciones
anormalmente densas se registran como advertencias. Cuando el estado es
`rejected`, el motor detiene la fusión, devuelve `inconclusive`, limita la
confianza a `0.25` y explica los motivos para repetir o revisar la captura.

El estado, la puntuación técnica, las razones bloqueantes y las advertencias se
guardan en `quality_summary` y en el primer paso de `decision_trace`.

## Fusión de evidencia

Solo cuando la puerta de calidad no rechaza la captura, el motor calcula tres
puntuaciones auditables:

1. evidencia macroscópica de crecimiento;
2. evidencia microscópica filamentosa;
3. evidencia microscópica celular.

La regla aplicada, los valores utilizados y la categoría resultante se guardan
en `decision_trace`. La confianza está limitada deliberadamente a un máximo de
`0.65`, porque el motor todavía no ha sido calibrado contra un conjunto de datos
real, representativo y etiquetado por especialistas.

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
- desempeño de la detección y segmentación;
- acuerdo entre especialistas;
- desempeño por medio, aumento y condición de captura.

La identificación a nivel de género o especie solo debe habilitarse después de
alcanzar criterios de aceptación definidos con microbiología y documentar las
limitaciones del conjunto de datos.

## Separación de responsabilidades

- El motor automático segmenta, mide, aplica la puerta de calidad y genera una categoría preliminar.
- El especialista comprueba las marcas, confirma, corrige, rechaza o marca como no concluyente.
- El administrador gestiona usuarios y, en etapas posteriores, versiones, datasets y evaluaciones.
- La aplicación conserva la trazabilidad de todos esos pasos.
