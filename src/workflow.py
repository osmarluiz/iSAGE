"""High-level driver API for an iSAGE session.

The annotate-train loop in iSAGE is just three platform calls glued together:
load the configs, set up the trainer, and alternate between
``run_annotation_workflow`` and ``trainer.train_one_iteration``. ``Workflow``
bundles that into one object so any driver — a Jupyter widget, a CLI script,
a Streamlit app, an HTTP service — uses the same minimal surface:

    >>> wf = Workflow.from_config(
    ...     dataset='configs/datasets/my.yaml',
    ...     training='configs/training/unet_efficientnet_b7.yaml',
    ...     session='Sessions/my_run',
    ... )
    >>> wf.annotate()    # launches the PyQt5 annotator on the latest iter
    >>> wf.train()       # trains, generates predictions, advances iter

The training backend is pluggable. The default is :class:`SmpTrainer` (U-Net
family from ``segmentation_models.pytorch`` plus EWDL). Pass
``trainer=YourTrainer()`` to swap it for your own implementation — see
``docs/bring-your-own-trainer.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import matplotlib.pyplot as plt
import pandas as pd

from src.annotation.launcher import run_annotation_workflow
from src.session.manager import get_or_create_session
from src.session.session_view import SessionView
from src.training.trainer_protocol import Trainer
from src.utils.config_loader import load_dataset_config, load_training_config


IterationSpec = Union[int, str]  # int (specific iter) or 'latest'


class Workflow:
    """One iSAGE session ready to annotate or train.

    Holds the dataset config, training config, session path, and a Trainer
    instance. The methods dispatch to the underlying platform functions, so
    this class is thin by design — no behaviour the lower layers don't
    already implement.

    The trainer is pluggable. If not provided, the default
    :class:`SmpTrainer` is constructed (U-Net family from
    ``segmentation_models.pytorch`` plus the Error-Weighted Dice Loss).
    Pass any object implementing the :class:`Trainer` protocol to swap.
    """

    def __init__(
        self,
        *,
        dataset_config: dict,
        training_config: dict,
        session_path: Union[Path, str],
        iteration: IterationSpec = "latest",
        trainer: Optional[Trainer] = None,
    ):
        self.dataset_config = dataset_config
        self.training_config = training_config
        self.session_path = Path(session_path)
        self.iteration: IterationSpec = iteration

        if trainer is None:
            # Default trainer: U-Net + EWDL via segmentation_models.pytorch.
            # Lazy-imported so users who plug in their own trainer don't pay
            # the smp import cost.
            from src.training.smp_trainer import SmpTrainer
            trainer = SmpTrainer(
                dataset_config=self.dataset_config,
                training_config=self.training_config,
            )
        self.trainer: Trainer = trainer

        get_or_create_session(
            session_path=self.session_path,
            dataset_config=self.dataset_config,
        )

    # ---- Constructors ------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        *,
        dataset: Union[Path, str],
        training: Union[Path, str],
        session: Union[Path, str],
        iteration: IterationSpec = "latest",
        trainer: Optional[Trainer] = None,
    ) -> "Workflow":
        """Build a Workflow from YAML paths and a session directory.

        Pass ``trainer`` to override the default :class:`SmpTrainer`. The
        custom trainer must implement the :class:`Trainer` protocol (one
        method: ``train_one_iteration``). See
        ``docs/bring-your-own-trainer.md`` for the contract.
        """
        return cls(
            dataset_config=load_dataset_config(str(dataset)),
            training_config=load_training_config(str(training)),
            session_path=session,
            iteration=iteration,
            trainer=trainer,
        )

    # ---- State -------------------------------------------------------------

    @property
    def view(self) -> SessionView:
        """Read-only view of the session on disk (always reflects current state)."""
        return SessionView(self.session_path)

    @property
    def name(self) -> str:
        return self.session_path.name

    # ---- Actions -----------------------------------------------------------

    def annotate(self, launch_tool: bool = True):
        """Open the annotator on ``self.iteration``. Blocks until the GUI closes."""
        return run_annotation_workflow(
            session_path=self.session_path,
            dataset_config=self.dataset_config,
            iteration=self.iteration,
            launch_tool=launch_tool,
        )

    def train(self, visualize: bool = False):
        """Train on ``self.iteration``, generate predictions, advance to next iter.

        Delegates to ``self.trainer.train_one_iteration``. The default trainer
        is :class:`SmpTrainer`; any object implementing the
        :class:`Trainer` protocol can be substituted at construction time.
        """
        return self.trainer.train_one_iteration(
            session_path=self.session_path,
            dataset_config=self.dataset_config,
            iteration=self.iteration,
            visualize=visualize,
        )

    # ---- Visualization (notebook-friendly) ---------------------------------

    def plot_progression(self, figsize=(8, 4)):
        """Plot per-iteration mIoU and pixel accuracy from metrics_history.csv.

        Returns the matplotlib Figure, or None if no metrics have been recorded
        yet (first iteration, or training without a validation set).
        """
        csv = self.session_path / "metrics_history.csv"
        if not csv.exists() or csv.stat().st_size == 0:
            print(
                "(No metrics_history.csv yet — either first training, or no "
                "validation set configured.)"
            )
            return None
        h = pd.read_csv(csv)
        if len(h) == 0:
            return None
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(h["iteration"], h["miou"], marker="o", linewidth=2, color="#1f77b4", label="val mIoU")
        if "pixel_accuracy" in h.columns:
            ax.plot(
                h["iteration"], h["pixel_accuracy"],
                marker="s", linewidth=1.5, color="#7f7f7f", alpha=0.6, label="pixel acc",
            )
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Metric")
        ax.set_title(f"{self.name} — progression")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
        ax.legend()
        plt.tight_layout()
        return fig

    # ---- Repr --------------------------------------------------------------

    def __repr__(self):
        return (
            f"Workflow(session={self.name!r}, "
            f"iteration={self.iteration!r}, "
            f"dataset={self.dataset_config['name']!r}, "
            f"trainer={type(self.trainer).__name__})"
        )


__all__ = ["Workflow"]
