"""
CRF label selector — DenseCRF-based label propagation baseline.

Like pseudo_label_selector, this expands the supervision set across
iterations using the trained model's confident predictions. The
distinction is that the predictions are first refined by a DenseCRF
(Krähenbühl & Koltun, 2011) that smooths the softmax outputs using
RGB similarity and spatial proximity before the confidence threshold
is applied. The CRF unary potential is the model's softmax; the
pairwise potentials are a Gaussian (position) and a bilateral
(position + RGB) term with literature-standard hyperparameters.

This represents the "label propagation via image-similarity smoothing"
family — a distinct output-reading mechanism from pure self-training.
Both share the same underlying property: the new supervision signal
comes from a function over the model's outputs (and, here, the RGB
image), so confident model errors remain invisible.

Drop-in usage:

    run_training_iteration(iter=N)
    run_crf_label_selection(iter=N)           # writes CRF-refined mask for iter N+1
    run_training_iteration(iter=N+1)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

import pydensecrf.densecrf as dcrf
from pydensecrf.utils import unary_from_softmax

from src.training.workflow import PredictionDataset


def _build_base_transform(dataset_config: dict):
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
    p = Path(relative_path)
    if p.is_absolute() and p.exists():
        return p
    cwd = Path.cwd()
    for base in (cwd, cwd / "archive", cwd / "DATASETS"):
        candidate = base / p
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not locate dataset path '{relative_path}'.")


def _apply_densecrf(
    softmax: np.ndarray,
    rgb_image: np.ndarray,
    num_classes: int,
    sxy_gaussian: float = 3.0,
    compat_gaussian: float = 3.0,
    sxy_bilateral: float = 80.0,
    srgb_bilateral: float = 13.0,
    compat_bilateral: float = 10.0,
    iterations: int = 5,
) -> np.ndarray:
    """Apply DenseCRF inference to refine a per-pixel softmax distribution.

    Args:
        softmax: (C, H, W) array with each pixel's probabilities summing to 1.
        rgb_image: (H, W, 3) uint8 array used by the bilateral pairwise term.
        num_classes: number of classes C.
        sxy_gaussian, compat_gaussian: parameters of the Gaussian pairwise term.
        sxy_bilateral, srgb_bilateral, compat_bilateral: parameters of the
            bilateral pairwise term.
        iterations: number of CRF mean-field iterations.

    Returns:
        (C, H, W) array of refined probabilities.
    """
    C, H, W = softmax.shape
    softmax = np.ascontiguousarray(softmax.astype(np.float32))
    softmax = np.clip(softmax, 1e-8, 1.0)
    softmax /= softmax.sum(axis=0, keepdims=True)

    d = dcrf.DenseCRF2D(W, H, num_classes)

    U = unary_from_softmax(softmax)
    d.setUnaryEnergy(U)

    d.addPairwiseGaussian(sxy=(sxy_gaussian, sxy_gaussian), compat=compat_gaussian)

    rgb_image = np.ascontiguousarray(rgb_image[:, :, :3].astype(np.uint8))
    d.addPairwiseBilateral(
        sxy=(sxy_bilateral, sxy_bilateral),
        srgb=(srgb_bilateral, srgb_bilateral, srgb_bilateral),
        rgbim=rgb_image,
        compat=compat_bilateral,
    )

    Q = d.inference(iterations)
    refined = np.array(Q).reshape((num_classes, H, W))
    return refined


def run_crf_label_selection(
    session_path: str | Path,
    dataset_config: dict,
    model: torch.nn.Module,
    device: torch.device | str,
    current_iter: int,
    confidence_threshold: float = 0.95,
    base_transform=None,
    batch_size: int = 8,
) -> dict:
    """Densify iteration_{current_iter+1} masks with CRF-refined pseudo-labels.

    The model's softmax outputs are refined by DenseCRF (RGB + spatial
    pairwise terms) before the confidence threshold is applied. Seed
    annotations from iter_0 remain authoritative.
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
            f"Seed masks not found at {seed_masks_dir}."
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
    print(f"  CRF: Gaussian(sxy=3,compat=3) + Bilateral(sxy=80,srgb=13,compat=10), 5 iters")

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

    # Map name -> full path so we can re-load the raw RGB image for CRF pairwise term.
    name_to_path = {p.name: p for p in image_paths}

    stats = {
        "frames_processed": 0,
        "frames_without_seed_mask": 0,
        "total_seed_pixels": 0,
        "total_pseudo_labels": 0,
        "total_pixels": 0,
    }
    per_class_counts = np.zeros(num_classes, dtype=np.int64)

    with torch.no_grad():
        for batch_images, batch_names in tqdm(loader, desc="CRF-propagation"):
            batch_images = batch_images.to(device)
            batch_probs = model(batch_images).cpu().numpy()  # (B, C, H, W)

            for probs, img_name in zip(batch_probs, batch_names):
                stem = Path(img_name).stem
                seed_mask_path = seed_masks_dir / f"{stem}.png"
                if not seed_mask_path.exists():
                    stats["frames_without_seed_mask"] += 1
                    continue

                # Load original RGB (un-normalized) for CRF bilateral term.
                raw_path = name_to_path.get(img_name, None)
                if raw_path is None:
                    # Fall back to assuming PNG in train_images_dir
                    raw_path = train_images_dir / img_name
                rgb_image = np.array(Image.open(raw_path).convert("RGB"))

                # CRF refinement: softmax -> CRF-refined probabilities.
                refined = _apply_densecrf(probs, rgb_image, num_classes)

                seed_mask = np.array(Image.open(seed_mask_path))
                if seed_mask.ndim == 3:
                    seed_mask = seed_mask[..., 0]

                output_mask = seed_mask.copy()

                max_probs = refined.max(axis=0)
                pred_classes = refined.argmax(axis=0).astype(np.uint8)

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

    print("\nCRF-propagation summary:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    pseudo_density = stats["total_pseudo_labels"] / max(stats["total_pixels"], 1) * 100
    print(f"  CRF-refined pseudo-label density: {pseudo_density:.2f}% of pixels")
    print("  per-class pixel counts in output masks:")
    for c in range(num_classes):
        print(f"    class {c}: {per_class_counts[c]:,}")

    return {**stats, "per_class_counts": per_class_counts.tolist()}
