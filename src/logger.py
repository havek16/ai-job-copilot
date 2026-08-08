"""
logger.py — Structured JSON logger for the agent pipeline.

Each step writes a log entry with step name, duration, and outcome.
Logs go to logs/agent_YYYY-MM-DD.log (one file per day).

Usage:
    from src.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Step started", extra={"step": "research", "duration_ms": 123})
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from src.config import config


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for easy machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via extra={...}
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ):
                log_entry[key] = value
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that writes JSON to both a dated log file and stdout.
    Idempotent — calling this twice with the same name returns the same logger.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # ── File handler ──────────────────────────────────────────────────────
    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_path = log_dir / f"agent_{date_str}.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # ── Console handler (plain text for readability during dev) ───────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(console_handler)

    return logger


def log_step(
    logger: logging.Logger,
    step_name: str,
    duration_ms: float,
    success: bool,
    error: str = "",
) -> None:
    """
    Convenience function to log a completed agent step with structured metadata.

    Args:
        logger:      The logger instance for the calling module.
        step_name:   Human-readable step name (e.g., "research", "fit_scoring").
        duration_ms: Wall-clock time the step took.
        success:     Whether the step completed without error.
        error:       Error message if success=False.
    """
    level = logging.INFO if success else logging.WARNING
    msg = f"Step '{step_name}' {'completed' if success else 'failed'} in {duration_ms:.1f}ms"
    logger.log(
        level,
        msg,
        extra={
            "step": step_name,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "error": error or None,
        },
    )
