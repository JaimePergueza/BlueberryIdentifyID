# Motor morfológico explicable 0.5.0

## Propósito

`PreliminaryTwoImageEngine 0.5.0` combina una fotografía macroscópica de caja
Petri con una imagen microscópica del mismo aislamiento. Produce categorías
visuales amplias, mediciones verificables y una interpretación orientativa. No
confirma género, especie, patogenicidad ni diagnóstico.

Cada predicción automática es inmutable y requiere revisión humana. Los
resultados antiguos conservan la versión exacta con la que fueron generados.

## Metadatos estructurados

El flujo de nuevo análisis registra por separado:

- código de muestra, lote, origen y fecha de recolección;
- observaciones de la muestra;
- medio, temperatura y tiempo de incubación;
- aumento, tipo de microscopio, tinción o medio de montaje;
- método de preparación microscópica;
- imagen Petri e imagen microscópica del mismo aislamiento.

Estos campos no son decorativos. La morfología colonial depende del medio, la
temperatura y la edad del cultivo; la interpretación microscópica depende del
aumento, la óptica y la preparación.

## Categorías generales

- `no_evident_growth`: no se observa crecimiento candidato suficiente;
- `suspicious_growth`: existe crecimiento, pero falta soporte microscópico;
- `probable_fungal_growth`: patrón amplio compatible con crecimiento filamentoso;
- `probable_bacterial_growth`: patrón celular no filamentoso compatible;
- `inconclusive`: calidad insuficiente, evidencia ambigua o conflicto entre motores.

Las cifras asociadas se denominan **puntuaciones heurísticas**. No son
probabilidades calibradas.

## Segmentación y evidencia

### Caja Petri

El motor intenta aislar la placa, excluir el borde y medir regiones candidatas,
cobertura, color, textura, circularidad, irregularidad, intensidad, crecimiento
confluente y conflictos de segmentación.

### Microscopía

El motor intenta aislar el campo y mide densidad de bordes, cobertura
filamentosa, esqueleto, ramificación, componentes alargados, componentes
redondeados, cantidad de estructuras, nitidez y cobertura analizada.

Las superposiciones muestran qué procesó el algoritmo. No constituyen
anotaciones expertas ni ground truth.

## Cuatro dimensiones de calidad

La versión 0.5.0 separa:

1. **calidad técnica de captura**: archivo válido, exposición, enfoque y campo;
2. **calidad de segmentación**: placa/campo aislados y ausencia de contradicción;
3. **suficiencia morfológica**: cantidad de evidencia interpretable;
4. **suficiencia de metadatos**: completitud de condiciones experimentales.

Una captura técnicamente aceptada puede seguir siendo insuficiente para una
hipótesis morfológica o taxonómica.

## Coherencia entre motores

`AnalysisCoherenceResolver 0.1.0` compara la categoría general, la fusión
macro/micro y el diferencial morfológico antes de guardar la predicción.

Cuando la clasificación general favorece un patrón bacteriano, pero existe
crecimiento macroscópico y evidencia filamentosa sustancial, el sistema no
presenta ambas conclusiones como si fueran compatibles. Se abstiene y devuelve:

- categoría automática `inconclusive`;
- explicación del conflicto;
- posibilidad de señal mixta o segmentación insuficiente;
- revisión de varios campos y confirmación adicional.

Esta resolución automática apoya al especialista, pero se excluye del ground
truth y de los datos de entrenamiento.

## Diferencial morfológico para arándanos

`MorphologicalDifferentialEngine 0.2.0` compara perfiles amplios asociados con
arándanos:

- morfología tipo `Penicillium`;
- morfología tipo `Aspergillus`;
- morfología tipo `Botrytis`;
- morfología tipo `Colletotrichum`;
- morfología tipo `Alternaria`;
- morfología tipo `Fusarium`;
- morfología tipo Mucorales/`Rhizopus`.

Cada perfil incluye:

- rasgos visuales que lo apoyan;
- rasgos ausentes o contradictorios;
- ejemplos reportados en arándanos;
- método recomendado para confirmación.

Los índices permanecen por debajo de 50 %, porque todavía no existe un detector
semántico validado de conidióforos, fiálides, vesículas, acérvulos, macroconidios,
esporangios u otras estructuras diagnósticas. Los nombres son hipótesis de
compatibilidad, no identificaciones.

## Frontera de seguridad y datasets

Los campos `taxonomic_differential` y `coherence_assessment` aparecen en la vista
operativa del especialista, pero se eliminan de:

- `final-result`, cuyo resultado autoritativo depende de la revisión humana;
- features curadas para entrenamiento;
- ground truth;
- etiquetas confirmadas de género o especie.

Solo las mediciones visuales reutilizables pueden incorporarse a datasets. Las
particiones deben hacerse por aislamiento o evento biológico, no por fotografía,
para evitar fuga entre entrenamiento y prueba.

## Confirmación microbiológica

La identificación final debe integrar:

- cultivo en condiciones documentadas;
- varios campos microscópicos maduros;
- aislamiento puro cuando sea necesario;
- revisión experta;
- ITS y marcadores secundarios apropiados al grupo;
- pruebas de patogenicidad cuando la pregunta científica lo requiera.

## Base bibliográfica del catálogo inicial

- Ramos Bell S., Hernández Montiel L. G., González Estrada R. R. y Gutiérrez
  Martínez P. *Main diseases in postharvest blueberries, conventional and
  eco-friendly control methods: A review*. LWT 149 (2021), 112046.
  DOI: 10.1016/j.lwt.2021.112046.
- Wan C. et al. *Isolation, Identification and Essential Oil Control of
  Pathogenic Fungi in Postharvest Blueberry*. Food Science 46(9) (2025),
  275–284. DOI: 10.7506/spkx1002-6630-20241012-066.
- Bollenbacher C. B. et al. *Fungal Organisms Associated with Postharvest Fruit
  Rots on Blueberry in Georgia (U.S.A.) Surveyed over Two Growing Seasons*.
  Plant Health Progress 27(2) (2026), 293–300.
  DOI: 10.1094/PHP-09-25-0228-S.
- *Storability evaluation of ‘Eureka’ blueberry under different temperatures
  and characterization of postharvest pathogenic fungi*. Scientia
  Horticulturae 363 (2026), 114925. DOI: 10.1016/j.scienta.2026.114925.

Estas referencias justifican qué perfiles incluir primero; no validan por sí
solas las reglas heurísticas ni autorizan una identificación visual automática.
