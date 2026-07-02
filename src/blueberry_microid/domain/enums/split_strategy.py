from enum import Enum


class SplitStrategy(str, Enum):
    """How `DatasetSplitter` groups `DatasetItem`s before assigning splits.

    Each strategy is a different, progressively stricter leakage-prevention
    unit — never a fallback for one another. A request for a stricter
    strategy must fail loudly (see `DatasetSplitMetadataError`) rather than
    silently degrade to a weaker one, because that would hide a real
    data-leakage risk instead of surfacing it.

    - `BY_SAMPLE`: groups by `Sample.id`. The baseline: no image/item of the
      same Sample can be split across train/validation/test.
    - `BY_LOT`: groups by `Sample.lot_code`. Stricter than `BY_SAMPLE` — every
      Sample from the same production/collection lot lands in the same
      split, so a model cannot learn lot-specific conditions (culture medium
      batch, capture protocol, incubator, shared contamination) as a proxy
      for a real microbiological pattern. Requires every relevant Sample to
      have a non-empty `lot_code`.
    - `BY_ORIGIN_LOT`: groups by `(Sample.origin, Sample.lot_code)`. The
      strictest option — also prevents leakage across samples that share a
      lot code but come from different origins from being treated as the
      same group, and vice versa. Requires every relevant Sample to have
      both `origin` and `lot_code`.
    """

    BY_SAMPLE = "by_sample"
    BY_LOT = "by_lot"
    BY_ORIGIN_LOT = "by_origin_lot"
