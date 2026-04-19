"""Logger factory. Core library's only logging entry point.

Entry points (CLI, webhook, embedded host) are responsible for configuring
structlog before invoking the grader. The core library never configures
loggers itself — no globals, no module-level state (spec §3.4).
"""
from __future__ import annotations

from typing import Any

import structlog


def get_logger(name: str) -> Any:
    """Return a named structured logger bound to ``name``.

    Safe to call before any host-side configuration; structlog returns a
    default-behaving logger until the host configures it.
    """
    return structlog.get_logger(name)
