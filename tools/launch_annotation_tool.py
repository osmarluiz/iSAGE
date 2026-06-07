#!/usr/bin/env python3
"""
Standalone Annotation Tool Launcher

Launches the iSAGE annotation widget as a standalone application.
Can be called from Jupyter notebook or command line.

Usage:
    python tools/launch_annotation_tool.py --session Sessions/VAIHINGEN_EXPERIMENT --iteration 0
"""

import sys
import argparse
import logging
import faulthandler
import atexit
import signal
import os
import traceback
from pathlib import Path

# Force UTF-8 stdout/stderr so checkmark prints don't crash on Windows
# consoles using cp1252. No-op when streams already speak utf-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

# Crash/exit diagnostics. Mirror to a file because stderr is not captured
# by the .bat launcher.
_crash_log = open(
    Path(__file__).resolve().parent.parent / 'annotator_crash.log',
    'a',
    buffering=1,
)


def _log_exit(msg):
    _crash_log.write(msg + "\n")
    _crash_log.flush()


# 1. Faulthandler catches segfault/abort/etc.
faulthandler.enable(file=_crash_log, all_threads=True)

# 2. atexit fires for every normal interpreter shutdown (sys.exit, return).
@atexit.register
def _on_atexit():
    _log_exit(f"[atexit] interpreter shutting down, pid={os.getpid()}")
    stack = "".join(traceback.format_stack())
    _log_exit("[atexit] stack at shutdown:\n" + stack)


# 3. Catch unhandled exceptions in any thread.
def _log_uncaught(exc_type, exc_value, tb):
    _log_exit(f"[excepthook] {exc_type.__name__}: {exc_value}")
    _log_exit("".join(traceback.format_exception(exc_type, exc_value, tb)))


sys.excepthook = _log_uncaught
try:
    import threading
    threading.excepthook = lambda args: _log_uncaught(args.exc_type, args.exc_value, args.exc_traceback)
except Exception:
    pass


# 4. Catch signals on Windows.
def _log_signal(signum, frame):
    _log_exit(f"[signal] received signum={signum}")
    stack = "".join(traceback.format_stack(frame))
    _log_exit("[signal] stack:\n" + stack)
    os._exit(128 + signum)


for _sig in ("SIGINT", "SIGTERM", "SIGBREAK", "SIGABRT"):
    if hasattr(signal, _sig):
        try:
            signal.signal(getattr(signal, _sig), _log_signal)
        except (ValueError, OSError):
            pass

_log_exit(f"\n=== launcher start pid={os.getpid()} ===")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# NOTE: prepare_session_structure() and sync_annotations_back() removed.
# Annotator works directly with iteration_X/ structure - no sync needed!


def main():
    parser = argparse.ArgumentParser(description='Launch SIAL Annotation Tool')
    parser.add_argument('--session', type=str, required=True, help='Path to session (e.g., Sessions/VAIHINGEN_EXPERIMENT)')
    parser.add_argument('--iteration', type=int, required=True, help='Iteration number')

    args = parser.parse_args()

    session_path = Path(args.session)
    iteration = args.iteration

    # Validate session exists
    if not session_path.exists():
        logger.error(f"Session not found: {session_path}")
        sys.exit(1)

    logger.info(f"Launching annotation tool for session: {session_path}")
    logger.info(f"Iteration: {iteration}")

    # Add the annotator package to Python path
    annotator_path = Path(__file__).parent.parent / 'isage_annotator'
    if not annotator_path.exists():
        logger.error(f"isage_annotator not found at {annotator_path}")
        sys.exit(1)

    sys.path.insert(0, str(annotator_path))

    # Import PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        import PyQt5.QtCore
    except ImportError:
        logger.error("PyQt5 not installed. Install with: pip install PyQt5")
        sys.exit(1)

    # Import the annotation widget
    try:
        from domains.semantic_segmentation.active_learning.ui.annotation.widgets.shared_modules_annotation_widget import SharedModulesAnnotationWidget
    except ImportError as e:
        logger.error(f"Failed to import SharedModulesAnnotationWidget: {e}")
        sys.exit(1)

    # Create QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Create annotation widget
    logger.info("Creating annotation widget...")
    try:
        annotation_widget = SharedModulesAnnotationWidget(
            session_path=str(session_path),
            iteration=iteration,
            parent=None
        )

        # Set window title
        annotation_widget.setWindowTitle(f"SIAL Annotation Tool - Iteration {iteration}")

        # Show maximized
        annotation_widget.showMaximized()

        logger.info("Annotation tool window opened")
        logger.info("Close the window when you're done annotating")

        # Run application
        try:
            exit_code = app.exec_()
            _log_exit(f"[main] app.exec_() returned {exit_code}")
        except BaseException as ex:
            _log_exit(f"[main] app.exec_() raised {type(ex).__name__}: {ex}")
            _log_exit(traceback.format_exc())
            raise

        logger.info("Annotation session complete!")
        logger.info("Annotations saved directly to iteration_X/annotations/ (no sync needed)")
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Failed to launch annotation tool: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
