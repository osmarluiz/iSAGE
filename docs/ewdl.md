# Error-Weighted Dice Loss (EWDL)

EWDL amplifies the gradient contribution of misclassified pixels relative to
correctly-classified ones. It is the supervision-side counterpart to iSAGE's
annotation strategy: the human clicks confidently-wrong pixels, EWDL weights
those clicks by a factor `λ > 1` until the model gets them right.

When `λ = 1`, EWDL reduces to plain Dice loss.

## Formulation

For predicted probabilities `y_pr(x, c) ∈ [0, 1]` and one-hot ground truth
`y_gt(x, c) ∈ {0, 1}` over labeled pixels `x ∈ S`, per-pixel correctness is:

```
correct(x) = 1   if argmax_c y_pr(x, c) == y_gt(x)
             0   otherwise
```

Per-pixel weight:

```
w(x) = 1   if correct(x) = 1
     = λ   if correct(x) = 0
```

Per-class loss (standard Dice with weights):

```
        L_EWDL^(c) = 1 - (2 Σ_x w(x) · y_gt(x,c) · y_pr(x,c) + ε)
                       / (Σ_x w(x) · (y_gt(x,c) + y_pr(x,c)) + ε)
```

Multiclass loss: average across classes.

```
        L_EWDL = (1/C) Σ_c L_EWDL^(c)
```

Unlabeled pixels (`y_gt = -1`, the `ignore_index`) are excluded from every sum.

## Picking λ

| λ | Behavior |
|---|---|
| 1 | Plain Dice — error and correct pixels weighted equally. |
| 2 | Mild error-emphasis. Useful as a stable warm-start. |
| **5** | Paper default. Best mIoU on BsB multiclass at 5 seeds (74.79 ± std). |
| 10 | Strong error-emphasis. Within noise of λ=5 in the paper's ablation. |
| 20 | Destabilizes — the high penalty starves majority-class learning (72.18 mIoU). |

See Table 3 of the paper for the λ ∈ {1, 2, 5, 10, 20} ablation on BsB
multiclass.

For your own dataset:

- Start with **λ = 5**. It is the value that survives both heavy-foreground
  (BsB cars) and balanced-class (BsB permeable) regimes.
- If the model never converges on hard classes, try **λ = 10**.
- If training oscillates or majority classes regress between iterations, try
  **λ = 2** or lower.
- The ablation in the paper is BsB-only. Vaihingen does not have a published
  λ sweep — adding one to your own dataset is a sensible diagnostic and a
  defensible extension of the paper's analysis.

## Where the code lives

The canonical implementation is in
`segmentation_models_pytorch/utils/losses.py`:

- `EWDLBinary` — binary segmentation.
- `EWDLMulticlass` — multiclass.

Plain reference losses (`DiceLoss`, `FocalLoss`, `CrossEntropyLoss`, `BCELoss`,
`JaccardLoss`, `BCEWithLogitsLoss`) are also in the same file and selectable
from the training YAML's `loss:` section. They are used in the paper's
comparison tables (Table 1 binary, Table 2 multiclass).

## Why not just cross-entropy?

CE with class weights or a focal modulation also amplifies hard examples, but
it operates on the *probability* the network assigns to the correct class
rather than on the *correctness* of the discrete prediction. A pixel with
`p_correct = 0.49` (one tier below the threshold for being "wrong") and a
pixel with `p_correct = 0.51` (one tier above) contribute almost identical
focal weights, even though one will appear as a confident error in the
annotator's overlay and the other will not.

EWDL uses the argmax check, so the binary signal "is this prediction wrong
right now?" maps directly onto the gradient. This is the same signal the
human used when clicking it: the annotator looks at the predicted class on
the overlay, not at probabilities. Loss and annotation share a definition of
"error."
