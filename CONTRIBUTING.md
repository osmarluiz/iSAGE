# Contributing to iSAGE

Thanks for considering a contribution. The project is small and the bar
for code review is "does it work, is it tested, does it match the paper's
claims?"

## Reporting bugs

Open a [GitHub issue](https://github.com/osmarluiz/iSAGE/issues) with:

- Python version, OS, GPU.
- The dataset YAML you're using (or a reduced version that reproduces the issue).
- The traceback or the unexpected output, copied verbatim.
- If the annotator GUI is involved, the contents of `annotator_crash.log`
  (created in the repo root on PyQt5 crashes).

## Running tests locally

```bash
pip install pytest
pytest tests/ -v
```

The suite is hermetic — no real data or GPU required. CI on every push
runs the same suite on Python 3.10 and 3.11.

## Pull requests

Small focused PRs are easier to review than large ones. For new features,
open an issue first so we can agree on scope.

When you open a PR, the CI must pass. If your change touches the four
canonical subsystems (annotator, session storage, training backend, JSON
record format), please update the relevant doc in `docs/` as part of the
same PR.

## Scope guardrails

iSAGE deliberately omits some machinery that would otherwise be common in
similar projects. Please **don't** add the following without opening a
discussion first — they would re-introduce the very machinery the paper
argues against:

- Pseudo-labels from model predictions.
- CRF or superpixel propagation.
- Foundation-model labeling (SAM, CLIPSeg) as a default supervision source.
- Acquisition functions over model outputs as the canonical iteration step.

These are not forbidden in user code (the four falsification baselines in
`src/annotation/` use them), but they should not be wired into the default
workflow.
