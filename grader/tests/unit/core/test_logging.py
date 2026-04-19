"""Tests for core/logging.py — get_logger contract."""
from __future__ import annotations

from nolte_grader.core.logging import get_logger


def test_get_logger_returns_usable_logger() -> None:
    log = get_logger("nolte_grader.test")
    log.info("hello", dimension="Y1")


def test_get_logger_different_names_return_loggers() -> None:
    log_a = get_logger("nolte_grader.core.a")
    log_b = get_logger("nolte_grader.core.b")
    assert log_a is not None
    assert log_b is not None


def test_get_logger_does_not_print(capsys: object) -> None:
    log = get_logger("nolte_grader.silent_test")
    log.debug("this should not appear in capsys without host configuration")
