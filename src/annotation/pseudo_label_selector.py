"""
Pseudo-label selector — automated semi-supervised baseline.

Replaces human-in-the-loop annotation with self-training. After each
iteration's model trains, this selector runs inference on all training
images and adopts the model's high-confidence predictions as additional
supervision for the next iteration. Sparse seed annotations from iter_0
remain authoritative and are never overwritten.

This is the canonical "pseudo-labeling" baseline used in semi-supervised
semantic segmentation. It serves as a contrast to HITSS by exemplifying
what fully automated label propagation produces: the model reinforces
its own predictions, including confidently-wrong ones, and confirmation
bias accumulates across iterations.

Drop-in usage:

    run_training_iteration(iter=N)              # trains model N
    run_pseudo_label_selection(iter=N)          # writes pseudo-labeled mask for iter N+1
    run_training_iteration(iter=N+1)            # trains on sparse seeds + pseudo-labels
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

from src.training.workflow import PredictionDataset


def _build_base_transform(dataset_config: dict):
    """Reconstruct the inference transform used by create_dataloaders()."""
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


def _resolve_dataset_path(relative_path: str | Path) -> Path:
    """Resolve dataset paths against root, archive/, and DATASETS/."""
    p = Path(relative_path)
    if p.is_absolute() and p.exists():
        return p
    cwd = Path.cwd()
    for base in (cwd, cwd / "archive", cwd / "DATASETS"):
        candidate = base / p
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not locate dataset path '{relative_path}'.")


def run_pseudo_label_selection(
    session_path: str | Path,
    dataset_config: dict,
    model: torch.nn.Module,
    device: torch.device | str,
    current_iter: int,
    confidence_threshold: float = 0.95,
    base_transform=None,
    batch_size: int = 8,
) -> dict:
    """Densify iteration_{current_iter+1} masks with high-confidence pseudo-labels.

    Loads the best model from ``iteration_{current_iter}/models/best_model.pth``,
    runs inference on every training image, and writes a mask to
    ``iteration_{current_iter+1}/masks/`` that combines the original sparse
    seed annotations (from iteration 0) with pseudo-labels at every pixel
    where the model's maximum softmax probability exceeds
    ``confidence_threshold``. Pixels carrying a sparse seed label are never
    overwritten by a pseudo-label, even if the model disagrees.

    Args:
        session_path: Path to the active-learning session directory.
        dataset_config: Dataset metadata (num_classes, ignore_index, paths).
        model: Segmentation model with softmax activation.
        device: Torch device for inference.
        current_iter: Iteration whose trained model produces the pseudo-labels.
        confidence_threshold: Minimum max-probability for a pixel to receive
            a pseudo-label. Standard literature value is 0.95.
        base_transform: Optional inference transform; rebuilt from
            dataset_config when None.
        batch_size: Inference batch size.

    Returns:
        Summary dict with frame counts, total pseudo-labels, and per-class counts.
    """
    session_path = Path(session_path)

    current_path = session_path / f"iteration_{current_iter}"
    next_path = session_path / f"iteration_{current_iter + 1}"
    next_masks_dir = next_path / "masks"
    seed_masks_dir = session_path / "iteration_0" / "masks"

    if not next_path.exists():
        raise FileNotFoundError(
            f"Expected {next_path} to exist. "
            f"Run run_training_iteration(iteration={current_iter}) first."
        )

    if not seed_masks_dir.exists():
        raise FileNotFoundError(
            f"Seed masks not found at {seed_masks_dir}. "
            f"Pseudo-labeling needs the iter_0 sparse seeds as authoritative anchors."
        )

    next_masks_dir.mkdir(parents=True, exist_ok=True)

    model_path = current_path / "models" / "best_model.pth"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model at {model_path}")

    print(f"Loading model weights from iteration {current_iter}...")
    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()

    train_images_dir = _resolve_dataset_path(dataset_config["paths"]["train_images"])
    print(f"  train_images: {train_images_dir}")
    print(f"  seed_masks:   {seed_masks_dir}")
    print(f"  output_masks: {next_masks_dir}")
    print(f"  confidence threshold: {confidence_threshold}")

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
        "frames_without_seed_mask": 0,
        "total_seed_pixels": 0,
        "total_pseudo_labels": 0,
        "total_pixels": 0,
    }
    per_class_counts = np.zeros(num_classes, dtype=np.int64)

    with torch.no_grad():
        for batch_images, batch_names in tqdm(loader, desc="Pseudo-labeling"):
            batch_images = batch_images.to(device)
            batch_probs = model(batch_images).cpu().numpy()  # (B, C, H, W)

            for probs, img_name in zip(batch_probs, batch_names):
                stem = Path(img_name).stem

                seed_mask_path = seed_masks_dir / f"{stem}.png"
                if not seed_mask_path.exists():
                    stats["frames_without_seed_mask"] += 1
                    continue

                seed_mask = np.array(Image.open(seed_mask_path))
                if seed_mask.ndim == 3:
                    seed_mask = seed_mask[..., 0]

                # Start from the sparse seed; pseudo-labels fill ignore_index pixels.
                output_mask = seed_mask.copy()

                max_probs = probs.max(axis=0)  # (H, W)
                pred_classes = probs.argmax(axis=0).astype(np.uint8)  # (H, W)

                confident = max_probs > confidence_threshold
                ignore_only = output_mask == ignore_index
                pseudo_target = confident & ignore_only
                output_mask[pseudo_target] = pred_classes[pseudo_target]

                Image.fromarray(output_mask.astype(np.uint8)).save(
                    next_masks_dir / f"{stem}.png"
                )

                stats["frames_processed"] += 1
                stats["total_pixels"] += output_mask.size
                seed_count = int((seed_mask != ignore_index).sum())
                pseudo_count = int(pseudo_target.sum())
                stats["total_seed_pixels"] += seed_count
                stats["total_pseudo_labels"] += pseudo_count

                for c in range(num_classes):
                    per_class_counts[c] += int((output_mask == c).sum())

    print("\nPseudo-labeling summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    pseudo_density = stats["total_pseudo_labels"] / max(stats["total_pixels"], 1) * 100
    print(f"  pseudo-label density: {pseudo_density:.2f}% of pixels")
    print("  per-class pixel counts in output masks:")
    for c in range(num_classes):
        print(f"    class {c}: {per_class_counts[c]:,}")

    return {**stats, "per_class_counts": per_class_counts.tolist()}
