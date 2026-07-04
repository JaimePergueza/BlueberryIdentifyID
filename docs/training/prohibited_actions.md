# Prohibited Actions

The following actions are prohibited for Fase 30 and remain prohibited for any future manual training attempt unless a later phase explicitly changes the policy.

## Execution And Dependencies

- Do not train in CI.
- Do not train YOLO in this phase.
- Do not execute YOLO in this phase.
- Do not execute `command_preview` directly without later phase authorization and human review.
- Do not install `ultralytics`.
- Do not install `torch`.
- Do not import `torch`.
- Do not use PyTorch.
- Do not use TensorFlow.
- Do not implement CNN, ViT, or deep learning real code.
- Do not require GPU for this repository phase.

## Artifacts

- Do not upload weights to Git.
- Do not store weights in the repository.
- Do not store weights in DB.
- Do not store model binaries in DB.
- Do not create `.pt`, `.onnx`, `.h5`, `.pth`, `.ckpt`, or similar model files in the repository.
- Do not ignore artifact policy.
- Do not ignore repository safety.
- Do not download weights without an approved policy.
- Do not upload large generated predictions or run directories to Git.

## Data And Labels

- Do not modify original images.
- Do not copy images into the repository as training artifacts.
- Do not change labels after the quality gate without creating a new bundle.
- Do not mix external datasets without formal evaluation.
- Do not download external datasets.
- Do not use taxonomic categories.
- Do not add microbiological genus or species labels.
- Do not claim microbiological diagnosis.

## Product Boundaries

- Do not replace `MockInferenceEngine` without a specific future phase.
- Do not implement frontend.
- Do not implement authentication.
- Do not change the product focus away from blueberry samples, Petri dish images, and microscopy images.
