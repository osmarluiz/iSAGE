"""The default iSAGE trainer: U-Net family + Error-Weighted Dice Loss.

This is the *reference implementation* of the :class:`Trainer` protocol. It
wraps the existing :func:`src.training.setup.setup_training` and
:func:`src.training.workflow.run_training_iteration` machinery behind a
clean interface, so :class:`src.workflow.Workflow` can accept it as a
pluggable component.

To bring your own trainer, implement the :class:`Trainer` protocol (one
method: ``train_one_iteration``) and pass an instance to
``Workflow.from_config(..., trainer=YourTrainer())``. See
``docs/bring-your-own-trainer.md`` for the full contract and
``examples/byot/example_trainer.py`` for a minimal working example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from src.training.setup import setup_training
from src.training.workflow import run_training_iteration

IterationSpec = Union[int, str]


class SmpTrainer:
    """Default trainer: builds a ``segmentation_models.pytorch`` model and
    runs the EWDL-supervised training loop documented in the methods paper.

    Stores the model, device, losses, metrics, and optimizer as attributes
    so the same trainer instance can train multiple iterations of the same
    session without rebuilding the graph.

    Example::

        trainer = SmpTrainer(dataset_config=ds, training_config=tr)
        wf = Workflow(
            dataset_config=ds, training_config=tr,
            session_path='Sessions/run', trainer=trainer,
        )
        wf.train()  # delegates to trainer.train_one_iteration(...)
    """

    def __init__(self, *, dataset_config: dict, training_config: dict):
        self.dataset_config = dataset_config
        self.training_config = training_config

        (
            self.model,
            self.device,
            self.train_loss,
            self.val_loss,
            self.metrics,
            self.optimizer,
        ) = setup_training(
            dataset_config=dataset_config,
            training_config=training_config,
        )

    def train_one_iteration(
        self,
        *,
        session_path: Path,
        dataset_config: dict,
        iteration: IterationSpec = "latest",
        visualize: bool = False,
    ) -> dict:
        """Run one EWDL-supervised training iteration. Returns the metrics dict."""
        return run_training_iteration(
            session_path=session_path,
            dataset_config=dataset_config,
            training_config=self.training_config,
            model=self.model,
            device=self.device,
            train_loss=self.train_loss,
            val_loss=self.val_loss,
            metrics=self.metrics,
            optimizer=self.optimizer,
            iteration=iteration,
            visualize=visualize,
        )


__all__ = ["SmpTrainer"]
