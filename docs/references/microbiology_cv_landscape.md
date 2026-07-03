# Microbiology Computer Vision Landscape Review

Phase 18 technical-scientific review for BlueberryMicroID.

This document is a decision map for future phases. It does not integrate
external code, download external datasets, train models, add dependencies,
change production logic, create migrations, or replace `MockInferenceEngine`.

## Scope And Guardrails

BlueberryMicroID currently works with two images for the same blueberry sample:

- Petri image: a photograph of the Petri dish where microbial growth is
  observed. It is not a fruit-quality image.
- Micro image: a microscopy photograph from the same sample.

Current labels are broad preliminary visual categories only. This review does
not add genus/species identification, taxonomy, diagnostic claims, PyTorch,
TensorFlow, YOLO, CNN, ViT, MLflow, TensorBoard, W&B, frontend, authentication,
external datasets, or real AI inference.

## Source Notes

Primary or near-primary sources consulted:

- Ultralytics YOLOv5 repository: https://github.com/ultralytics/yolov5
- AGAR dataset paper and project pages for microbial colony detection:
  https://arxiv.org/abs/2108.01234 and https://agar.neurosys.com/
- MEMTrack official repository: https://github.com/talbenha/memtrack
- DIBaS publication entry for Digital Images of Bacteria Species:
  https://doi.org/10.1016/j.biosystems.2017.08.001
- Reviews and survey-style references on microorganism image analysis and
  deep learning are used only as conceptual roadmap input, not as adopted
  implementation.

Two names provided for review, "CSI-Microbes Identification" and "SinfNet",
could not be tied to a single clearly authoritative primary source from the
available public search results during this phase. They are therefore treated
as unresolved references: useful search leads, but not adoption candidates
until a repository, paper, license, and dataset provenance are verified.

## Landscape Classification

| Reference | Data type | Macro Petri | Micro image | Video/tracking | Uses deep learning | Requires external dataset | Compatibility | Main risk | Recommended use |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| CSI-Microbes Identification, unresolved source | Unknown until source is verified | partial | partial | unknown | unknown | unknown | low | No verified primary source, license, data schema, or domain proof | Track as lead only; do not adopt now |
| Bacteria detection with YOLOv5-style pipelines | Object detection images with bounding boxes | partial | partial | no | yes | yes, unless BlueberryMicroID creates boxes | low now, medium later | Requires bounding-box labels, PyTorch, YOLO dependency stack, and domain-specific evaluation | Conceptual reference for future colony/object detection only |
| MEMTrack | Microscopy video or frame sequences for cell tracking | no | partial | yes | likely method-specific, external implementation | yes or external videos | low for current scope | Current product uses static Petri/micro images, not time-lapse tracking | Reference only until video microscopy is in scope |
| SinfNet, unresolved source | Unverified; likely image dataset/model reference if identified later | no | partial | unknown | unknown | likely yes | low | Source ambiguity and external-domain mismatch | Do not adopt until source/license/domain are verified |
| DIBaS | Microscopy images of bacterial species | no | partial | no | no by itself; models may use DL | yes | medium as benchmark, low as training mix-in | Clinical/lab species domain differs from blueberry sample workflow; taxonomy/species labels are outside current scope | Use only as external-domain benchmark or literature reference, not mixed into own dataset |
| Surveys/reviews on microorganism detection | Papers/reviews | partial | partial | partial | often yes | no direct dataset required | medium | Survey conclusions can overgeneralize across acquisition domains | Roadmap input; not implementation authority |
| Petri colony detection datasets/papers such as AGAR | Petri dish colony images, annotations/counts | yes | no | no | sometimes yes | yes | medium later | Domain, media, lighting, colony morphology, and labels differ from BlueberryMicroID; object annotations required | Strong conceptual reference for Phase 19 classical segmentation/counting and later box annotation design |
| Clinical bacterial image datasets | Microscopy or culture images from clinical workflows | partial | partial | partial | varies | yes | low to medium as benchmark | Clinical domain shift, different sample preparation, labels, acquisition devices, and regulatory assumptions | Literature/benchmark only; never merge directly into curated blueberry dataset |

## Reference Assessments

### CSI-Microbes Identification

Status: unresolved reference.

The name suggests a microorganism identification project, but Phase 18 did not
resolve a single authoritative repository, paper, dataset landing page, license,
or reproducible data schema. Because BlueberryMicroID must not copy external
code or import external datasets without provenance, this source cannot be an
adoption candidate yet.

Potential compatibility is unknown. It may be relevant to microscopy,
classification, or combined visual workflows, but that remains speculative. A
future phase may revisit it only after verifying: official URL, authorship,
license, data type, labels, acquisition protocol, and whether it claims
taxonomy that conflicts with the current broad-label scope.

Recommendation: no adoption now; keep as a search lead.

### Bacteria Detection With YOLOv5

YOLOv5 is an object-detection framework from Ultralytics. It is useful when the
task is to locate objects with bounding boxes, such as colonies, cells, or
regions of interest. It is not a natural fit for the current BlueberryMicroID
state because the curated dataset stores reviewed run-level labels, not
bounding boxes or instance masks.

For Petri images, YOLO-style detection could become useful if the project later
collects colony-level box annotations. For microscopy images, it could become
useful only if the target becomes localizing visible structures rather than
classifying a whole reviewed sample.

Risks:

- Requires PyTorch/YOLO and a deep-learning stack, which is explicitly out of
  scope now.
- Requires object-level labels; current `DatasetItem` and `DatasetRelease`
  labels are sample-level.
- Could encourage overclaiming if trained on external bacteria data that does
  not match blueberry Petri conditions.

Recommendation: conceptual reference only for future object detection. Do not
adopt before a bounding-box annotation phase exists.

### MEMTrack

MEMTrack is a microscopy tracking project centered on motion over time. Its
main relevance is video or sequential microscopy analysis, not static single
image classification.

BlueberryMicroID currently stores one Petri image and one microscopy image per
analysis run. It has no video upload model, no frame sequence entity, no
tracking annotations, and no temporal ground truth. Adding MEMTrack ideas now
would widen scope into a different data modality.

Recommendation: not compatible for the current MVP. Keep as a conceptual
reference if a future phase introduces time-lapse microscopy.

### SinfNet

Status: unresolved reference.

The provided name did not resolve to a verified primary source during this
phase. It may refer to a network, dataset, or paper, but without an official
source this project should not rely on it.

Recommendation: no adoption. Re-review only if an official paper/repository
and license are supplied.

### DIBaS

DIBaS, Digital Images of Bacteria Species, is a microscopy image dataset used
in bacterial species classification research. It is relevant as a known
micro-image reference, but it is not a drop-in training source for
BlueberryMicroID.

Compatibility:

- Micro image: partial, because it contains microscopy images.
- Petri image: no, because it is not a Petri dish colony dataset.
- Labels: species-oriented, which conflicts with the current no-taxonomy scope.

Risks:

- Mixing DIBaS with BlueberryMicroID curated data could create domain shift:
  different sample preparation, microscope settings, organisms, label schema,
  and acquisition conditions.
- Species labels could push the product toward taxonomy claims that the current
  system must not make.

Recommendation: use only as literature context, external-domain benchmark, or
possible pretraining reference in a future approved deep-learning phase. Do not
merge into the curated dataset.

### Surveys And Scientific Reviews

Survey papers are useful for understanding the field's movement from classical
image processing to deep learning, including segmentation, detection,
classification, and tracking. They are not implementation specs.

Implications for the roadmap:

- Classical segmentation/counting remains valuable when data is small and
  annotations are weak.
- Deep learning becomes reasonable only after strong data governance exists:
  reviewed labels, split leakage controls, image audit, feature extraction,
  baseline comparisons, and enough examples.
- Different acquisition domains should be treated as separate evaluation
  domains unless proven otherwise.

Recommendation: use surveys as roadmap input, not as authority to add
dependencies or models.

### Petri Colony Detection

Petri colony detection work, including datasets such as AGAR, is the strongest
near-term conceptual fit for BlueberryMicroID's macro Petri branch. These
sources focus on colony visibility, detection, counting, and sometimes
segmentation on plate images.

Immediate adoption should still be classical and modest: thresholding,
connected components, simple morphology, and technical count estimates as
experimental features. YOLO-style detection should wait until BlueberryMicroID
has its own box or mask annotations.

Recommendation: strongest input for Phase 19, but adopt ideas, not code or
datasets.

### Clinical Bacterial Datasets

Clinical bacterial datasets can be useful for understanding acquisition
protocols and evaluation pitfalls. They are risky as training data for a
blueberry-centered workflow because the domain, preparation, labels, and
regulatory expectations differ.

Recommendation: benchmark or literature reference only. Never merge directly
into BlueberryMicroID curated training data without a documented domain study.

## Adoption Matrix

| Category | Sources | Justification |
|---|---|---|
| Adopt now | None as code/model/data | Phase 18 is documentation only; current dataset is not sufficient for deep learning or object detection adoption |
| Adopt later | Petri colony detection concepts; possibly YOLO-style detection after annotations; DIBaS as benchmark/pretraining reference only after domain controls | Useful directions, but each requires either annotations, domain validation, or a future approved model phase |
| Conceptual reference only | Surveys/reviews; MEMTrack; clinical bacterial datasets | Helpful for roadmap and risk framing, but not directly compatible with current static sample-level workflow |
| Not compatible now | CSI-Microbes unresolved; SinfNet unresolved; YOLOv5 implementation; direct DIBaS/SinfNet dataset mixing | Missing provenance, wrong modality, deep-learning dependency, missing annotations, or domain/taxonomy conflict |

## Technical Roadmap After Phase 18

### A. Macro Petri

Recommended near-term direction:

1. Classical Petri colony segmentation prototype.
2. Connected-component or contour-style candidate detection.
3. Approximate colony count and simple shape/area distributions.
4. Persist outputs only after a later phase defines entities and validation.
5. Consider YOLO only after the project has its own bounding boxes or masks.

Why classical first: it can be tested on current Petri images, requires no deep
learning, creates interpretable diagnostics, and helps determine whether object
annotations are worth collecting.

### B. Micro

Recommended direction:

1. Continue whole-image feature classification experiments.
2. Add simple segmentation only if expert review says visible structures are
   meaningful and consistently captured.
3. Use deep learning only after the curated dataset is large enough and split
   leakage controls are stable.

### C. External Datasets

External datasets should be used only for:

- literature comparison;
- benchmark experiments kept separate from BlueberryMicroID training data;
- possible pretraining in a future explicitly approved phase.

They should not be merged into the curated dataset without domain evaluation,
label mapping review, licensing review, and clear split isolation.

### D. Deep Models

Do not introduce deep learning until all of the following are true:

- enough own reviewed data exists;
- `HumanReview` final labels are available;
- train/validation/test splits are grouped by sample/lot/origin as needed;
- image audit is not failed;
- feature extraction has run;
- classical baselines have been compared;
- a phase explicitly approves PyTorch/TensorFlow/YOLO/CNN/ViT work.

## Recommended Phase 19

Recommended next phase:

**Phase 19 - Macro Petri classical colony segmentation prototype**

Objective:

- Explore whether Petri dish images can produce simple, reproducible,
  non-deep colony candidate features.

Inputs:

- Existing Petri image paths from `DatasetRelease` manifests.
- Existing image audit status.
- Optional existing feature extraction outputs for context.

Outputs:

- A prototype report or persisted technical summary, depending on the approved
  Phase 19 scope.
- Candidate colony count, area distribution, and segmentation quality warnings.
- No taxonomic labels and no diagnostic claim.

Restrictions:

- No PyTorch, TensorFlow, YOLO, CNN, ViT, or deep learning.
- No external dataset download.
- No species/genus labels.
- No replacement of `MockInferenceEngine`.
- No business prediction path change.

Why this comes before YOLO/deep learning:

- Current data has sample-level labels, not bounding boxes.
- Classical segmentation can reveal whether Petri acquisition quality supports
  any object-level work.
- The output can guide future annotation design before committing to a deep
  object detector.

## Phase 18 Decision Summary

No external project should be adopted into production now. The strongest next
technical move is a constrained classical Petri colony segmentation prototype,
because it aligns with current data, avoids new deep-learning dependencies, and
can inform whether future object annotations are justified.
