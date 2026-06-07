"""CLI argparse + dispatch tests. Don't actually launch GUI or train."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


# Load cli.py as a regular module so we can hit its internals.
def _load_cli():
    cli_path = Path(__file__).resolve().parent.parent / "cli.py"
    spec = importlib.util.spec_from_file_location("isage_cli", cli_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_help_lists_subcommands(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py", "--help"])
    cli = _load_cli()
    with pytest.raises(SystemExit) as exc:
        cli.parse_args()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "status" in out
    assert "annotate" in out
    assert "train" in out
    assert "repl" in out


def test_cli_status_subcommand_takes_only_session(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "status", "--session", "/tmp/whatever"],
    )
    cli = _load_cli()
    args = cli.parse_args()
    assert args.cmd == "status"
    assert args.session == "/tmp/whatever"


def test_cli_repl_subcommand_requires_workflow_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py", "repl"])
    cli = _load_cli()
    with pytest.raises(SystemExit) as exc:
        cli.parse_args()
    assert exc.value.code == 2  # argparse missing-arg error


def test_cli_status_runs_on_nonexistent_session(monkeypatch, capsys, tmp_path):
    """status against a missing session should print a helpful note, not crash."""
    target = tmp_path / "noexist"
    monkeypatch.setattr(sys, "argv", ["cli.py", "status", "--session", str(target)])
    cli = _load_cli()
    exit_code = cli.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Session" in out


def test_cli_status_prints_table_for_existing_session(monkeypatch, capsys, tiny_session):
    monkeypatch.setattr(sys, "argv", ["cli.py", "status", "--session", str(tiny_session)])
    cli = _load_cli()
    exit_code = cli.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    # Header
    assert "Iter" in out
    assert "Ann" in out
    # Iter rows (we built 2 iters)
    assert "0" in out
    assert "1" in out


def test_cli_no_subcommand_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    cli = _load_cli()
    exit_code = cli.main()
    assert exit_code == 2
    out = capsys.readouterr().out
    assert "subcommand" in out.lower()


def test_cli_resolve_iteration_latest():
    cli = _load_cli()
    assert cli._resolve_iteration("latest") == "latest"
    assert cli._resolve_iteration("3") == 3


def test_cli_resolve_iteration_invalid_exits(monkeypatch, capsys):
    cli = _load_cli()
    with pytest.raises(SystemExit) as exc:
        cli._resolve_iteration("not_a_number")
    assert exc.value.code == 2
