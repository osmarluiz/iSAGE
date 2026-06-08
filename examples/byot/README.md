# Bring-your-own-trainer example

iSAGE separates *what gets stored on disk* (the session directory, fixed)
from *what trains the model* (the trainer, pluggable). The default trainer
that ships with iSAGE is `SmpTrainer` -- a U-Net family from
`segmentation_models.pytorch` plus the Error-Weighted Dice Loss. This
directory shows how to substitute it with your own.

## Why might you want this?

- You already have a training script in a different framework
  (PyTorch Lightning, monai, fastai, MMSegmentation, JAX, plain PyTorch).
- You want to use a model architecture that is not in
  `segmentation_models.pytorch`.
- You want to ablate or replace EWDL with a different loss strategy.

The annotator, the JSON record format, and the session directory layout
stay the same. Only the training step changes.

## The example

[`example_trainer.py`](example_trainer.py) implements a `TinyTorchTrainer`
class that respects the Trainer protocol. It uses raw PyTorch (no
`segmentation_models.pytorch`) and a small ad-hoc U-Net, so the file
stands on its own. Adapt it to your framework of choice -- the structure
of the `train_one_iteration` method is the template.

## Run it

```python
from src.workflow import Workflow
from examples.byot.example_trainer import TinyTorchTrainer

wf = Workflow.from_config(
    dataset='configs/datasets/my.yaml',
    training='configs/training/unet_efficientnet_b7.yaml',  # only num_classes is read
    session='Sessions/byot_run',
    trainer=TinyTorchTrainer(num_epochs=5, lr=1e-3),
)

wf.annotate()  # the iSAGE PyQt5 annotator opens, unchanged
wf.train()     # your trainer runs in place of SmpTrainer
```

Everything else (notebook widget, CLI, session inspection, plot
progression) keeps working transparently.

## The contract you need to respect

A trainer is any object with one method:

```python
def train_one_iteration(self, *, session_path, dataset_config, iteration, visualize=False) -> dict:
    # 1. Read masks from session_path / f"iteration_{iteration}" / "masks"
    # 2. Write best_model.pth to session_path / f"iteration_{iteration}" / "models"
    # 3. Write per-image prediction PNGs to session_path / f"iteration_{iteration}" / "predictions"
    # 4. Create session_path / f"iteration_{iteration+1}" with the four subdirs
    #    and copy annotation JSONs forward
    # 5. (Optional) append a row to session_path / "metrics_history.csv"
    return {"iteration": iteration, "success": True, ...}
```

See [`docs/bring-your-own-trainer.md`](../../docs/bring-your-own-trainer.md)
for the full specification and reasoning.
