"""Shared pytest fixtures for the iSAGE test suite.

The fixtures construct everything inside a temporary directory so tests are
hermetic and parallelizable.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

# Make 'src.X' imports resolve from anywhere the suite is invoked.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_synthetic_image(size: int, seed: int) -> Image.Image:
    """Produce a deterministic synthetic RGB image. Fast, no I/O dependencies."""
    rng = np.random.RandomState(seed)
    arr = rng.randint(0, 255, size=(size, size, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def _make_mask(size: int, num_classes: int, ignore_index: int) -> Image.Image:
    """Produce a mask with all-ignore baseline and a few sparse class pixels.

    Mirrors the iSAGE convention: most pixels are ignore_index, a handful
    carry class labels.
    """
    mask = np.full((size, size), ignore_index, dtype=np.uint8)
    rng = np.random.RandomState(0)
    coords = rng.randint(0, size, size=(num_classes * 4, 2))
    for i, (y, x) in enumerate(coords):
        mask[y, x] = i % num_classes
    return Image.fromarray(mask)


@pytest.fixture
def tiny_dataset(tmp_path: Path):
    """Build a 5-image synthetic dataset with 3 foreground classes.

    Returns a dict with the YAML path, the image dir, and dataset config keys
    that tests can reference. Includes val images and val masks so val-required
    paths can be exercised; tests that want val-less can null them out.
    """
    img_dir = tmp_path / "images"
    val_img_dir = tmp_path / "val_images"
    val_mask_dir = tmp_path / "val_masks"
    sparse_masks_dir = tmp_path / "sparse_masks"
    img_dir.mkdir()
    val_img_dir.mkdir()
    val_mask_dir.mkdir()
    sparse_masks_dir.mkdir()

    size = 32
    num_classes = 3
    ignore_index = num_classes

    for i in range(5):
        _make_synthetic_image(size, seed=i).save(img_dir / f"{i}.png")
        # Seed sparse mask (mostly ignore + a few class pixels)
        _make_mask(size, num_classes, ignore_index).save(sparse_masks_dir / f"{i}.png")
    for i in range(2):
        _make_synthetic_image(size, seed=100 + i).save(val_img_dir / f"{i}.png")
        _make_mask(size, num_classes, ignore_index).save(val_mask_dir / f"{i}.png")

    yaml_obj = {
        "name": "TINY",
        "paths": {
            "train_images": str(img_dir),
            "train_dense_masks": None,
            "train_sparse_masks": str(sparse_masks_dir),
            "val_images": str(val_img_dir),
            "val_masks": str(val_mask_dir),
            "test_images": None,
            "test_masks": None,
        },
        "classes": {
            "num_classes": num_classes,
            "ignore_index": ignore_index,
            "names": ["a", "b", "c"],
            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
        },
        "image": {"width": size, "height": size, "channels": 3},
    }
    yaml_path = tmp_path / "tiny.yaml"
    yaml_path.write_text(yaml.safe_dump(yaml_obj))
    return {
        "yaml_path": yaml_path,
        "img_dir": img_dir,
        "size": size,
        "num_classes": num_classes,
        "ignore_index": ignore_index,
        "config": yaml_obj,
    }


@pytest.fixture
def tiny_session(tmp_path: Path, tiny_dataset):
    """Pre-populated session with iteration_0 and iteration_1.

    iteration_0 has annotations + masks; iteration_1 has annotations + masks
    + a fake model.pth. Lets SessionView tests assert against a realistic
    layout without running training.
    """
    session = tmp_path / "session_under_test"
    cfg = tiny_dataset["config"]
    num_classes = cfg["classes"]["num_classes"]
    ignore_index = cfg["classes"]["ignore_index"]
    size = cfg["image"]["width"]
    images = sorted((tiny_dataset["img_dir"]).glob("*.png"))

    for iter_n in (0, 1):
        ip = session / f"iteration_{iter_n}"
        (ip / "annotations").mkdir(parents=True)
        (ip / "masks").mkdir()
        (ip / "models").mkdir()
        (ip / "predictions").mkdir()
        for img in images:
            stem = img.stem
            (ip / "annotations" / f"{stem}.json").write_text(json.dumps({
                "format_version": "1.0",
                "image": {"name": img.name, "width": size, "height": size},
                "iteration": iter_n,
                "created_at": "2026-01-01T00:00:00Z",
                "annotations": [[5, 5, 0], [10, 10, 1], [15, 15, 2]],
            }))
            _make_mask(size, num_classes, ignore_index).save(ip / "masks" / f"{stem}.png")

    # Mark iter_1 as trained by writing a stub model.pth and predictions
    (session / "iteration_1" / "models" / "best_model.pth").write_bytes(b"\x00" * 16)
    for img in images:
        Image.new("L", (size, size)).save(session / "iteration_1" / "predictions" / img.name)

    # Write a metrics_history.csv with one row for iter_0 only (iter_1 not finished)
    (session / "metrics_history.csv").write_text(
        "iteration,miou,pixel_accuracy,train_loss,val_loss\n"
        "0,0.42,0.81,0.5,1.2\n"
    )
    return session
