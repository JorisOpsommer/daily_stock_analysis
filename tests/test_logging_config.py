# -*- coding: utf-8 -*-
"""Regression tests for application logging configuration."""

import logging

import pytest

from src.logging_config import LITELLM_LOGGERS, DailyRotatingFileHandler, setup_logging


@pytest.fixture(autouse=True)
def restore_logging_state():
    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    original_handlers = list(root_logger.handlers)
    original_litellm_levels = {
        logger_name: logging.getLogger(logger_name).level
        for logger_name in LITELLM_LOGGERS
    }

    yield

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        if handler not in original_handlers:
            handler.close()
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_root_level)

    for logger_name, level in original_litellm_levels.items():
        logging.getLogger(logger_name).setLevel(level)


def _read_debug_log(log_dir) -> str:
    for handler in logging.getLogger().handlers:
        handler.flush()
    debug_log = next(log_dir.glob("stock_analysis_debug_*.log"))
    return debug_log.read_text(encoding="utf-8")


def test_log_format_includes_logger_name(tmp_path, monkeypatch):
    monkeypatch.delenv("LITELLM_LOG_LEVEL", raising=False)

    setup_logging(log_prefix="stock_analysis", log_dir=str(tmp_path), debug=False)

    logging.getLogger("src.sample").info("logger context smoke")

    debug_log_text = _read_debug_log(tmp_path)
    assert " | src.sample | " in debug_log_text
    assert "logger context smoke" in debug_log_text


@pytest.mark.parametrize("env_value", [None, "", "  "])
def test_litellm_debug_is_quiet_by_default_and_empty_env(tmp_path, monkeypatch, env_value):
    if env_value is None:
        monkeypatch.delenv("LITELLM_LOG_LEVEL", raising=False)
    else:
        monkeypatch.setenv("LITELLM_LOG_LEVEL", env_value)

    setup_logging(log_prefix="stock_analysis", log_dir=str(tmp_path), debug=False)

    for logger_name in LITELLM_LOGGERS:
        logging.getLogger(logger_name).debug("%s token debug should be filtered", logger_name)
    logging.getLogger("LiteLLM").warning("litellm warning should remain")
    logging.getLogger("src.sample").debug("project debug should remain")

    debug_log_text = _read_debug_log(tmp_path)

    for logger_name in LITELLM_LOGGERS:
        assert f"{logger_name} token debug should be filtered" not in debug_log_text
    assert "litellm warning should remain" in debug_log_text
    assert "project debug should remain" in debug_log_text


def test_litellm_log_level_debug_restores_litellm_debug(tmp_path, monkeypatch):
    monkeypatch.setenv("LITELLM_LOG_LEVEL", "DEBUG")

    setup_logging(log_prefix="stock_analysis", log_dir=str(tmp_path), debug=False)

    for logger_name in LITELLM_LOGGERS:
        logging.getLogger(logger_name).debug("%s debug should remain", logger_name)

    debug_log_text = _read_debug_log(tmp_path)

    for logger_name in LITELLM_LOGGERS:
        assert f"{logger_name} debug should remain" in debug_log_text


def test_invalid_litellm_log_level_falls_back_to_warning(tmp_path, monkeypatch):
    monkeypatch.setenv("LITELLM_LOG_LEVEL", "verbose")

    setup_logging(log_prefix="stock_analysis", log_dir=str(tmp_path), debug=False)

    logging.getLogger("LiteLLM").debug("invalid level debug should be filtered")
    logging.getLogger("LiteLLM").warning("invalid level warning should remain")

    debug_log_text = _read_debug_log(tmp_path)

    assert "invalid level debug should be filtered" not in debug_log_text
    assert "invalid level warning should remain" in debug_log_text
    assert "LITELLM_LOG_LEVEL" in debug_log_text
    assert "已回退为 WARNING" in debug_log_text


def test_daily_rotating_handler_rolls_to_new_dated_file_on_day_change(tmp_path):
    handler = DailyRotatingFileHandler(
        tmp_path, prefix="stock_analysis", backup_count=5, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("test_daily_rotation")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    current_day = handler._current_day()

    logger.info("same day line")

    # 模拟日期变更：伪造内部记录的日期为过去，下一次 emit 应滚动到新日期文件
    handler._today = "19000101"
    logger.info("after midnight line")

    files = sorted(p.name for p in tmp_path.glob("stock_analysis_*.log"))
    assert any(f == f"stock_analysis_{current_day}.log" for f in files)
    target = next(p for p in tmp_path.glob(f"stock_analysis_{current_day}.log"))
    assert "same day line" in target.read_text(encoding="utf-8")
    assert "after midnight line" in target.read_text(encoding="utf-8")
    handler.close()


def test_daily_rotating_handler_prunes_old_files_beyond_backup_count(tmp_path):
    for day in ["20260101", "20260102", "20260103", "20260104", "20260105"]:
        (tmp_path / f"stock_analysis_{day}.log").write_text("old", encoding="utf-8")

    handler = DailyRotatingFileHandler(
        tmp_path, prefix="stock_analysis", backup_count=3, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("test_daily_rotation_prune")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False

    logger.info("new line")

    files = sorted(p.name for p in tmp_path.glob("stock_analysis_*.log"))
    assert len(files) == 3, files
    handler.close()
