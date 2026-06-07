"""
Entropy-oracle point selector — automated baseline for active learning.

Replaces the human-in-the-loop error inspection with entropy-based point
selection. For each training image, picks the highest-entropy pixel per
predicted class, reads the corresponding ground-truth label, and appends
the (x, y, gt_label) point to the next iteration's annotations.

Designed as a drop-in that runs between training iterations, without
modifying the existing workflow:

    run_training_iteration(iter=N)             # trains model N, copies annotations N → N+1
    run_entropy_oracle_selection(iter=N)       # appends new entropy points to iter N+1
    run_training_iteration(iter=N+1)           # trains on updated iter N+1 annotations
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
    """Resolve a yaml dataset path by checking common locations.

    The codebase's yamls use paths like ``VAIHINGEN_3/image_train`` that expect
    the data to live at the project root. In practice the data may have been
    moved to ``archive/`` or ``DATASETS/`` during reorganization. This helper
    searches those standard locations so the selector keeps working without
    requiring the yaml to be edited.
    """
    p = Path(relative_path)
    if p.is_absolute() and p.exists():
        return p

    cwd = Path.cwd()
    candidates = [
        cwd / p,
        cwd / "archive" / p,
        cwd / "DATASETS" / p,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Could not locate dataset path '{relative_path}'. "
        f"Searched: {[str(c) for c in candidates]}"
    )


def _build_base_transform(dataset_config: dict):
    """Reconstruct the inference transform used by create_dataloaders().

    Mirrors ``src.training.dataloader.create_dataloaders`` so the selector
    can run standalone without requiring the caller to already have a
    base_transform in scope.
    """
    normalization = dataset_config.get("normalization")
    if normalization:
        return transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=normalization["mean"], std=normalization["std"]
                ),
            ]
        )
    return transforms.Compose([transforms.ToTensor()])


def _select_points_for_frame(
    probs: np.ndarray,
    gt_mask: np.ndarray,
    num_classes: int,
    ignore_index: int,
    existing_points: set[tuple[int, int]],
    max_per_class: int,
) -> tuple[list[list[int]], dict[str, int]]:
    """Pick highest-entropy pixels per predicted class for a single frame.

    Args:
        probs: Softmax probabilities, shape (C, H, W).
        gt_mask: Ground-truth labels, shape (H, W).
        num_classes: Number of foreground classes (0..num_classes-1).
        ignore_index: Label value in gt_mask that means "unlabeled".
        existing_points: Set of (x, y) already annotated in this frame.
        max_per_class: Budget of new points per class (usually 1).

    Returns:
        new_points: List of [x, y, gt_label].
        stats: Counters for skipped classes (empty prediction / GT ignore).
    """
    C, H, W = probs.shape

    # Pixel-wise predictive entropy with numerical-stability epsilon.
    entropy = -(probs * np.log(probs + 1e-10)).sum(axis=0)
    pred = probs.argmax(axis=0)

    new_points: list[list[int]] = []
    stats = {"empty_prediction": 0, "gt_ignore": 0}

    for c in range(num_classes):
        class_mask = pred == c
        if not class_mask.any():
            stats["empty_prediction"] += 1
            continue

        # Restrict entropy to pixels predicted as class c.
        masked = np.where(class_mask, entropy, -np.inf)

        # Exclude already-annotated coordinates to avoid re-selecting the same pixel.
        if existing_points:
            xs = np.fromiter((x for x, _ in existing_points), dtype=np.int64)
            ys = np.fromiter((y for _, y in existing_points), dtype=np.int64)
            in_bounds = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
            masked[ys[in_bounds], xs[in_bounds]] = -np.inf

        picks_this_class = 0
        while picks_this_class < max_per_class:
            if not np.isfinite(masked).any():
                break
            flat = masked.argmax()
            y, x = np.unravel_index(flat, (H, W))
            if not np.isfinite(masked[y, x]):
                break

            masked[y, x] = -np.inf  # never pick this pixel again in this pass

            gt_label = int(gt_mask[y, x])
            if gt_label == ignore_index:
                stats["gt_ignore"] += 1
                # Try the next-best pixel for this class instead of giving up.
                continue

            new_points.append([int(x), int(y), gt_label])
            existing_points.add((int(x), int(y)))
            picks_this_class += 1

    return new_points, stats


def _load_gt_mask(gt_masks_dir: Path, stem: str) -> np.ndarray | None:
    for ext in (".png", ".tif", ".tiff"):
        candidate = gt_masks_dir / f"{stem}{ext}"
        if candidate.exists():
            arr = np.array(Image.open(candidate))
            return arr[..., 0] if arr.ndim == 3 else arr
    return None


def run_entropy_oracle_selection(
    session_path: str | Path,
    dataset_config: dict,
    model: torch.nn.Module,
    device: torch.device | str,
    current_iter: int,
    base_transform=None,
    max_per_class_per_frame: int = 1,
    batch_size: int = 8,
) -> dict:
    """Populate iteration_{current_iter+1}/annotations with entropy-oracle points.

    Loads the best model from ``iteration_{current_iter}/models/best_model.pth``,
    runs inference on all training images, computes per-pixel entropy, and picks
    the highest-entropy pixel per predicted class. Reads the GT label at each
    selected position and appends it to the next iteration's JSON annotations.
    Regenerates the corresponding PNG masks so ``run_training_iteration`` can
    consume them directly.

    Args:
        session_path: Path to the active-learning session directory.
        dataset_config: Parsed dataset metadata (num_classes, ignore_index, paths).
        model: Segmentation model instance with softmax activation.
        device: Torch device for inference.
        base_transform: Inference transform (no augmentation) matching training.
        current_iter: Iteration whose trained model guides the selection.
        base_transform: Optional inference transform. Rebuilt from dataset_config if None.
        max_per_class_per_frame: Budget per predicted class per frame (default 1).
        batch_size: Inference batch size.

    Returns:
        Summary dict with counts of frames processed, points added, and skip reasons.
    """
    session_path = Path(session_path)

    current_path = session_path / f"iteration_{current_iter}"
    next_path = session_path / f"iteration_{current_iter + 1}"
    next_annotations_dir = next_path / "annotations"
    next_masks_dir = next_path / "masks"

    if not next_annotations_dir.exists():
        raise FileNotFoundError(
            f"Expected {next_annotations_dir} to exist. "
            f"Run run_training_iteration(iteration={current_iter}) first "
            f"so it creates and pre-populates iter {current_iter + 1}."
        )

    model_path = current_path / "models" / "best_model.pth"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model at {model_path}")

    print(f"Loading model weights from iteration {current_iter}...")
    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()

    # Dataset configs use either `train_dense_masks` (yaml) or `train_masks`
    # (session dataset_metadata.json). Accept both.
    paths = dataset_config["paths"]
    gt_masks_key = "train_dense_masks" if "train_dense_masks" in paths else "train_masks"
    if gt_masks_key not in paths:
        raise KeyError(
            "dataset_config['paths'] must contain either 'train_dense_masks' "
            "or 'train_masks' pointing at the dense GT masks directory."
        )

    train_images_dir = _resolve_dataset_path(paths["train_images"])
    gt_masks_dir = _resolve_dataset_path(paths[gt_masks_key])
    print(f"  train_images: {train_images_dir}")
    print(f"  train_dense_masks: {gt_masks_dir}")

    num_classes = dataset_config["classes"]["num_classes"]
    ignore_index = dataset_config["classes"]["ignore_index"]

    if base_transform is None:
        base_transform = _build_base_transform(dataset_config)

    image_paths = sorted(
        list(train_images_dir.glob("*.png"))
        + list(train_images_dir.glob("*.tif"))
        + list(train_images_dir.glob("*.tiff"))
    )
    if not image_paths:
        raise FileNotFoundError(f"No training images in {train_images_dir}")

    dataset = PredictionDataset(image_paths, base_transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    stats = {
        "frames_processed": 0,
        "frames_without_gt": 0,
        "points_added": 0,
        "classes_empty_prediction": 0,
        "classes_gt_ignore": 0,
    }

    with torch.no_grad():
        for batch_images, batch_names in tqdm(loader, desc="Entropy-oracle"):
            batch_images = batch_images.to(device)
            batch_probs = model(batch_images).cpu().numpy()  # (B, C, H, W)

            for probs, img_name in zip(batch_probs, batch_names):
                stem = Path(img_name).stem
                json_path = next_annotations_dir / f"{stem}.json"

                if json_path.exists():
                    with open(json_path) as f:
                        data = json.load(f)
                else:
                    data = {
                        "format_version": "1.0",
                        "image": {
                            "name": f"{stem}.png",
                            "width": int(probs.shape[2]),
                            "height": int(probs.shape[1]),
                        },
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

                new_points, frame_stats = _select_points_for_frame(
                    probs=probs,
                    gt_mask=gt_mask,
                    num_classes=num_classes,
                    ignore_index=ignore_index,
                    existing_points=existing_points,
                    max_per_class=max_per_class_per_frame,
                )

                data["annotations"].extend(new_points)
                data["iteration"] = current_iter + 1
                data["created_at"] = datetime.now(timezone.utc).isoformat()

                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)

                stats["frames_processed"] += 1
                stats["points_added"] += len(new_points)
                stats["classes_empty_prediction"] += frame_stats["empty_prediction"]
                stats["classes_gt_ignore"] += frame_stats["gt_ignore"]

    # Rebuild masks from the updated JSONs so training can consume them.
    print("\nRegenerating PNG masks from updated annotations...")
    img_w = dataset_config["image"]["width"]
    img_h = dataset_config["image"]["height"]
    success, fail = batch_json_to_masks(
        json_dir=next_annotations_dir,
        output_dir=next_masks_dir,
        image_size=(img_w, img_h),
        ignore_index=ignore_index,
    )
    print(f"✓ Regenerated {success} masks ({fail} failed)")

    print("\nEntropy-oracle summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return stats
