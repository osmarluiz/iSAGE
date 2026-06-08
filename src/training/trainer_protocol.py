"""The Trainer contract for iSAGE.

iSAGE separates *what gets stored on disk* (the session directory) from *what
trains the model*. The session directory is fixed:

    Sessions/<name>/
        iteration_N/
            annotations/   # JSONs written by the annotator
            masks/         # PNGs derived from the JSONs (supervision)
            models/        # trained checkpoints
            predictions/   # model outputs used as overlay for iteration_{N+1}
        metrics_history.csv

The trainer is the variable part. The default that ships with iSAGE is
:class:`src.training.smp_trainer.SmpTrainer` (a U-Net family from
``segmentation_models.pytorch`` plus the Error-Weighted Dice Loss). Users
can plug their own trainer by implementing this :class:`Trainer` protocol.

A custom trainer is free to use any framework (raw PyTorch, PyTorch
Lightning, monai, fastai, MMSegmentation, JAX, even non-Python via subprocess
calls). The only contract is the four points below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Union, runtime_checkable


IterationSpec = Union[int, str]  # int or 'latest'


@runtime_checkable
class Trainer(Protocol):
    """Anything that trains one iSAGE iteration.

    Implementations must:

    1. **Read masks.** Consume the PNG mask files under
       ``session_path / f"iteration_{iteration}" / "masks"``. Each pixel is
       a class index in ``[0, num_classes-1]`` or the ``ignore_index``
       value defined in ``dataset_config['classes']['ignore_index']``.

    2. **Write a model checkpoint.** Save the trained model state to
       ``session_path / f"iteration_{iteration}" / "models" / "best_model.pth"``.
       The format is implementation-defined; downstream consumers (the
       annotator's prediction overlay) only need predictions, not the
       checkpoint itself.

    3. **Write predictions.** Save one PNG per training image to
       ``session_path / f"iteration_{iteration}" / "predictions"``. Each
       pixel value is a predicted class index. These power the
       prediction-overlay the annotator shows on the next iteration.

    4. **Advance the iteration.** Create
       ``session_path / f"iteration_{iteration+1}"`` with the usual four
       subdirectories (``annotations``, ``masks``, ``models``,
       ``predictions``) and copy the current iteration's annotation JSONs
       into the new ``annotations/``. Optionally also regenerate the masks
       there.

    Optionally:

    5. Append one row to ``session_path / "metrics_history.csv"`` with the
       iteration's metrics. See ``examples/byot/example_trainer.py`` for
       the column convention.

    The default implementation :class:`SmpTrainer` does all of these.
    Override individual steps in a custom trainer if your framework needs
    them done differently; the rest of iSAGE (annotator, session manager,
    CLI, notebook) is agnostic to how training happens.
    """

    def train_one_iteration(
        self,
        *,
        session_path: Path,
        dataset_config: dict,
        iteration: IterationSpec = "latest",
        visualize: bool = False,
    ) -> dict:
        """Train on the given iteration and return a result dict.

        Args:
            session_path: Root of the session directory.
            dataset_config: Parsed YAML dict from ``configs/datasets/*.yaml``.
                Carries class names, ``ignore_index``, image paths, etc.
            iteration: ``'latest'`` (default) or a specific integer.
            visualize: If True, the trainer may produce diagnostic plots.
                Implementations may ignore this flag.

        Returns:
            A dict with at least ``iteration`` (int) and ``success`` (bool).
            Recommended additional keys: ``mean_iou``, ``pixel_accuracy``,
            ``train_loss``, ``val_loss``, ``num_predictions``,
            ``next_iteration``, ``message``.
        """
        ...


__all__ = ["Trainer", "IterationSpec"]
