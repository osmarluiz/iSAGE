# iSAGE — Iterative Sparse Annotation Guided by Expert

iSAGE is a sparse-annotation platform for semantic segmentation. The annotator
sees the current model's predictions overlaid on the image and clicks on pixels
where the model is confidently wrong. The Error-Weighted Dice Loss (EWDL)
amplifies the gradient at those clicks during retraining, and an integrated
platform hosts inspection, annotation, retraining, and dataset maintenance as a
single continuous workflow. No pseudo-labels, no propagation, no consistency
regularization — each annotated pixel is exactly the supervision that reaches
the loss.

This repository releases the full platform that produced every experiment in
the paper. It is designed for re-use: any image dataset with enumerable
classes can be plugged in.

## What's inside

The platform comprises four subsystems, mirroring §3.4 of the paper:

| Subsystem | What it does | Where it lives |
|---|---|---|
| **Annotation interface** | PyQt5 widget showing image + prediction overlay; left-click adds a point, right-click removes | `isage_annotator/` |
| **Record storage** | One JSON file per image stores the full annotation history (coordinate, class) — auditable, diffable, portable | `Sessions/<name>/iteration_N/annotations/` (created at runtime) |
| **Session layout** | Each iteration is packaged as `iteration_N/{annotations,masks,models,predictions}/` so any past state can be reloaded or compared | `src/session/` |
| **Training backend** | Sparse dataloader (treats unlabeled pixels as ignore_index), EWDL, retraining loop, prediction generation | `src/training/` + `segmentation_models_pytorch/` (modified) |

## Quickstart

```bash
git clone https://github.com/osmarluiz/iSAGE.git
cd iSAGE
pip install -r requirements.txt
jupyter lab isage_workflow.ipynb
```

The notebook walks through the five-cell loop:

1. **Setup** — imports, GPU check.
2. **Configure** — load dataset + training YAMLs.
3. **Session** — create or resume a session.
4. **Annotate** — launches the PyQt5 widget; you click on errors; close window when done.
5. **Train** — runs EWDL retraining, generates predictions, advances to `iteration_{N+1}`.

After cell 5, jump back to cell 4 and the loop continues. The next iteration's
overlay reflects what the model just learned, so each round shows you where to
click next.

## Use your own dataset

Two files define a dataset:

- A YAML in `configs/datasets/` listing image paths, class names, colors, and `ignore_index`.
- A training YAML in `configs/training/` listing architecture, encoder, loss, and hyperparameters.

`configs/datasets/vaihingen_1k_v3.yaml` and `configs/training/unet_efficientnet_b7.yaml`
are the canonical examples. Copy them, edit the paths and class definitions,
point the notebook at the new YAML names, and run.

The platform is domain-agnostic by construction. Any image format that PIL
reads (PNG, JPG, TIFF, multi-band TIFF) and any class taxonomy that fits an
integer-indexed `(num_classes + 1)` scheme works.

See `docs/bring-your-own-data.md` for a step-by-step walkthrough.

## What this platform does NOT do

- It does **not** generate pseudo-labels from model predictions.
- It does **not** propagate clicks through CRFs, superpixels, or any spatial heuristic.
- It does **not** use foundation models (SAM, CLIPSeg) to densify supervision.
- It does **not** require a labeled validation set during training.

These omissions are deliberate — they are the experimental thesis of the paper.
Reintroducing them defeats the point. The four falsification baselines in
`src/annotation/` (entropy oracle, pseudo-labeling, CRF propagation, uniform
random) re-run the iSAGE protocol with each of these mechanisms in place so the
comparison can be made on the same model, schedule, and seed budget.

## Repository layout

```
.
├── isage_workflow.ipynb       Single-notebook orchestrator (5 cells)
├── src/
│   ├── annotation/            Launcher + four output-reading baselines
│   ├── session/               Session management + mask generator
│   ├── training/              EWDL training loop + dataloader
│   ├── datasets/, losses/, metrics/, utils/
├── isage_annotator/           PyQt5 annotation GUI
├── segmentation_models_pytorch/   Vendored, modified — contains EWDL
├── configs/
│   ├── datasets/              Per-dataset YAMLs
│   └── training/              Per-experiment YAMLs
├── tools/
│   └── launch_annotation_tool.py   Standalone annotator launcher
└── docs/                      json-record-spec, BYOD, EWDL, smp diff
```

## Hardware

- Annotation: any machine with a display (Linux/Mac/Windows; WSL works with X server).
- Training: GPU strongly recommended. Paper experiments used a single NVIDIA RTX 4090; smaller models (U-Net + EfficientNet-B0) train on 8 GB VRAM.

## Citing

If you use iSAGE in academic work, please cite:

```bibtex
@article{carvalho2026isage,
  title   = {iSAGE: Iterative Sparse Annotation Guided by Expert},
  author  = {Carvalho, Osmar Luiz Ferreira de and others},
  journal = {Expert Systems with Applications},
  year    = {2026},
  note    = {Under review}
}
```

A camera-ready BibTeX entry will replace the placeholder when the paper
appears. The associated paper repository (LaTeX source, figures, raw data
analysis scripts) is at <https://github.com/osmarluiz/sial-paper>.

## License

MIT — see `LICENSE`.

The vendored `segmentation_models_pytorch/` directory is a fork of the
upstream library [qubvel/segmentation_models.pytorch](https://github.com/qubvel/segmentation_models.pytorch)
(also MIT-licensed) with added loss functions, including EWDL. See
`docs/smp-modifications.md` for the diff against upstream.
