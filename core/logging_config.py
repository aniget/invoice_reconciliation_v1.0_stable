"""
core/logging_config.py — Centralised logging configuration.

Currently four different files call logging.basicConfig() independently
with different formats.  The last one to call it wins, which produces
inconsistent output and fights over the single debug.log file.

This module is the ONE place that configures the root logger.
Every other module should just do:

    import logging
    logger = logging.getLogger(__name__)

and never call basicConfig() itself.

Call setup_logging() once at application startup (in app.py main()).
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path, log_level: str = "INFO") -> None:
    """
    Configure the root logger with consistent formatting.

    Args:
        log_file:  Path where log records are written (in addition to stdout).
        log_level: String level name, e.g. "INFO", "DEBUG", "WARNING".
    """
    # Ensure the log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — persistent record
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Stream handler — developer console / Docker logs
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any handlers that were added before this call
    # (prevents duplicate lines if setup_logging is called more than once)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Silence overly chatty third-party loggers
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("gradio").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised — level=%s  file=%s", log_level, log_file
    )
