# Bring your own trainer

iSAGE separates *what gets stored on disk* (the session directory) from
*what trains the model* (the trainer). The session directory is the
contract; the trainer is the variable part. This document explains how to
plug in a custom trainer when the default does not fit.

## The mental model

```
                                                  (you can swap this)
                                                          |
                                                          v
   +-----------+      +-----------+      +----------+   +---------+
   | Annotator |----->| Session   |<-----| Trainer  |-->| Models  |
   |  (JSON)   |      | directory |      |          |   | & preds |
   +-----------+      +-----------+      +----------+   +---------+
                          ^                   |
                          |                   v
                          +-------------------+
                          (reads masks, writes
                           models + predictions)
```

Three modules:

1. **Trainer** -- pluggable. Default is :class:`SmpTrainer`
   (U-Net family from ``segmentation_models.pytorch`` plus the
   Error-Weighted Dice Loss). Any framework that respects the contract
   below can replace it.
2. **Annotator** -- the iSAGE PyQt5 widget, which writes the canonical
   JSON record. You can substitute it only if your replacement produces
   the same JSON schema. The annotator is what makes iSAGE specific.
3. **Session organization** -- fixed on-disk layout. Not pluggable; the
   layout *is* the contract.

The annotator and the session organization stay fixed because they are
what makes iSAGE iSAGE. Everything else is your choice.

## The Trainer contract

A trainer is any object with one method:

```python
def train_one_iteration(
    self,
    *,
    session_path: Path,
    dataset_config: dict,
    iteration: int | str = "latest",
    visualize: bool = False,
) -> dict:
    ...
```

The method must:

1. **Read masks.** Consume the PNG mask files under
   `session_path / f"iteration_{iteration}" / "masks"`. Each pixel is a
   class index in `[0, num_classes-1]` or the `ignore_index` value from
   `dataset_config['classes']['ignore_index']`.

2. **Write a model checkpoint.** Save the trained state to
   `session_path / f"iteration_{iteration}" / "models" / "best_model.pth"`.
   Format is implementation-defined.

3. **Write predictions.** Save one PNG per training image to
   `session_path / f"iteration_{iteration}" / "predictions"`. Each pixel
   value is a predicted class index. These power the prediction overlay
   on the next iteration's annotator.

4. **Advance the iteration.** Create
   `session_path / f"iteration_{iteration+1}"` with the four
   subdirectories (`annotations`, `masks`, `models`, `predictions`) and
   copy the current iteration's annotation JSONs into the new
   `annotations/`.

Optional:

5. Append one row to `session_path / "metrics_history.csv"` with the
   iteration's metrics. See the example trainer for the column
   convention.

The protocol is declared as
[`src.training.trainer_protocol.Trainer`](../src/training/trainer_protocol.py).
Python's `@runtime_checkable` lets you `isinstance(your_trainer, Trainer)`
for quick verification.

## How to plug it in

```python
from src.workflow import Workflow
from my_trainers import MyCustomTrainer

wf = Workflow.from_config(
    dataset='configs/datasets/my.yaml',
    training='configs/training/my.yaml',
    session='Sessions/my_run',
    trainer=MyCustomTrainer(),     # <-- swap here
)

wf.annotate()  # same as always: opens the PyQt5 annotator
wf.train()     # delegates to your trainer.train_one_iteration
```

Everything else stays the same. The notebook widget, the CLI, the session
inspection, and the annotator are oblivious to which trainer you use.

## Minimal working example

A complete custom trainer in roughly 80 lines lives at
[`examples/byot/example_trainer.py`](../examples/byot/example_trainer.py).
It uses raw PyTorch (no ``segmentation_models.pytorch`` dependency), reads
the masks the iSAGE convention specifies, trains a small U-Net for a few
epochs, and writes the expected outputs. Drop it next to your training
script as a template and adapt to your framework of choice.

## Why might you want this?

- **Different model family.** You have your own architecture (a U-Net
  variant, a transformer, an attention module) that the
  ``segmentation_models.pytorch`` zoo does not cover.
- **Different framework.** You already maintain training scripts in
  PyTorch Lightning, monai, fastai, MMSegmentation, JAX, or even something
  non-Python invoked via subprocess.
- **Different loss strategy.** EWDL is the supervision contract the
  methods paper recommends; you may want to ablate it, replace it, or
  combine it with auxiliary terms.
- **Hyperparameter sweeps.** Wrapping a different optimizer, scheduler,
  or augmentation pipeline becomes a one-class change instead of an edit
  through the platform internals.

## What the default trainer does

For reference, the default :class:`SmpTrainer` (the implementation that
ships with iSAGE and powers every experiment in the methods paper) does:

1. Build a U-Net or other architecture from
   ``segmentation_models.pytorch`` using the YAML at
   ``configs/training/<name>.yaml``.
2. Wrap it with the Error-Weighted Dice Loss (or any loss configured in
   the YAML's ``loss.train.name`` field).
3. Train for the configured number of epochs against the sparse mask
   supervision in ``iteration_N/masks/``.
4. Save the best-by-val-mIoU checkpoint (or final-epoch checkpoint when
   no validation set is configured) to ``iteration_N/models/best_model.pth``.
5. Run inference on the full training set and write predictions to
   ``iteration_N/predictions/``.
6. Create ``iteration_{N+1}/`` with copied annotations.
7. Append a row to ``metrics_history.csv``.

Custom trainers are free to do these in any order, parallelism, or
implementation; only the outputs must match.

## Limitations of pluggability

- The default annotator reads ``iteration_N/predictions/`` to show the
  overlay. Predictions must be PNGs of the same dimensions as the training
  images and the same class indexing as the annotator (the YAML's
  ``classes.names`` order). A custom trainer that writes one-hot tensors
  or saved logits will not display correctly without conversion.
- Metrics history is optional but recommended -- the notebook's
  ``Workflow.plot_progression()`` reads it. Without the CSV, the
  per-iteration chart is blank.
- The annotator and the session organization are not pluggable. Replacing
  the annotator is theoretically possible if your replacement writes
  JSONs in the documented schema (see [json-record-spec.md](json-record-spec.md)),
  but no example of that is shipped.
