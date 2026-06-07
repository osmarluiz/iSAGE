#!/usr/bin/env python3
"""CLI driver for an iSAGE session — the terminal equivalent of the notebook.

The notebook and this script are two drivers of the same ``Workflow`` API.
Switching between them is harmless: the session on disk is the source of
truth (the JSON annotation files and per-iteration directories), so you can
annotate from the CLI, train from the notebook, and switch back without
migrating anything. That property is the §3.1 claim of the paper made
operational.

Usage:

    python cli.py \\
        --dataset configs/datasets/vaihingen_1k_v3.yaml \\
        --training configs/training/unet_efficientnet_b7.yaml \\
        --session Sessions/my_run

After the workflow loads, a small REPL appears::

    [iter=latest] annotate | train | status | use <N> | quit > _

  - ``annotate``  Opens the PyQt5 annotator on the current iteration.
  - ``train``     Trains on the current iteration, generates predictions,
                  advances to the next iteration.
  - ``status``    Prints the iteration table for the session.
  - ``use <N>``   Switch the current iteration target. ``use 3`` operates on
                  ``iteration_3`` for subsequent annotate/train calls; ``use
                  latest`` returns to dynamic latest-iter targeting.
  - ``quit``      Exits.

You can also set the initial iteration with ``--iteration N`` instead of the
default ``latest``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path so 'from src.X import Y' resolves
sys.path.insert(0, str(Path(__file__).parent))

from src.workflow import Workflow  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="iSAGE CLI driver — annotate and train a session from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", required=True, help="Path to dataset YAML.")
    parser.add_argument("--training", required=True, help="Path to training YAML.")
    parser.add_argument("--session", required=True, help="Path to session directory (created if missing).")
    parser.add_argument(
        "--iteration",
        default="latest",
        help="Iteration to operate on. 'latest' or an integer. Default: latest.",
    )
    return parser.parse_args()


def print_status(workflow: Workflow) -> None:
    view = workflow.view
    if not view.exists or not view.iterations:
        print("  (no iterations yet)")
        return
    print(f"  {'Iter':>5} {'Ann':>8} {'Masks':>8} {'Model':>7} {'Preds':>8} {'val mIoU':>10}")
    print(f"  {'-'*5} {'-'*8} {'-'*8} {'-'*7} {'-'*8} {'-'*10}")
    for s in view.iterations:
        miou = f"{s.miou:.4f}" if s.miou is not None else "—"
        model = "✓" if s.has_model else "—"
        print(f"  {s.number:>5} {s.annotation_count:>8} {s.mask_count:>8} {model:>7} {s.prediction_count:>8} {miou:>10}")


def repl(workflow: Workflow) -> None:
    """Interactive command loop. Blocks until the user types 'quit' or hits EOF."""
    print()
    print(f"Session: {workflow.name}")
    print(f"Dataset: {workflow.dataset_config['name']}  ({workflow.dataset_config['classes']['num_classes']} classes)")
    print(f"Iteration: {workflow.iteration}")
    print()
    print_status(workflow)
    print()
    while True:
        try:
            cmd = input(f"[iter={workflow.iteration}] annotate | train | status | use <N> | quit > ").strip().lower()
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


def main():
    args = parse_args()
    print(f"Loading workflow…")
    workflow = Workflow.from_config(
        dataset=args.dataset,
        training=args.training,
        session=args.session,
        iteration=args.iteration if args.iteration == "latest" else int(args.iteration),
    )
    repl(workflow)
    print("Bye.")


if __name__ == "__main__":
    main()
