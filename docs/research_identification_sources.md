# Fuentes para identificación morfológica y construcción del clasificador

Este documento registra las fuentes técnicas que orientan la siguiente fase de
BlueberryMicroID. El objetivo es separar con claridad tres niveles:

1. medición visual reproducible;
2. clasificación morfológica preliminar;
3. identificación taxonómica validada.

## Manuales de micología

- Crous, Verkley, Groenewald y Houbraken (eds.), *Fungal Biodiversity*,
  Westerdijk Laboratory Manual Series, 2019. Manual general para aislamiento,
  cultivo, estudio morfológico y molecular de hongos.
- Samson, Houbraken, Thrane, Frisvad y Andersen, *Food and Indoor Fungi*,
  Westerdijk Laboratory Manual Series, 2.ª ed., 2019. Referencia para combinar
  caracteres de colonia, microscopía y datos de cultivo.
- Leslie y Summerell, *The Fusarium Laboratory Manual*, 2006. Ejemplo de
  identificación que integra caracteres morfológicos, cultivo y evidencia
  molecular dentro de un género complejo.

## Identificación molecular

- Schoch et al. (2012) propusieron la región ITS como código de barras primario
  de hongos. ITS no resuelve por sí sola todos los grupos, por lo que algunos
  taxones necesitan marcadores suplementarios.
- UNITE mantiene secuencias ITS y Species Hypotheses para identificación y
  comunicación taxonómica reproducible.

## Bioimagen y segmentación

- OpenCV y scikit-image proporcionan detección de círculos, contornos,
  watershed, propiedades de regiones, morfología y esqueletización.
- CellProfiler ofrece flujos reproducibles para identificar objetos y medir
  tamaño, forma, intensidad y textura.
- ilastik permite clasificación interactiva de píxeles y objetos y exporta
  mapas de probabilidad, segmentaciones e incertidumbre.
- CVAT y Segment Anything pueden acelerar la anotación de máscaras, pero las
  máscaras deben revisarse por una persona y no constituyen etiquetas
  taxonómicas.

## Datasets y trabajos comparables

- DIFaS/OpenFungi muestran que es posible entrenar clasificadores de imágenes
  fúngicas cuando existe una colección curada con etiquetas expertas.
- Los resultados publicados no son directamente transferibles a arándanos:
  cambian organismos, preparación, microscopio, medio, cámara y dominio de
  captura. Los datasets externos se usarán para prototipos y comparación, no
  como ground truth del laboratorio local.

## Decisión para BlueberryMicroID

La plataforma avanzará de forma jerárquica:

1. control de calidad y segmentación visible;
2. categorías amplias (sin crecimiento, filamentoso, celular, no concluyente);
3. dataset pareado y revisado por aislamiento;
4. etiquetas confirmadas mediante el procedimiento microbiológico definido;
5. entrenamiento por grupo/género y, solo cuando los datos lo permitan, por
   especie.

La partición de datos se realizará por aislamiento o muestra, nunca separando
fotografías del mismo aislamiento entre entrenamiento y prueba.
