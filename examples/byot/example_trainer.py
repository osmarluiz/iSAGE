"""Bring-your-own-trainer example.

A minimal trainer that respects the iSAGE Trainer contract without using
``segmentation_models.pytorch``. Useful as a template if you want to plug
in PyTorch Lightning, monai, fastai, MMSegmentation, or any framework of
your own.

The trainer below uses raw PyTorch with a small ad-hoc U-Net so the file
stands on its own without external segmentation-library dependencies.
Swap the network class and the optimization loop for whatever you prefer;
the contract with iSAGE is just:

    iteration_N/masks/  →  read
    iteration_N/models/best_model.pth   →  write
    iteration_N/predictions/    →  write (one PNG per training image)
    iteration_{N+1}/{annotations,masks,models,predictions}/    →  create
    metrics_history.csv     →  append one row (optional)

Run with:

    from src.workflow import Workflow
    from examples.byot.example_trainer import TinyTorchTrainer

    wf = Workflow.from_config(
        dataset='configs/datasets/my.yaml',
        training='configs/training/unet_efficientnet_b7.yaml',   # any YAML; only num_classes matters
        session='Sessions/byot_run',
        trainer=TinyTorchTrainer(num_epochs=5, lr=1e-3),
    )
    wf.train()
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset

IterationSpec = Union[int, str]


# ---------------------------------------------------------------------------
# A tiny U-Net so the example does not depend on segmentation_models.pytorch.
# ---------------------------------------------------------------------------

class _DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class _TinyUNet(nn.Module):
    def __init__(self, num_classes: int, in_channels: int = 3):
        super().__init__()
        self.e1 = _DoubleConv(in_channels, 16)
        self.e2 = _DoubleConv(16, 32)
        self.bottleneck = _DoubleConv(32, 64)
        self.u2 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.d2 = _DoubleConv(64, 32)
        self.u1 = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.d1 = _DoubleConv(32, 16)
        self.head = nn.Conv2d(16, num_classes, 1)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(F.max_pool2d(e1, 2))
        b = self.bottleneck(F.max_pool2d(e2, 2))
        d2 = self.d2(torch.cat([self.u2(b), e2], dim=1))
        d1 = self.d1(torch.cat([self.u1(d2), e1], dim=1))
        return self.head(d1)


# ---------------------------------------------------------------------------
# Dataset that respects the iSAGE convention.
# ---------------------------------------------------------------------------

class _SparseSegDataset(Dataset):
    def __init__(self, image_dir: Path, mask_dir: Path, ignore_index: int):
        self.images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".tiff", ".tif"))
        self.mask_dir = mask_dir
        self.ignore_index = ignore_index

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img = np.asarray(Image.open(self.images[idx]).convert("RGB"), dtype=np.float32) / 255.0
        mask = np.asarray(Image.open(self.mask_dir / self.images[idx].with_suffix(".png").name), dtype=np.int64)
        return torch.from_numpy(img).permute(2, 0, 1), torch.from_numpy(mask)


# ---------------------------------------------------------------------------
# The Trainer protocol implementation.
# ---------------------------------------------------------------------------

class TinyTorchTrainer:
    """A minimal trainer demonstrating the Trainer protocol.

    Builds a tiny U-Net, trains for a configurable number of epochs with
    a cross-entropy loss that ignores unlabeled pixels (via ``ignore_index``),
    writes a model checkpoint, generates predictions, advances the iteration,
    and appends a metrics row.
    """

    def __init__(self, num_epochs: int = 10, lr: float = 1e-3, batch_size: int = 4):
        self.num_epochs = num_epochs
        self.lr = lr
        self.batch_size = batch_size

    def train_one_iteration(
        self,
        *,
        session_path: Path,
        dataset_config: dict,
        iteration: IterationSpec = "latest",
        visualize: bool = False,
    ) -> dict:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Resolve 'latest' to a concrete iteration number
        if iteration == "latest":
            iters = sorted(int(p.name.split("_")[1]) for p in session_path.iterdir()
                           if p.is_dir() and p.name.startswith("iteration_"))
            iteration = iters[-1] if iters else 0
        iter_path = session_path / f"iteration_{iteration}"

        # Read inputs
        image_dir = Path(dataset_config["paths"]["train_images"])
        mask_dir = iter_path / "masks"
        num_classes = dataset_config["classes"]["num_classes"]
        ignore_index = dataset_config["classes"]["ignore_index"]

        # Train
        model = _TinyUNet(num_classes=num_classes).to(device)
        ds = _SparseSegDataset(image_dir, mask_dir, ignore_index)
        dl = DataLoader(ds, batch_size=self.batch_size, shuffle=True)
        opt = torch.optim.Adam(model.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss(ignore_index=ignore_index)

        model.train()
        last_loss = 0.0
        for epoch in range(self.num_epochs):
            epoch_loss = 0.0
            for imgs, masks in dl:
                imgs, masks = imgs.to(device), masks.to(device)
                opt.zero_grad()
                logits = model(imgs)
                loss = criterion(logits, masks)
                loss.backward()
                opt.step()
                epoch_loss += loss.item()
            last_loss = epoch_loss / max(len(dl), 1)
            print(f"  epoch {epoch+1}/{self.num_epochs}  loss={last_loss:.4f}")

        # Write model checkpoint
        models_dir = iter_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), models_dir / "best_model.pth")

        # Write predictions
        pred_dir = iter_path / "predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        model.eval()
        with torch.no_grad():
            for img_path in ds.images:
                img = np.asarray(Image.open(img_path).convert("RGB"), dtype=np.float32) / 255.0
                t = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(device)
                pred = model(t).argmax(dim=1).cpu().numpy()[0].astype(np.uint8)
                Image.fromarray(pred).save(pred_dir / img_path.with_suffix(".png").name)

        # Advance the iteration: create iteration_{N+1}/ and copy annotations
        next_iter_path = session_path / f"iteration_{iteration + 1}"
        for sub in ("annotations", "masks", "models", "predictions"):
            (next_iter_path / sub).mkdir(parents=True, exist_ok=True)
        for j in (iter_path / "annotations").glob("*.json"):
            shutil.copy(j, next_iter_path / "annotations" / j.name)

        # Optionally append a metrics row
        csv_path = session_path / "metrics_history.csv"
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["iteration", "miou", "pixel_accuracy", "train_loss", "val_loss"])
            # No val pass in this minimal example; record train_loss only.
            w.writerow([iteration, "", "", f"{last_loss:.6f}", ""])

        return {
            "iteration": iteration,
            "success": True,
            "train_loss": last_loss,
            "next_iteration": iteration + 1,
            "message": "TinyTorchTrainer iteration complete",
        }
