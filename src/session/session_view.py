"""Read-only view of an iSAGE session on disk.

A session's filesystem layout is the source of truth:

    Sessions/<name>/
        iteration_0/
            annotations/   # JSON per image
            masks/         # PNG per image (generated from JSONs)
            models/        # best_model.pth after training
            predictions/   # PNG predictions after training
        iteration_1/
            ...
        metrics_history.csv

`SessionView` wraps that hierarchy so notebooks, scripts, and the
annotation tool can introspect a session without re-implementing the
same `os.path` and `glob` calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class IterationStatus:
    """Snapshot of what exists inside one ``iteration_N/`` directory."""

    number: int
    path: Path
    annotation_count: int
    mask_count: int
    has_model: bool
    prediction_count: int
    miou: Optional[float] = None
    pixel_accuracy: Optional[float] = None

    @classmethod
    def from_dir(cls, path: Path) -> "IterationStatus":
        number = int(path.name.split("_")[1])
        ann_dir = path / "annotations"
        mask_dir = path / "masks"
        pred_dir = path / "predictions"
        model_path = path / "models" / "best_model.pth"
        return cls(
            number=number,
            path=path,
            annotation_count=sum(1 for _ in ann_dir.glob("*.json")) if ann_dir.exists() else 0,
            mask_count=sum(1 for _ in mask_dir.glob("*.png")) if mask_dir.exists() else 0,
            has_model=model_path.exists(),
            prediction_count=sum(1 for _ in pred_dir.iterdir()) if pred_dir.exists() else 0,
        )

    @property
    def is_complete(self) -> bool:
        """True when annotations, masks, model, and predictions are all present."""
        return (
            self.annotation_count > 0
            and self.mask_count > 0
            and self.has_model
            and self.prediction_count > 0
        )


class SessionView:
    """Read-only inspection of a session directory.

    Construction is cheap (no I/O); each property reads the filesystem
    on access so the view always reflects current disk state.
    """

    def __init__(self, path):
        self.path = Path(path)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def exists(self) -> bool:
        return self.path.exists() and self.path.is_dir()

    @property
    def metrics_history(self) -> Optional[pd.DataFrame]:
        csv = self.path / "metrics_history.csv"
        if not csv.exists():
            return None
        try:
            return pd.read_csv(csv)
        except (pd.errors.EmptyDataError, OSError):
            return None

    @property
    def iterations(self) -> list[IterationStatus]:
        if not self.exists:
            return []
        dirs = sorted(
            (d for d in self.path.iterdir() if d.is_dir() and d.name.startswith("iteration_")),
            key=lambda p: int(p.name.split("_")[1]),
        )
        statuses = [IterationStatus.from_dir(d) for d in dirs]
        history = self.metrics_history
        if history is not None:
            miou_by_iter = dict(zip(history["iteration"], history["miou"]))
            pa_by_iter = (
                dict(zip(history["iteration"], history["pixel_accuracy"]))
                if "pixel_accuracy" in history.columns
                else {}
            )
            for s in statuses:
                s.miou = miou_by_iter.get(s.number)
                s.pixel_accuracy = pa_by_iter.get(s.number)
        return statuses

    @property
    def latest_iteration(self) -> Optional[IterationStatus]:
        its = self.iterations
        return its[-1] if its else None

    def summary_html(self) -> str:
        """HTML status block — used by the notebook widget."""
        if not self.exists:
            return (
                '<div style="color:#2a7;font-family:sans-serif;padding:4px 0">'
                "New session — clicking <b>Setup / Load</b> will create it.</div>"
            )
        its = self.iterations
        if not its:
            return (
                '<div style="color:#888;font-family:sans-serif;padding:4px 0">'
                "Session exists but has no iterations yet.</div>"
            )
        rows = [
            '<tr style="background:#f0f0f0">'
            "<th style='padding:4px 10px;text-align:right'>Iter</th>"
            "<th style='padding:4px 10px;text-align:right'>Annotations</th>"
            "<th style='padding:4px 10px;text-align:right'>Masks</th>"
            "<th style='padding:4px 10px;text-align:center'>Model</th>"
            "<th style='padding:4px 10px;text-align:right'>Predictions</th>"
            "<th style='padding:4px 10px;text-align:right'>val mIoU</th>"
            "</tr>"
        ]
        for s in its:
            model_icon = (
                '<span style="color:#2a7">&#10003;</span>'
                if s.has_model
                else '<span style="color:#888">&mdash;</span>'
            )
            miou = f"{s.miou:.4f}" if s.miou is not None else "&mdash;"
            rows.append(
                f"<tr>"
                f"<td style='padding:2px 10px;text-align:right'><b>{s.number}</b></td>"
                f"<td style='padding:2px 10px;text-align:right'>{s.annotation_count}</td>"
                f"<td style='padding:2px 10px;text-align:right'>{s.mask_count}</td>"
                f"<td style='padding:2px 10px;text-align:center'>{model_icon}</td>"
                f"<td style='padding:2px 10px;text-align:right'>{s.prediction_count}</td>"
                f"<td style='padding:2px 10px;text-align:right;color:#1f77b4'>{miou}</td>"
                f"</tr>"
            )
        table = (
            "<div style='font-family:monospace;font-size:11px;padding:4px 0'>"
            "<table style='border-collapse:collapse;border:1px solid #ddd'>"
            + "".join(rows)
            + "</table></div>"
        )
        return table


__all__ = ["SessionView", "IterationStatus"]
