"""SessionView introspection tests. No torch/smp required."""

from pathlib import Path

import pytest

from src.session.session_view import IterationStatus, SessionView


def test_nonexistent_session():
    view = SessionView("/tmp/this_definitely_does_not_exist_xyz")
    assert view.exists is False
    assert view.iterations == []
    assert view.latest_iteration is None
    assert view.metrics_history is None
    # summary_html should produce a helpful message, not crash
    html = view.summary_html()
    assert isinstance(html, str)
    assert "create" in html.lower() or "new session" in html.lower()


def test_session_with_iterations(tiny_session):
    view = SessionView(tiny_session)
    assert view.exists is True
    assert view.name == tiny_session.name

    iters = view.iterations
    assert len(iters) == 2
    assert [s.number for s in iters] == [0, 1]

    iter0 = iters[0]
    assert iter0.annotation_count == 5
    assert iter0.mask_count == 5
    assert iter0.has_model is False
    assert iter0.prediction_count == 0
    assert iter0.miou == pytest.approx(0.42)

    iter1 = iters[1]
    assert iter1.annotation_count == 5
    assert iter1.mask_count == 5
    assert iter1.has_model is True
    assert iter1.prediction_count == 5
    # iter_1 not in metrics history yet — mIoU should be None
    assert iter1.miou is None


def test_latest_iteration(tiny_session):
    view = SessionView(tiny_session)
    latest = view.latest_iteration
    assert latest is not None
    assert latest.number == 1


def test_metrics_history_loaded(tiny_session):
    view = SessionView(tiny_session)
    df = view.metrics_history
    assert df is not None
    assert len(df) == 1
    assert df["iteration"].iloc[0] == 0


def test_summary_html_contains_iteration_table(tiny_session):
    view = SessionView(tiny_session)
    html = view.summary_html()
    assert "<table" in html
    # Should contain both iteration rows
    assert ">0<" in html  # iter 0
    assert ">1<" in html  # iter 1
    # Should reflect the mIoU value (0.4200)
    assert "0.4200" in html


def test_iteration_status_is_complete_flag(tiny_session):
    view = SessionView(tiny_session)
    iter0, iter1 = view.iterations
    # iter_0: no model, no predictions
    assert iter0.is_complete is False
    # iter_1: has annotations, masks, model, predictions
    assert iter1.is_complete is True


def test_iteration_status_from_dir(tiny_session):
    iter_path = tiny_session / "iteration_1"
    status = IterationStatus.from_dir(iter_path)
    assert status.number == 1
    assert status.has_model is True
    assert status.annotation_count == 5
