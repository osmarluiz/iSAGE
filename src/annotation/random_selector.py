"""
Random point selector — fully output-independent baseline for active learning.

For each frame and each ground-truth class, picks one uniformly random pixel
of that class and records (x, y, gt_label). The model's predictions are not
read at all — neither for budget allocation nor for pixel choice — so this
baseline carries zero dependence on model outputs.

Purpose: this is the strongest possible test of the structural claim that "no
function over model outputs reaches the pixels that carry the highest training
value". If output-independent random sampling, with perfect GT-stratified
class coverage and ground-truth labels for free, still saturates below iSAGE,
then the gap cannot be explained away by "the right output-reading function
was not tried" — there is no output reading at all.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

from src.session.mask_utils import batch_json_to_masks
from src.training.workflow import PredictionDataset


def _resolve_dataset_path(relative_path: str | Path) -> Path:
    p = Path(relative_path)
    if p.is_absolute() and p.exists():
        return p
    cwd = Path.cwd()
    for c in (cwd / p, cwd / "archive" / p, cwd / "DATASETS" / p):
        if c.exists():
            return c
    raise FileNotFoundError(f"Could not locate dataset path '{relative_path}'.")


def _build_base_transform(dataset_config: dict):
    normalization = dataset_config.get("normalization")
    if normalization:
        return transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=normalization["mean"], std=normalization["std"]),
        ])
    return transforms.Compose([transforms.ToTensor()])


def _select_random_points_for_frame(
    gt_mask: np.ndarray,
    num_classes: int,
    ignore_index: int,
    existing_points: set[tuple[int, int]],
    max_per_class: int,
    rng: np.random.Generator,
) -> tuple[list[list[int]], dict[str, int]]:
    """Pick uniformly random pixels per ground-truth class for a single frame.

    Allocates budget by GT class (not by predicted class) and samples within
    each GT class region uniformly at random. This is fully independent of
    model outputs.
    """
    new_points: list[list[int]] = []
    stats = {"class_absent": 0}

    for c in range(num_classes):
        coords = np.argwhere(gt_mask == c)  # (N, 2) array of (y, x) for GT class c
        if coords.size == 0:
            stats["class_absent"] += 1
            continue

        # Filter out already-annotated pixels.
        if existing_points:
            keep = np.ones(coords.shape[0], dtype=bool)
            for i, (y, x) in enumerate(coords):
                if (int(x), int(y)) in existing_points:
                    keep[i] = False
            coords = coords[keep]
            if coords.size == 0:
                continue

        rng.shuffle(coords)
        picks_this_class = 0
        idx = 0
        while picks_this_class < max_per_class and idx < coords.shape[0]:
            y, x = int(coords[idx, 0]), int(coords[idx, 1])
            idx += 1
            new_points.append([x, y, c])  # GT class c by construction
            existing_points.add((x, y))
            picks_this_class += 1

    return new_points, stats


def _load_gt_mask(gt_masks_dir: Path, stem: str) -> np.ndarray | None:
    for ext in (".png", ".tif", ".tiff"):
        candidate = gt_masks_dir / f"{stem}{ext}"
        if candidate.exists():
            arr = np.array(Image.open(candidate))
            return arr[..., 0] if arr.ndim == 3 else arr
    return None


def run_random_selection(
    session_path: str | Path,
    dataset_config: dict,
    current_iter: int,
    seed: int,
    max_per_class_per_frame: int = 1,
) -> dict:
    """Populate iteration_{current_iter+1}/annotations with GT-based random points.

    No model inference is required: for each training image, the GT mask is
    read directly and a uniformly random pixel from each GT class region is
    appended to the next iteration's annotations.
    """
    session_path = Path(session_path)
    next_path = session_path / f"iteration_{current_iter + 1}"
    next_annotations_dir = next_path / "annotations"
    next_masks_dir = next_path / "masks"

    if not next_annotations_dir.exists():
        raise FileNotFoundError(
            f"Expected {next_annotations_dir} to exist. "
            f"Run run_training_iteration(iteration={current_iter}) first."
        )

    paths = dataset_config["paths"]
    gt_masks_key = "train_dense_masks" if "train_dense_masks" in paths else "train_masks"
    if gt_masks_key not in paths:
        raise KeyError("dataset_config['paths'] needs train_dense_masks or train_masks")

    train_images_dir = _resolve_dataset_path(paths["train_images"])
    gt_masks_dir = _resolve_dataset_path(paths[gt_masks_key])
    print(f"  train_images: {train_images_dir}")
    print(f"  train_dense_masks: {gt_masks_dir}")

    num_classes = dataset_config["classes"]["num_classes"]
    ignore_index = dataset_config["classes"]["ignore_index"]

    image_paths = sorted(
        list(train_images_dir.glob("*.png"))
        + list(train_images_dir.glob("*.tif"))
        + list(train_images_dir.glob("*.tiff"))
    )
    if not image_paths:
        raise FileNotFoundError(f"No training images in {train_images_dir}")

    # Per (seed, iteration) RNG so picks are reproducible but differ across iters.
    rng = np.random.default_rng(seed=seed * 10000 + current_iter)

    stats = {
        "frames_processed": 0,
        "frames_without_gt": 0,
        "points_added": 0,
        "classes_absent": 0,
    }

    img_w = dataset_config["image"]["width"]
    img_h = dataset_config["image"]["height"]

    for img_path in tqdm(image_paths, desc="Random-selection"):
        stem = img_path.stem
        json_path = next_annotations_dir / f"{stem}.json"

        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
        else:
            data = {
                "format_version": "1.0",
                "image": {"name": f"{stem}.png", "width": img_w, "height": img_h},
                "annotations": [],
                "iteration": current_iter + 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        existing_points = {
            (int(a[0]), int(a[1])) for a in data.get("annotations", [])
        }

        gt_mask = _load_gt_mask(gt_masks_dir, stem)
        if gt_mask is None:
            stats["frames_without_gt"] += 1
            continue

        new_points, frame_stats = _select_random_points_for_frame(
            gt_mask=gt_mask,
            num_classes=num_classes,
            ignore_index=ignore_index,
            existing_points=existing_points,
            max_per_class=max_per_class_per_frame,
            rng=rng,
        )

        data["annotations"].extend(new_points)
        data["iteration"] = current_iter + 1
        data["created_at"] = datetime.now(timezone.utc).isoformat()

        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        stats["frames_processed"] += 1
        stats["points_added"] += len(new_points)
        stats["classes_absent"] += frame_stats["class_absent"]

    print("\nRegenerating PNG masks from updated annotations...")
    success, fail = batch_json_to_masks(
        json_dir=next_annotations_dir,
        output_dir=next_masks_dir,
        image_size=(img_w, img_h),
        ignore_index=ignore_index,
    )
    print(f"✓ Regenerated {success} masks ({fail} failed)")

    print("\nRandom-selection summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return stats
