"""Jupyter widgets for the iSAGE notebook driver.

These widgets are one of two ways to drive the iSAGE workflow. The other is
the CLI (``cli.py`` at the repo root). Both call the same ``Workflow``
class — the widgets are pure UX, no platform logic lives here.

Typical use in a notebook cell::

    from src.notebook_widgets import SessionPicker
    picker = SessionPicker.display()
    # user fills in dropdowns and clicks Setup / Load
    # then in the next cell:
    picker.workflow.annotate()
    picker.workflow.train()
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import ipywidgets as W
from IPython.display import display, clear_output

from src.session.session_view import SessionView
from src.workflow import Workflow


_DATASETS_DIR = Path("configs/datasets")
_TRAININGS_DIR = Path("configs/training")
_SESSIONS_DIR = Path("Sessions")


def _scan_yamls(folder: Path) -> List[str]:
    return sorted(f.name for f in folder.glob("*.yaml")) if folder.exists() else []


def _scan_sessions() -> List[str]:
    return sorted(d.name for d in _SESSIONS_DIR.iterdir() if d.is_dir()) if _SESSIONS_DIR.exists() else []


class SessionPicker:
    """Interactive picker that builds a Workflow when the user clicks Setup / Load.

    After the user clicks the button, ``self.workflow`` is bound to a fresh
    ``Workflow`` instance, the widget collapses to a one-line summary, and
    later cells can use ``picker.workflow.annotate()`` / ``.train()``.

    Construct via the ``display()`` classmethod — never call ``__init__``
    directly from a notebook cell.
    """

    def __init__(self):
        self.workflow: Optional[Workflow] = None
        self._container: Optional[W.Box] = None
        self._build()

    # ---- public --------------------------------------------------------

    @classmethod
    def display(cls) -> "SessionPicker":
        """Build the widget, render it, and return the picker.

        The returned object's ``.workflow`` attribute starts at ``None`` and
        is populated when the user clicks Setup / Load.
        """
        picker = cls()
        display(picker._container)
        return picker

    # ---- construction --------------------------------------------------

    def _build(self):
        layout_wide = W.Layout(width="620px")
        style_lbl = {"description_width": "110px"}

        dataset_options = _scan_yamls(_DATASETS_DIR)
        training_options = _scan_yamls(_TRAININGS_DIR)
        sessions = _scan_sessions()

        default_training = (
            "unet_efficientnet_b7.yaml"
            if "unet_efficientnet_b7.yaml" in training_options
            else (training_options[0] if training_options else None)
        )

        self._dataset = W.Dropdown(
            options=dataset_options,
            value=dataset_options[0] if dataset_options else None,
            description="Dataset:",
            layout=layout_wide,
            style=style_lbl,
        )
        self._training = W.Dropdown(
            options=training_options,
            value=default_training,
            description="Training:",
            layout=layout_wide,
            style=style_lbl,
        )
        self._session = W.Combobox(
            options=sessions,
            value=sessions[0] if sessions else "my_run",
            placeholder="session name",
            description="Session:",
            layout=layout_wide,
            style=style_lbl,
            ensure_option=False,
        )
        self._status = W.HTML(value="")
        self._iteration = W.Dropdown(
            options=[("latest", "latest")],
            value="latest",
            description="Use iter:",
            layout=layout_wide,
            style=style_lbl,
        )
        self._submit = W.Button(
            description="Setup / Load",
            button_style="primary",
            icon="play",
            layout=W.Layout(width="220px"),
        )
        self._out = W.Output()

        self._session.observe(self._refresh_status, names="value")
        self._submit.on_click(self._on_submit)
        self._refresh_status()

        self._accordion = self._build_new_dataset_accordion()

        self._container = W.VBox([
            self._dataset,
            self._training,
            self._session,
            self._status,
            self._iteration,
            self._submit,
            self._out,
            self._accordion,
        ])

    def _build_new_dataset_accordion(self) -> W.Accordion:
        wide = W.Layout(width="540px")
        style = {"description_width": "140px"}

        self._new_name = W.Text(placeholder="my_dataset", description="Name:", layout=wide, style=style)
        self._new_train = W.Text(placeholder="/path/to/images", description="Train images dir:", layout=wide, style=style)
        self._new_val = W.Text(placeholder="(optional)", description="Val images dir:", layout=wide, style=style)
        self._new_valm = W.Text(placeholder="(optional)", description="Val masks dir:", layout=wide, style=style)
        self._new_classes = W.Textarea(
            placeholder="road\nbuilding\nvegetation",
            description="Class names:",
            layout=W.Layout(width="540px", height="90px"),
            style=style,
        )
        self._new_btn = W.Button(
            description="Create dataset YAML",
            button_style="success",
            icon="plus",
            layout=W.Layout(width="260px"),
        )
        self._new_status = W.HTML(value="")
        self._new_btn.on_click(self._on_create_dataset)

        form = W.VBox([
            self._new_name, self._new_train, self._new_val, self._new_valm,
            self._new_classes, self._new_btn, self._new_status,
        ])
        accordion = W.Accordion(children=[form])
        accordion.set_title(0, "Create new dataset…")
        accordion.selected_index = None
        return accordion

    # ---- handlers ------------------------------------------------------

    def _refresh_status(self, change=None):
        view = SessionView(_SESSIONS_DIR / self._session.value)
        self._status.value = view.summary_html()
        if view.exists and view.iterations:
            opts = [("latest", "latest")] + [(f"iteration_{s.number}", s.number) for s in view.iterations]
        else:
            opts = [("latest", "latest")]
        self._iteration.options = opts
        self._iteration.value = "latest"

    def _on_submit(self, _):
        with self._out:
            clear_output()
            try:
                self.workflow = Workflow.from_config(
                    dataset=_DATASETS_DIR / self._dataset.value,
                    training=_TRAININGS_DIR / self._training.value,
                    session=_SESSIONS_DIR / self._session.value,
                    iteration=self._iteration.value,
                )
                self._collapse_to_summary()
            except Exception as e:
                import traceback
                print(f"FAILED: {type(e).__name__}: {e}")
                traceback.print_exc()

    def _collapse_to_summary(self):
        """Replace the picker UI with a one-line summary after successful load."""
        wf = self.workflow
        view = wf.view
        latest_n = view.latest_iteration.number if view.latest_iteration else None
        latest_str = f"iter {latest_n}" if latest_n is not None else "no iterations yet"
        iter_str = (
            f"latest ({latest_str})" if self._iteration.value == "latest"
            else f"iteration_{self._iteration.value}"
        )
        summary = W.HTML(value=(
            '<div style="padding:8px;background:#f0f9f0;border:1px solid #2a7;'
            'border-radius:4px;font-family:sans-serif">'
            f'<b>Loaded:</b> session <code>{wf.name}</code> &middot; '
            f'dataset <code>{wf.dataset_config["name"]}</code> &middot; '
            f'using {iter_str}'
            '</div>'
        ))
        self._container.children = (summary,)

    def _on_create_dataset(self, _):
        import yaml
        import matplotlib.pyplot as plt
        from PIL import Image

        name = self._new_name.value.strip()
        train_p = self._new_train.value.strip()
        val_p = self._new_val.value.strip() or None
        valm_p = self._new_valm.value.strip() or None
        class_list = [c.strip() for c in self._new_classes.value.split("\n") if c.strip()]

        if not name or not train_p or not class_list:
            self._new_status.value = (
                '<span style="color:#c00">Name, train images path, and class names are required.</span>'
            )
            return
        train_dir = Path(train_p)
        if not train_dir.exists():
            self._new_status.value = (
                f'<span style="color:#c00">Train images path does not exist: {train_dir}</span>'
            )
            return
        samples = (
            sorted(train_dir.glob("*.png"))
            + sorted(train_dir.glob("*.tif"))
            + sorted(train_dir.glob("*.tiff"))
            + sorted(train_dir.glob("*.jpg"))
        )
        if not samples:
            self._new_status.value = (
                f'<span style="color:#c00">No images found in {train_dir}</span>'
            )
            return

        with Image.open(samples[0]) as img:
            width, height = img.size
            channels = len(img.getbands())

        num_classes = len(class_list)
        cmap = plt.get_cmap("tab10" if num_classes <= 10 else "tab20")
        colors = [[int(255 * c) for c in cmap(i)[:3]] for i in range(num_classes)]

        yaml_obj = {
            "name": name.upper(),
            "paths": {
                "train_images": str(train_dir),
                "train_dense_masks": None,
                "train_sparse_masks": str(Path("Sessions") / name / "sparse_masks"),
                "val_images": val_p,
                "val_masks": valm_p,
                "test_images": None,
                "test_masks": None,
            },
            "classes": {
                "num_classes": num_classes,
                "ignore_index": num_classes,
                "names": class_list,
                "colors": colors,
            },
            "image": {"width": width, "height": height, "channels": channels},
        }

        yaml_path = _DATASETS_DIR / f"{name}.yaml"
        if yaml_path.exists():
            self._new_status.value = (
                f'<span style="color:#c00">{yaml_path.name} already exists — pick another name.</span>'
            )
            return
        with open(yaml_path, "w") as f:
            yaml.safe_dump(yaml_obj, f, default_flow_style=False, sort_keys=False)

        val_note = "" if val_p else " (no validation — that is fine)"
        self._new_status.value = (
            f'<span style="color:#2a7"><b>Created {yaml_path.name}</b> — '
            f'{len(samples)} images, {width}×{height}×{channels}{val_note}</span>'
        )
        # Refresh dataset dropdown and select the new YAML
        self._dataset.options = _scan_yamls(_DATASETS_DIR)
        self._dataset.value = yaml_path.name


__all__ = ["SessionPicker"]
