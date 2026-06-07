# `segmentation_models_pytorch` modifications

This repository ships a vendored, modified copy of
[`segmentation_models.pytorch`](https://github.com/qubvel/segmentation_models.pytorch)
(commonly imported as `smp`). The upstream library is excellent and unchanged
for everything related to encoders, decoders, and architectures. The
modifications are confined to loss functions and a few utility tweaks needed
to wire those losses into the training loop.

**Do not `pip install segmentation-models-pytorch` separately.** The local
copy at `/segmentation_models_pytorch` is the one the workflow uses, and the
PyPI release does not contain EWDL or the other custom losses.

## Added losses

All additions live in `segmentation_models_pytorch/utils/losses.py`:

| Class | Purpose | Used by the paper |
|---|---|---|
| `EWDLBinary` | Error-Weighted Dice Loss, binary segmentation | Yes (Table 1, binary tasks) |
| `EWDLMulticlass` | Error-Weighted Dice Loss, multiclass | Yes (Table 2, multiclass; Table 5, Vaihingen) |

`DiceLoss`, `FocalLoss`, `CrossEntropyLoss`, `BCELoss`, `JaccardLoss`,
`BCEWithLogitsLoss`, `L1Loss`, `MSELoss`, `NLLLoss`, and the other standard
upstream losses are unchanged.

## Other tweaks

- **`utils/data_loader.py`**: helper for treating an `ignore_index` value as
  unsupervised during loss computation. Required because sparse supervision
  needs gradient zeroing at unlabeled pixels — the upstream Dice loss does not
  support this directly.
- **`utils/metrics.py`**: per-class IoU with `ignore_index` support, used for
  Vaihingen's clutter-excluded protocol.

No upstream source files were deleted. The architectures, encoders, decoders,
and metrics behave identically to the corresponding upstream release.

## Diff against upstream

If you want to see exactly what changed, a clean diff against upstream is:

```bash
git clone https://github.com/qubvel/segmentation_models.pytorch.git /tmp/smp_upstream
diff -r /tmp/smp_upstream/segmentation_models_pytorch ./segmentation_models_pytorch
```

The expected differences are the additions listed above. If you see deletions
or modifications outside `utils/`, please open an issue — those would not be
intentional.

## License

Upstream `segmentation_models.pytorch` is MIT-licensed. The modifications in
this repository are also MIT — see `LICENSE` at the repo root. The upstream
copyright and license file in
`segmentation_models_pytorch/LICENSE` are preserved.
