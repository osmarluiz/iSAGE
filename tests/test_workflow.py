"""Workflow API tests.

These tests exercise the public Workflow API but stop short of running the
GUI annotator or a real training loop -- the goal is to verify
construction, configuration handling, and dispatch, not to retrain the
paper. The default trainer (SmpTrainer) needs torch + smp, so most tests
inject a stub trainer to keep them fast and hermetic. The pluggability is
itself an assertion of the new architecture.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest


class StubTrainer:
    """Minimal Trainer protocol implementation for tests.

    Does not touch torch, smp, or any GPU. Records the iteration it was
    asked to train so tests can assert on dispatch.
    """

    def __init__(self):
        self.train_calls = []

    def train_one_iteration(self, *, session_path, dataset_config, iteration, visualize=False):
        self.train_calls.append({
            "session_path": session_path,
            "iteration": iteration,
            "visualize": visualize,
        })
        return {"iteration": iteration, "success": True, "message": "stub"}


def _minimal_training_yaml(path):
    path.write_text(
        "name: stub\n"
        "model:\n  architecture: Unet\n  encoder: efficientnet-b0\n  encoder_weights: imagenet\n  activation: softmax\n  in_channels: 3\n"
        "training:\n  learning_rate: 0.0001\n  batch_size: {train: 2, val: 2}\n  num_epochs: 1\n  device: cpu\n  num_workers: 0\n"
        "loss:\n  train: {name: EWDLMulticlass, params: {eps: 1.0, wrong_penalty: 5.0, activation: null}}\n  validation: {name: CrossEntropyLoss, params: {}}\n"
        "optimizer: {name: Adam, params: {lr: 0.0001}}\n"
        "metrics: [mIoU]\n"
        "checkpointing: {save_best: true, monitor_metric: val_loss, mode: min, save_interval: null}\n"
    )
    return path


def test_workflow_construction(tmp_path, tiny_dataset):
    """Workflow.from_config builds and exposes the basic attributes when given
    a stub trainer, bypassing the default smp-backed trainer's heavy imports.
    """
    training_yaml = _minimal_training_yaml(tmp_path / "training.yaml")

    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws",
        iteration="latest",
        trainer=StubTrainer(),
    )

    assert wf.session_path == tmp_path / "ws"
    assert wf.iteration == "latest"
    assert wf.dataset_config["name"] == "TINY"
    assert wf.training_config["name"] == "stub"
    assert wf.name == "ws"
    assert (tmp_path / "ws").exists()
    assert (tmp_path / "ws" / "iteration_0" / "annotations").exists()


def test_workflow_view_returns_session_view(tmp_path, tiny_dataset):
    """Workflow.view returns a SessionView reflecting current disk state."""
    training_yaml = _minimal_training_yaml(tmp_path / "training.yaml")

    from src.session.session_view import SessionView
    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws2",
        trainer=StubTrainer(),
    )
    assert isinstance(wf.view, SessionView)
    assert wf.view.exists is True


def test_workflow_repr(tmp_path, tiny_dataset):
    """repr() is informative -- includes session name, iteration, dataset,
    and the trainer class name (proves the pluggability is surfaced)."""
    training_yaml = _minimal_training_yaml(tmp_path / "training.yaml")

    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws3",
        trainer=StubTrainer(),
    )
    r = repr(wf)
    assert "ws3" in r
    assert "TINY" in r
    assert "latest" in r
    assert "StubTrainer" in r


def test_workflow_train_dispatches_to_trainer(tmp_path, tiny_dataset):
    """Workflow.train() delegates to trainer.train_one_iteration. This is
    the load-bearing contract for the pluggable architecture."""
    training_yaml = _minimal_training_yaml(tmp_path / "training.yaml")

    from src.workflow import Workflow

    stub = StubTrainer()
    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws4",
        iteration="latest",
        trainer=stub,
    )

    result = wf.train(visualize=False)
    assert result["success"] is True
    assert len(stub.train_calls) == 1
    call = stub.train_calls[0]
    assert call["iteration"] == "latest"
    assert call["session_path"] == tmp_path / "ws4"
    assert call["visualize"] is False


def test_val_optional_dataloader(tmp_path, tiny_dataset):
    """The dataloader accepts val_images=None -- returns val_loader=None.

    This isn't strictly a Workflow test, but it's the contract Workflow
    depends on (val-less BYOD path). Failing this means train() will crash.
    """
    from src.training.dataloader import create_dataloaders

    cfg = copy.deepcopy(tiny_dataset["config"])
    cfg["paths"]["val_images"] = None
    cfg["paths"]["val_masks"] = None

    training_cfg = {
        "training": {"batch_size": {"train": 2, "val": 2}},
        "loss": {"train": {"name": "EWDLMulticlass"}},
    }

    masks_dir = tmp_path / "fake_masks"
    masks_dir.mkdir()
    from PIL import Image
    import numpy as np

    for img in sorted(tiny_dataset["img_dir"].glob("*.png")):
        Image.fromarray(
            np.full((tiny_dataset["size"], tiny_dataset["size"]), tiny_dataset["ignore_index"], dtype=np.uint8)
        ).save(masks_dir / img.name)

    train_loader, val_loader, train_images, base_t, class_counts = create_dataloaders(
        dataset_config=cfg, training_config=training_cfg, masks_dir=masks_dir,
    )
    assert train_loader is not None
    assert val_loader is None, "val_loader must be None when val paths are null"
    assert len(train_images) == 5
