# Changelog

All notable changes to iSAGE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project follows
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-06-08

Initial public release accompanying the arXiv preprint of
*iSAGE: Iterative Sparse Annotation Guided by Expert*
(Carvalho et al., 2026).

### Added (release-prep additions consolidated under 1.0.0)
- Test suite under `tests/` covering `SessionView` introspection, `Workflow`
  construction, val-optional dataloader, CLI argparse dispatch, and an
  end-to-end BYOT integration test on the BSB toy.
- GitHub Actions CI (`.github/workflows/test.yml`) running pytest on
  Python 3.10 and 3.11 with CPU-only torch wheels.
- `examples/bsb_toy/` — 30-patch BsB Aerial subset for a 3-minute
  reproducibility demo.
- Pluggable `Trainer` protocol (`src/training/trainer_protocol.py`) with
  the default `SmpTrainer` and a working alternative `TinyTorchTrainer`
  under `examples/byot/` that uses raw PyTorch with no
  `segmentation_models.pytorch` dependency.
- `docs/architecture.md` describing the four-subsystem decomposition,
  `docs/bring-your-own-trainer.md` describing the trainer contract,
  `docs/annotator-reference.md` listing every shortcut and panel of the
  PyQt5 annotator.
- `CITATION.cff` for GitHub citation rendering (arXiv preprint format,
  with placeholder `XXXX.XXXXX` until upload).
- Hero image and result figure embedded in `README.md`.

### Added (core platform)
- `src/workflow.py` — `Workflow` class, the single API every driver uses.
- `src/notebook_widgets.py` — `SessionPicker` widget for the Jupyter
  driver, including the "Create new dataset…" accordion.
- `cli.py` — terminal driver with `status` / `annotate` / `train` / `repl`
  subcommands and the `use <N>` REPL command.
- `src/session/session_view.py` — read-only filesystem introspection over
  a session directory.
- Val-optional training: `dataset_config['paths']['val_images']` and
  `val_masks` may be `null`. Per-epoch validation, `metrics_history.csv`,
  and val-mIoU-based best-model selection are all skipped — the
  final-epoch model is saved (matches the paper's §4.1 stance that "the
  model that ships is the one at the end of training").
- `isage_annotator/` — PyQt5 annotation GUI carved out of the broader
  VIZ_SOFTWARE platform; only the subsystem iSAGE depends on is shipped.
- `segmentation_models_pytorch/` — vendored fork with `EWDLBinary` and
  `EWDLMulticlass` added. Documented in `docs/smp-modifications.md`.
- `configs/datasets/` and `configs/training/` — paper recipes for BsB
  Aerial (binary and multiclass), Vaihingen 1k, and cross-architecture
  validation runs.
- `tools/launch_annotation_tool.py` — standalone annotator entry point
  used by both drivers via `subprocess`.
- `docs/` — JSON record spec, BYOD walkthrough, EWDL math and λ guidance,
  smp modifications, architecture overview.
