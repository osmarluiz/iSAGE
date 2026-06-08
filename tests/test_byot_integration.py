"""Integration test: a non-default trainer runs one full iSAGE iteration
end-to-end on the BSB toy and writes every output the contract demands.

This is the load-bearing assertion that the Trainer protocol is
genuinely pluggable, not just structurally compatible. The reference
trainer (TinyTorchTrainer at examples/byot/example_trainer.py) uses raw
PyTorch with a tiny U-Net and no segmentation_models.pytorch dependency.
If this test passes, custom trainers with any framework should work too.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


# Skip the test if torch is not available (CI matrix where CPU-only torch
# is installed should still run this; only environments without torch skip).
torch = pytest.importorskip("torch")


def _has_bsb_toy() -> bool:
    """The example dataset ships with the repo; tests skip if it is missing
    (e.g., a partial checkout)."""
    root = Path(__file__).resolve().parent.parent / "examples" / "bsb_toy"
    return (root / "dataset.yaml").exists() and (root / "image_train").exists()


@pytest.mark.skipif(not _has_bsb_toy(), reason="BSB toy example not present")
def test_byot_end_to_end_on_bsb_toy(tmp_path):
    """A custom Trainer (TinyTorchTrainer) plugs into Workflow and produces
    every output the contract requires.
    """
    import sys
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from examples.byot.example_trainer import TinyTorchTrainer
    from src.training.trainer_protocol import Trainer
    from src.workflow import Workflow

    trainer = TinyTorchTrainer(num_epochs=1, lr=1e-3, batch_size=4)
    assert isinstance(trainer, Trainer), "trainer must satisfy the Trainer protocol"

    session_path = tmp_path / "byot_session"
    wf = Workflow.from_config(
        dataset=str(repo_root / "examples" / "bsb_toy" / "dataset.yaml"),
        training=str(repo_root / "examples" / "bsb_toy" / "training.yaml"),
        session=session_path,
        iteration="latest",
        trainer=trainer,
    )
    assert type(wf.trainer).__name__ == "TinyTorchTrainer"
    assert (session_path / "iteration_0" / "masks").exists()

    result = wf.train()

    # The contract: outputs of train_one_iteration
    assert result["success"] is True
    assert result["iteration"] == 0
    assert result["next_iteration"] == 1

    # The contract: artifacts on disk
    assert (session_path / "iteration_0" / "models" / "best_model.pth").exists(), \
        "model checkpoint missing"

    pred_dir = session_path / "iteration_0" / "predictions"
    pred_files = sorted(pred_dir.glob("*.png"))
    assert len(pred_files) == 30, f"expected 30 prediction PNGs, got {len(pred_files)}"

    # Predictions must contain valid class indices
    pred = np.asarray(Image.open(pred_files[0]))
    assert pred.dtype == np.uint8
    assert pred.shape == (256, 256)
    assert pred.min() >= 0
    assert pred.max() < 5  # 5 classes in BSB toy

    # The contract: iteration_{N+1} created with the four subdirs
    iter1 = session_path / "iteration_1"
    for sub in ("annotations", "masks", "models", "predictions"):
        assert (iter1 / sub).exists(), f"iteration_1/{sub}/ missing"
    n_ann_iter1 = len(list((iter1 / "annotations").glob("*.json")))
    assert n_ann_iter1 == 30, f"expected 30 annotation JSONs copied forward, got {n_ann_iter1}"

    # The contract: metrics_history.csv has one row for iter 0
    csv_path = session_path / "metrics_history.csv"
    assert csv_path.exists()
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert int(rows[0]["iteration"]) == 0
    assert float(rows[0]["train_loss"]) > 0
