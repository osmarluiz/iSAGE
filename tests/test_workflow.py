"""Workflow API tests.

These tests exercise the public Workflow API but stop short of running the
GUI annotator or a real training loop — the goal is to verify construction,
configuration handling, and dispatch, not to retrain the paper. Slow paths
(annotate, train) are covered by separate integration tests gated behind
``--run-integration``.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest


def _patch_setup_training_to_skip_torch(monkeypatch):
    """Avoid pulling torch + smp + GPU init during fast tests.

    Workflow's __init__ calls setup_training to build the model. For
    introspection-level tests we don't need a real model — we just need the
    method to return enough values to satisfy the constructor.
    """
    fake_returns = (object(), "cpu", object(), object(), [object()], object())

    def fake_setup_training(*, dataset_config, training_config):
        return fake_returns

    monkeypatch.setattr("src.workflow.setup_training", fake_setup_training)
    return fake_returns


def test_workflow_construction(tmp_path, tiny_dataset, monkeypatch):
    """Workflow.from_config builds and exposes the basic attributes."""
    _patch_setup_training_to_skip_torch(monkeypatch)

    session_path = tmp_path / "ws"
    # Use a placeholder training YAML that just needs to load
    training_yaml = tmp_path / "training.yaml"
    training_yaml.write_text(
        "name: stub\n"
        "model:\n  architecture: Unet\n  encoder: efficientnet-b0\n  encoder_weights: imagenet\n  activation: softmax\n  in_channels: 3\n"
        "training:\n  learning_rate: 0.0001\n  batch_size: {train: 2, val: 2}\n  num_epochs: 1\n  device: cpu\n  num_workers: 0\n"
        "loss:\n  train: {name: EWDLMulticlass, params: {eps: 1.0, wrong_penalty: 5.0, activation: null}}\n  validation: {name: CrossEntropyLoss, params: {}}\n"
        "optimizer: {name: Adam, params: {lr: 0.0001}}\n"
        "metrics: [mIoU]\n"
        "checkpointing: {save_best: true, monitor_metric: val_loss, mode: min, save_interval: null}\n"
    )

    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=session_path,
        iteration="latest",
    )

    assert wf.session_path == session_path
    assert wf.iteration == "latest"
    assert wf.dataset_config["name"] == "TINY"
    assert wf.training_config["name"] == "stub"
    assert wf.name == "ws"
    # Session directory got created
    assert session_path.exists()
    # And contains iteration_0 with the standard subdirs
    assert (session_path / "iteration_0" / "annotations").exists()


def test_workflow_view_returns_session_view(tmp_path, tiny_dataset, monkeypatch):
    """Workflow.view returns a SessionView reflecting current disk state."""
    _patch_setup_training_to_skip_torch(monkeypatch)

    training_yaml = tmp_path / "training.yaml"
    training_yaml.write_text(
        "name: stub\nmodel:\n  architecture: Unet\n  encoder: efficientnet-b0\n  encoder_weights: imagenet\n  activation: softmax\n  in_channels: 3\n"
        "training:\n  learning_rate: 0.0001\n  batch_size: {train: 2, val: 2}\n  num_epochs: 1\n  device: cpu\n  num_workers: 0\n"
        "loss:\n  train: {name: EWDLMulticlass, params: {eps: 1.0, wrong_penalty: 5.0, activation: null}}\n  validation: {name: CrossEntropyLoss, params: {}}\n"
        "optimizer: {name: Adam, params: {lr: 0.0001}}\n"
        "metrics: [mIoU]\n"
        "checkpointing: {save_best: true, monitor_metric: val_loss, mode: min, save_interval: null}\n"
    )

    from src.session.session_view import SessionView
    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws2",
    )
    assert isinstance(wf.view, SessionView)
    assert wf.view.exists is True


def test_workflow_repr(tmp_path, tiny_dataset, monkeypatch):
    """repr() is informative — includes session name, iteration, dataset."""
    _patch_setup_training_to_skip_torch(monkeypatch)
    training_yaml = tmp_path / "training.yaml"
    training_yaml.write_text(
        "name: stub\nmodel:\n  architecture: Unet\n  encoder: efficientnet-b0\n  encoder_weights: imagenet\n  activation: softmax\n  in_channels: 3\n"
        "training:\n  learning_rate: 0.0001\n  batch_size: {train: 2, val: 2}\n  num_epochs: 1\n  device: cpu\n  num_workers: 0\n"
        "loss:\n  train: {name: EWDLMulticlass, params: {eps: 1.0, wrong_penalty: 5.0, activation: null}}\n  validation: {name: CrossEntropyLoss, params: {}}\n"
        "optimizer: {name: Adam, params: {lr: 0.0001}}\n"
        "metrics: [mIoU]\n"
        "checkpointing: {save_best: true, monitor_metric: val_loss, mode: min, save_interval: null}\n"
    )

    from src.workflow import Workflow

    wf = Workflow.from_config(
        dataset=tiny_dataset["yaml_path"],
        training=training_yaml,
        session=tmp_path / "ws3",
    )
    r = repr(wf)
    assert "ws3" in r
    assert "TINY" in r
    assert "latest" in r


def test_val_optional_dataloader(tmp_path, tiny_dataset):
    """The dataloader accepts val_images=None — returns val_loader=None.

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

    # We need a masks_dir with one PNG per training image.
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
