# Morphological taxonomic differential

## Scope

`MorphologicalDifferentialEngine 0.1.0` converts the existing Petri and
microscopy measurements into a limited, explainable differential. It does not
identify a genus or species and must not be used as a diagnosis.

The first supported genus-like profiles are:

- morphology compatible with *Penicillium*;
- morphology compatible with *Aspergillus*;
- broad interpretation as another filamentous fungus when genus-like evidence
  cannot be separated.

Genus-like compatibility indices are capped below 0.50. They are heuristic
indices, not calibrated probabilities.

## Scientific basis

The profile vocabulary follows the polyphasic identification guidance in:

- Visagie CM et al. (2014), **Identification and nomenclature of the genus
  Penicillium**, Studies in Mycology 78:343–371,
  DOI `10.1016/j.simyco.2014.09.001`.
- Samson RA et al. (2014), **Phylogeny, identification and nomenclature of the
  genus Aspergillus**, Studies in Mycology 78:141–173,
  DOI `10.1016/j.simyco.2014.07.004`.
- Schoch CL et al. (2012), **Nuclear ribosomal internal transcribed spacer (ITS)
  region as a universal DNA barcode marker for Fungi**, PNAS 109:6241–6246,
  DOI `10.1073/pnas.1117018109`.

These sources treat colony characters and conidiophore morphology as important
but insufficient on their own for species assignment. The application
therefore reports missing diagnostic structures and recommends molecular
confirmation.

## Penicillium-like profile

Supporting measurements may include:

- visible filamentous growth;
- grey-green or blue-green colony colour;
- heterogeneous colony texture;
- elongated and branching microscopic structures.

The profile remains unconfirmed until microscopy demonstrates the relevant
conidiophore architecture, such as phialides, metulae and conidial chains.
Branching patterns can be monoverticillate, divaricate, biverticillate,
terverticillate or more complex. ITS alone may be insufficient for species
resolution; a secondary marker such as `BenA` is commonly required.

## Aspergillus-like profile

Supporting measurements may include:

- visible filamentous growth;
- elongated and branching microscopic structures;
- candidate rounded structures that warrant review.

The profile remains unconfirmed until a terminal vesicle and an interpretable
conidial head are demonstrated. The reviewer must determine whether phialides
are uniseriate or biseriate and assess stipe, vesicle, metula, phialide and
conidial morphology. Molecular confirmation commonly combines ITS with an
appropriate secondary marker such as `CaM` or `BenA`.

## Output contract

The differential is stored under:

```text
prediction.feature_summary.taxonomic_differential
```

Important fields:

- `engine.name` and `engine.version`;
- `status`: `available`, `insufficient` or `unavailable`;
- `summary`;
- `morphological_description`;
- `broad_interpretation`;
- `primary_hypothesis`, which may be `null`;
- `candidates` with supporting, missing and confirmation evidence;
- `score_semantics`, `limitations` and `confirmation_required`.

A rejected quality gate always produces `unavailable` with no genus-like
candidates. A non-filamentous result produces `insufficient`. Existing
predictions remain immutable and do not acquire the differential
retrospectively.

## Known limitations

The current visual extractors do not semantically detect conidiophores,
vesicles, metulae, phialides or conidial chains. Consequently, the differential
is an educational and review-support layer over generic morphology metrics.
The next scientific milestone is a curated isolation-level dataset containing
paired Petri images, multiple microscopy fields, standardised culture metadata,
expert annotations and molecular ground truth.
