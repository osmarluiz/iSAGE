# BSB toy example

A minimal reproducibility example for the Software Impacts companion paper.
Runs end-to-end in about **3 minutes on a single GPU** and exercises the
full iSAGE pipeline: seed → train → predict → next iteration.

## What's here

| Path | What |
|---|---|
| `image_train/` | 30 RGB PNG patches (256×256), curated for full 5-class coverage |
| `mask_train/` | dense reference masks (background, car, road, building, permeable area) — used only by the paper-style evaluation, **not** by iSAGE training |
| `sparse_masks_iter0/` | iteration-0 seed annotations (a handful of clicks per class per patch) — the actual input iSAGE consumes |
| `image_val/` | 10 RGB PNG patches for validation |
| `mask_val/` | dense val masks (for computing mIoU) |
| `dataset.yaml` | dataset config pointing to all of the above |
| `training.yaml` | U-Net + EfficientNet-B0 + EWDL (λ=5), 20 epochs — toy convergence only |

Source: subset of the BsB Aerial dataset from
[Carvalho et al. 2022](https://doi.org/10.3390/rs14215489), redistributed
with the authors' permission under the same terms as iSAGE (MIT).

## Run it (terminal)

```bash
python cli.py train \
    --dataset examples/bsb_toy/dataset.yaml \
    --training examples/bsb_toy/training.yaml \
    --session Sessions/bsb_toy_run \
    --iteration 0
```

Expected: a ~3 minute training run, a `Sessions/bsb_toy_run/iteration_0/`
directory with `models/best_model.pth` and `predictions/`, and a new empty
`iteration_1/` ready for the next round of annotation.

Then check progression:

```bash
python cli.py status --session Sessions/bsb_toy_run
```

## Run it (notebook)

Open `isage_workflow.ipynb`, pick `bsb_toy.yaml` as the dataset, pick
`unet_efficientnet_b0_toy.yaml` as the training config (you may need to copy
`examples/bsb_toy/training.yaml` to `configs/training/` first to make it
visible in the dropdown), pick session name `bsb_toy_run`, click
*Setup / Load*, then run the train cell.

## Annotate more iterations

After cell 4 of the notebook (or after `train` in the CLI), open the
annotator on `iteration_1` and add a few clicks where the prediction overlay
gets things wrong:

```bash
python cli.py annotate \
    --dataset examples/bsb_toy/dataset.yaml \
    --training examples/bsb_toy/training.yaml \
    --session Sessions/bsb_toy_run
```

Then re-run `train` to go to `iteration_2`. With only 30 patches the toy
plateaus after about 3 iterations — enough to demonstrate the pattern, not
enough to reach the paper's headline mIoU.

## Why these patches

The 30 patches were selected by scanning the first 300 of the full BsB-256
training set for masks containing all 5 foreground classes (background,
car, road, building, permeable area). Every selected patch contains all
five classes, so iSAGE sees the same class taxonomy at iteration 0 that the
paper used — at 3% of the budget.
