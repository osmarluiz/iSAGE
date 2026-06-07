#!/usr/bin/env python3
"""CLI driver for an iSAGE session — the terminal equivalent of the notebook.

The notebook and this script are two drivers of the same ``Workflow`` API.
Switching between them is harmless: the session on disk is the source of
truth (the JSON annotation files and per-iteration directories), so you can
annotate from the CLI, train from the notebook, and switch back without
migrating anything. That property is the §3.1 claim of the paper made
operational.

Four subcommands, each scoped to what it actually needs:

    # Fast status (no model load, ~0.5s)
    python cli.py status --session Sessions/my_run

    # One-shot annotate (loads the model, opens the GUI, returns)
    python cli.py annotate \\
        --dataset configs/datasets/X.yaml \\
        --training configs/training/Y.yaml \\
        --session Sessions/my_run [--iteration N]

    # One-shot train (loads model, trains, advances iter)
    python cli.py train --dataset ... --training ... --session ... [--iteration N]

    # Interactive REPL (loads model once, multiple commands)
    python cli.py repl --dataset ... --training ... --session ... [--iteration N]

Running with no subcommand defaults to ``repl`` if all workflow args are
present, matching the previous one-mode behaviour.

REPL commands::

    [iter=latest] annotate | train | status | use <N> | quit > _

  - ``annotate``  Opens the PyQt5 annotator on the current iteration.
  - ``train``     Trains on the current iteration, generates predictions,
                  advances to the next iteration.
  - ``status``    Prints the iteration table for the session.
  - ``use <N>``   Switch the current iteration target. ``use 3`` operates on
                  ``iteration_3`` for subsequent annotate/train calls; ``use
                  latest`` returns to dynamic latest-iter targeting.
  - ``quit``      Exits.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path so 'from src.X import Y' resolves
sys.path.insert(0, str(Path(__file__).parent))

from src.session.session_view import SessionView  # noqa: E402
# NOTE: Workflow is lazily imported inside the subcommands that need it.
# Importing it eagerly pulls in torch + segmentation_models_pytorch (~1s of
# imports + GPU init), which `status` does not need.


# ---- arg parsing -----------------------------------------------------------


def _add_workflow_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--dataset", required=True, help="Path to dataset YAML.")
    sub.add_argument("--training", required=True, help="Path to training YAML.")
    sub.add_argument("--session", required=True, help="Path to session directory (created if missing).")
    sub.add_argument(
        "--iteration", default="latest",
        help="Iteration to operate on. 'latest' or an integer. Default: latest.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="iSAGE CLI driver — annotate and train a session from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", metavar="{status,annotate,train,repl}")

    p_status = sub.add_parser(
        "status",
        help="Print the iteration table for a session (no model load — fast).",
    )
    p_status.add_argument("--session", required=True, help="Path to session directory.")

    p_ann = sub.add_parser(
        "annotate",
        help="Load the model and open the PyQt5 annotator on the iteration.",
    )
    _add_workflow_args(p_ann)

    p_train = sub.add_parser(
        "train",
        help="Load the model and train on the iteration; advance to next iter.",
    )
    _add_workflow_args(p_train)

    p_repl = sub.add_parser(
        "repl",
        help="Load the model once and enter an interactive command loop.",
    )
    _add_workflow_args(p_repl)

    return parser.parse_args()


# ---- helpers ---------------------------------------------------------------


def _resolve_iteration(value: str):
    if value == "latest":
        return "latest"
    try:
        return int(value)
    except ValueError:
        print(f"--iteration must be 'latest' or an integer, got: {value!r}")
        sys.exit(2)


def print_status_view(view: SessionView) -> None:
    """Print the iteration table for an arbitrary SessionView. Used by the
    `status` subcommand (no model load) and by the REPL `status` command."""
    if not view.exists:
        print(f"  (session does not exist yet: {view.path})")
        return
    if not view.iterations:
        print("  (no iterations yet)")
        return
    print(f"  {'Iter':>5} {'Ann':>8} {'Masks':>8} {'Model':>7} {'Preds':>8} {'val mIoU':>10}")
    print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*10}")
    for s in view.iterations:
        miou = f"{s.miou:.4f}" if s.miou is not None else "—"
        model = "✓" if s.has_model else "—"
        print(f"  {s.number:>5} {s.annotation_count:>8} {s.mask_count:>8} {model:>7} {s.prediction_count:>8} {miou:>10}")


def print_status(workflow) -> None:
    """Convenience wrapper kept for backwards compatibility with the REPL."""
    print_status_view(workflow.view)


# ---- subcommand implementations --------------------------------------------


def cmd_status(args) -> int:
    view = SessionView(args.session)
    print(f"Session: {view.path}")
    print_status_view(view)
    return 0


def _build_workflow(args):
    from src.workflow import Workflow  # lazy: avoid torch import on status
    return Workflow.from_config(
        dataset=args.dataset,
        training=args.training,
        session=args.session,
        iteration=_resolve_iteration(args.iteration),
    )


def cmd_annotate(args) -> int:
    print("Loading workflow…")
    workflow = _build_workflow(args)
    workflow.annotate()
    return 0


def cmd_train(args) -> int:
    print("Loading workflow…")
    workflow = _build_workflow(args)
    workflow.train()
    print()
    print_status(workflow)
    return 0


def cmd_repl(args) -> int:
    print("Loading workflow…")
    workflow = _build_workflow(args)
    repl(workflow)
    return 0


# ---- REPL ------------------------------------------------------------------


def repl(workflow) -> None:
    """Interactive command loop. Blocks until 'quit' or EOF."""
    print()
    print(f"Session: {workflow.name}")
    print(f"Dataset: {workflow.dataset_config['name']}  ({workflow.dataset_config['classes']['num_classes']} classes)")
    print(f"Iteration: {workflow.iteration}")
    print()
    print_status(workflow)
    print()
    while True:
        try:
            cmd = input(
                f"[iter={workflow.iteration}] annotate | train | status | use <N> | quit > "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd in ("q", "quit", "exit"):
            break
        if cmd in ("a", "annotate"):
            print()
            workflow.annotate()
            print()
        elif cmd in ("t", "train"):
            print()
            workflow.train()
            print()
            print_status(workflow)
            print()
        elif cmd in ("s", "status"):
            print()
            print_status(workflow)
            print()
        elif cmd.startswith("use "):
            target = cmd[4:].strip()
            if target == "latest":
                workflow.iteration = "latest"
                print(f"  → now targeting: latest\n")
            else:
                try:
                    n = int(target)
                    iters = workflow.view.iterations
                    valid = [s.number for s in iters]
                    if n not in valid:
                        print(f"  iteration {n} does not exist. Available: {valid}\n")
                    else:
                        workflow.iteration = n
                        print(f"  → now targeting: iteration_{n}\n")
                except ValueError:
                    print(f"  use expects an integer or 'latest', got: {target!r}\n")
        elif cmd == "":
            continue
        else:
            print(f"Unknown command: {cmd!r}. Type 'annotate', 'train', 'status', 'use <N>', or 'quit'.")


# ---- entry -----------------------------------------------------------------


def main() -> int:
    args = parse_args()
    if args.cmd is None:
        # Backwards compat: no subcommand defaults to repl when workflow args
        # are present, otherwise prints help.
        if hasattr(args, "dataset") and args.dataset:
            return cmd_repl(args)
        print("No subcommand given. Try one of:")
        print("  python cli.py status   --session ...")
        print("  python cli.py annotate --dataset ... --training ... --session ...")
        print("  python cli.py train    --dataset ... --training ... --session ...")
        print("  python cli.py repl     --dataset ... --training ... --session ...")
        print("\nUse --help on any subcommand for details.")
        return 2

    dispatch = {
        "status": cmd_status,
        "annotate": cmd_annotate,
        "train": cmd_train,
        "repl": cmd_repl,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
