# Diferencial morfológico para arándanos

## Alcance

`MorphologicalDifferentialEngine 0.2.0` convierte mediciones Petri y
microscópicas en un diferencial visual explicable. No identifica ni confirma un
género o una especie y no debe utilizarse como diagnóstico.

Los perfiles iniciales son:

- morfología tipo *Penicillium*;
- morfología tipo *Aspergillus*;
- morfología tipo *Botrytis*;
- morfología tipo *Colletotrichum*;
- morfología tipo *Alternaria*;
- morfología tipo *Fusarium*;
- morfología tipo Mucorales/*Rhizopus*.

Los índices se mantienen por debajo de 0.50. Son compatibilidades heurísticas,
no probabilidades calibradas.

## Por qué se incluyeron estos perfiles

El catálogo prioriza microorganismos documentados en enfermedades o pudriciones
de arándano. La literatura de poscosecha destaca moho gris por *Botrytis*,
antracnosis por *Colletotrichum* y pudriciones asociadas con *Alternaria*, junto
con reportes de *Penicillium*, *Aspergillus* y *Fusarium*. Estudios recientes
identificaron mediante morfología y métodos moleculares aislamientos como
*Penicillium crustosum*, *Aspergillus tubingensis*, *Alternaria alternata* y
*Fusarium verticillioides*.

Los nombres de especies se muestran únicamente como ejemplos publicados en
arándanos. Nunca representan el resultado de la imagen cargada.

## Evidencia por candidato

Cada candidato contiene:

- `display_name`: perfil morfológico;
- `reported_blueberry_examples`: ejemplos reportados en la bibliografía;
- `compatibility_index`: índice heurístico limitado;
- `supporting_evidence`: señales visibles favorables;
- `missing_or_contradictory_evidence`: estructuras ausentes o no demostradas;
- `required_confirmation`: trabajo de laboratorio necesario.

El campo `primary_hypothesis` puede ser `null`. Solo se propone una hipótesis
principal cuando el perfil mejor puntuado supera el umbral conservador y se
separa suficientemente del segundo. La hipótesis continúa sin confirmar.

## Estructuras necesarias

El sistema todavía no reconoce semánticamente:

- penicilos, métulas, fiálides y cadenas conidiales;
- vesículas y cabezas conidiales;
- conidióforos botrioides;
- acérvulos, setas y apresorios;
- conidios muriformes;
- macroconidios, microconidios y clamidosporas;
- esporangios, columelas, rizoides y estolones.

Por ello, un perfil puede orientar dónde mirar, pero no reemplaza la microscopía
experta.

## Metadatos y suficiencia

El diferencial debe interpretarse junto con:

- medio de cultivo;
- temperatura y tiempo de incubación;
- aumento y tipo de microscopio;
- tinción, montaje y preparación;
- lote, origen y fecha de recolección.

La ausencia de estos datos reduce la suficiencia de la interpretación, aunque la
captura sea técnicamente correcta.

## Contratos y seguridad

El diferencial se almacena en:

```text
prediction.feature_summary.taxonomic_differential
```

Se muestra al especialista en el detalle operativo, pero se elimina del
resultado autoritativo, de la curación de datasets y del ground truth. Una
captura rechazada produce `unavailable`; un patrón no filamentoso produce
`insufficient`.

## Confirmación

La identificación final debe combinar cultivo documentado, múltiples campos,
revisión experta e identificación molecular. ITS puede requerir marcadores
secundarios como `BenA`, `CaM`, `TEF1-α`, `RPB2`, `G3PDH` o `HSP60`, según el
grupo y la resolución buscada.

## Referencias principales

- Visagie CM et al. (2014). *Identification and nomenclature of the genus
  Penicillium*. Studies in Mycology 78:343–371. DOI 10.1016/j.simyco.2014.09.001.
- Samson RA et al. (2014). *Phylogeny, identification and nomenclature of the
  genus Aspergillus*. Studies in Mycology 78:141–173. DOI 10.1016/j.simyco.2014.07.004.
- Ramos Bell S. et al. (2021). *Main diseases in postharvest blueberries,
  conventional and eco-friendly control methods: A review*. LWT 149:112046.
  DOI 10.1016/j.lwt.2021.112046.
- Wan C. et al. (2025). *Isolation, Identification and Essential Oil Control of
  Pathogenic Fungi in Postharvest Blueberry*. Food Science 46(9):275–284.
  DOI 10.7506/spkx1002-6630-20241012-066.
- Bollenbacher CB et al. (2026). *Fungal Organisms Associated with Postharvest
  Fruit Rots on Blueberry in Georgia (U.S.A.) Surveyed over Two Growing
  Seasons*. Plant Health Progress 27(2):293–300. DOI 10.1094/PHP-09-25-0228-S.
