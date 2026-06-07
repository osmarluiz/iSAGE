"""High-level driver API for an iSAGE session.

The annotate-train loop in iSAGE is just three platform calls glued together:
load the configs, set up the model, and alternate between
``run_annotation_workflow`` and ``run_training_iteration``. ``Workflow``
bundles that into one object so any driver — a Jupyter widget, a CLI script,
a Streamlit app, an HTTP service — uses the same minimal surface:

    >>> wf = Workflow.from_config(
    ...     dataset='configs/datasets/my.yaml',
    ...     training='configs/training/unet_efficientnet_b7.yaml',
    ...     session='Sessions/my_run',
    ... )
    >>> wf.annotate()    # launches the PyQt5 annotator on the latest iter
    >>> wf.train()       # trains, generates predictions, advances iter

The notebook is one driver and not the API. Replacing the notebook with the
CLI script ``examples/cli_driver.py`` is a faithful equivalent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import matplotlib.pyplot as plt
import pandas as pd

from src.annotation.launcher import run_annotation_workflow
from src.session.manager import get_or_create_session
from src.session.session_view import SessionView
from src.training.setup import setup_training
from src.training.workflow import run_training_iteration
from src.utils.config_loader import load_dataset_config, load_training_config


IterationSpec = Union[int, str]  # int (specific iter) or 'latest'


class Workflow:
    """One iSAGE session ready to annotate or train.

    Holds the model, optimizer, losses, dataset config, training config, and
    session path. The methods just dispatch to the underlying platform
    functions, so this class is thin by design — no behaviour the lower layers
    don't already implement.
    """

    def __init__(
        self,
        *,
        dataset_config: dict,
        training_config: dict,
        session_path: Union[Path, str],
        iteration: IterationSpec = "latest",
    ):
        self.dataset_config = dataset_config
        self.training_config = training_config
        self.session_path = Path(session_path)
        self.iteration: IterationSpec = iteration

        (
            self.model,
            self.device,
            self.train_loss,
            self.val_loss,
            self.metrics,
            self.optimizer,
        ) = setup_training(
            dataset_config=self.dataset_config,
            training_config=self.training_config,
        )
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
    ) -> "Workflow":
        """Build a Workflow from YAML paths and a session directory."""
        return cls(
            dataset_config=load_dataset_config(str(dataset)),
            training_config=load_training_config(str(training)),
            session_path=session,
            iteration=iteration,
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
        """Train on ``self.iteration``, generate predictions, advance to next iter."""
        return run_training_iteration(
            session_path=self.session_path,
            dataset_config=self.dataset_config,
            training_config=self.training_config,
            model=self.model,
            device=self.device,
            train_loss=self.train_loss,
            val_loss=self.val_loss,
            metrics=self.metrics,
            optimizer=self.optimizer,
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
            f"dataset={self.dataset_config['name']!r})"
        )


__all__ = ["Workflow"]
