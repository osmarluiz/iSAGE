# iSAGE architecture

iSAGE is structured as **four cooperating subsystems** that exchange one
artifact only: the session directory on disk. This separation is what makes
the same workflow runnable from a Jupyter widget, a CLI REPL, or a custom
Python script — every driver reads and writes the same files.

<p align="center">
  <img src="images/workflow.png" alt="iSAGE iterative workflow" width="800"/>
  <br/>
  <em>One iSAGE iteration. Solid arrows = data flow; dashed = human action.</em>
</p>

## The four subsystems

### 1. Annotation interface — `isage_annotator/`

PyQt5 application that displays one training image at a time with the
current model's prediction overlaid. Left-click adds a class point at the
exact pixel; right-click removes a nearby point. Pan, zoom, and a minimap
let the annotator navigate large patches.

Entry widget: `isage_annotator/domains/semantic_segmentation/active_learning/ui/annotation/widgets/shared_modules_annotation_widget.py`. Launched as a subprocess by
`tools/launch_annotation_tool.py`.

### 2. Record storage — JSON per image

Every click is persisted to a JSON file under
`Sessions/<name>/iteration_N/annotations/<image>.json`. The schema is
documented in [`docs/json-record-spec.md`](json-record-spec.md). One JSON
per source image; the schema makes the record:

- **auditable** — every supervision pixel is one line of JSON, locatable
  by image and iteration;
- **diffable** — `git diff` between two iterations shows exactly which
  pixels were added/removed/changed;
- **portable** — the JSONs plus the mask generator reconstruct the
  training supervision without the GUI or any UI state.

### 3. Session layout

A canonical filesystem tree:

```
Sessions/<name>/
├── iteration_0/
│   ├── annotations/   # JSON per image
│   ├── masks/         # PNG per image (regenerated from JSONs)
│   ├── models/        # best_model.pth after training
│   └── predictions/   # PNG predictions after training
├── iteration_1/
│   ├── ...
└── metrics_history.csv
```

This layout is the contract between drivers. The notebook, the CLI, and any
custom script all read and write the same paths. `src/session/session_view.py`
exposes a read-only `SessionView` class that derives every status property
from the filesystem.

### 4. Training backend — `src/training/` + vendored `segmentation_models_pytorch/`

`src/training/dataloader.py` builds a sparse-supervision dataloader: at every
labeled pixel, the loss is computed; at every unlabeled pixel (where mask
== `ignore_index`), the gradient is zero. `src/training/workflow.py` runs
the per-iteration loop — train, evaluate, save best checkpoint, generate
predictions, advance to the next iteration.

The Error-Weighted Dice Loss (`EWDLBinary`, `EWDLMulticlass`) lives in the
vendored `segmentation_models_pytorch/utils/losses.py`. See
[`docs/ewdl.md`](ewdl.md) for the math and λ guidance, and
[`docs/smp-modifications.md`](smp-modifications.md) for the upstream diff.

## The Workflow class — one API for every driver

`src/workflow.py` exposes a `Workflow` class that wires the four subsystems
together:

```python
from src.workflow import Workflow

wf = Workflow.from_config(
    dataset='configs/datasets/my.yaml',
    training='configs/training/unet_efficientnet_b7.yaml',
    session='Sessions/my_run',
    iteration='latest',
)
wf.annotate()          # subsystem 1 → 2 (interface writes JSONs)
wf.train()             # subsystem 4 reads 2 + 3 → updates 3
wf.view                # SessionView: read-only inspection of subsystem 3
wf.plot_progression()  # matplotlib chart from subsystem 3's CSV
```

Every driver in the repo (notebook widget, CLI REPL, programmatic script)
constructs this object and calls these methods. No business logic lives in
the drivers themselves.

## What makes the platform a platform

Each subsystem is **independently replaceable**:

- The annotator could be rewritten in any framework (Streamlit, web, etc.) — as long as it writes JSONs in the documented schema, the rest of the system doesn't notice.
- The training backend could swap the loss, the architecture, the encoder — as long as it reads `iteration_N/masks/` and writes `models/best_model.pth` + `predictions/`, the rest is unchanged.
- Sessions are portable: copy `Sessions/<name>/` to another machine, point the dataset YAML at the local image paths, and continue.

This is what makes the platform a research instrument: every experiment in
the paper was produced by composing the same four parts. Falsification
baselines (entropy oracle, pseudo-labeling, CRF propagation, uniform random)
in `src/annotation/` replace subsystem 1 with an automated selector — the
other three subsystems stay identical, so the comparison is on the
mechanism in slot 1, not on incidental implementation differences.
