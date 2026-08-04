# -*- coding: utf-8 -*-
"""Regression tests for CompanyReportsTableGenerator (SEC 10-Q tabular overview)."""

from types import SimpleNamespace

from src.services.company_reports_service import (
    CompanyReportsBundle,
    FilingSummary,
)
from src.services.company_reports_table import CompanyReportsTableGenerator


def _make_bundle() -> CompanyReportsBundle:
    filing = FilingSummary(
        form="10-Q",
        filing_date="2026-06-27",
        period_of_report="2026-06-27",
        income_statement={
            "Revenue": 12_500_000_000.0,
            "GrossProfit": 6_000_000_000.0,
            "OperatingIncomeLoss": 3_000_000_000.0,
            "NetIncomeLoss": 2_200_000_000.0,
            "EarningsPerShareDiluted": 1.4,
        },
        balance_sheet={
            "Assets": 100_000_000_000.0,
            "CurrentAssets": 40_000_000_000.0,
            "StockholdersEquity": 60_000_000_000.0,
            "LongTermDebt": 10_000_000_000.0,
        },
        cash_flow={
            "NetCashProvidedByUsedInOperatingActivities": 4_000_000_000.0,
            "PaymentsToAcquirePropertyPlantAndEquipment": 500_000_000.0,
        },
        income_period_label="2026-06-27 (Q3)",
        balance_period_label="2026-06-27",
        cash_flow_period_label="2026-06-27 (YTD)",
        notes={"currency": "USD"},
    )
    return CompanyReportsBundle(ticker="AAPL", filings=[filing], currency="USD")


class _FakeAnalyzer:
    """Minimal LLM analyzer with a scriptable `generate_text`."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def generate_text(
        self, prompt, max_tokens=None, temperature=None, allow_reasoning_fallback=None
    ):
        self.calls.append((prompt, max_tokens, temperature))
        self.last_allow_reasoning_fallback = allow_reasoning_fallback
        if not self.results:
            return ""
        return self.results.pop(0)


def _make_generator(max_attempts=3, retry_backoff_seconds=0.0):
    return CompanyReportsTableGenerator(
        max_tokens=2000,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )


def test_generate_skips_empty_bundle():
    gen = _make_generator()
    assert (
        gen.generate(CompanyReportsBundle(ticker="AAPL"), _FakeAnalyzer([""]))
        == "Error: no SEC 10-Q filings available"
    )


def test_generate_skips_none_bundle():
    gen = _make_generator()
    assert (
        gen.generate(None, _FakeAnalyzer([""]))
        == "Error: no SEC 10-Q filings available"
    )


def test_generate_skips_missing_generate_text():
    gen = _make_generator()
    assert gen.generate(_make_bundle(), SimpleNamespace()) == "Error: LLM analyzer unavailable"


def test_generate_returns_sanitized_markdown():
    gen = _make_generator()
    fake = _FakeAnalyzer([r"## Income Statement \(in \$M\)\n\n| Metric | 2026-06-27 |"])
    result = gen.generate(_make_bundle(), fake)
    assert "\\(" not in result
    assert "\\$" not in result
    assert "## Income Statement (in $M)" in result
    assert fake.calls[0][1] == 2000  # max_tokens forwarded


def test_generate_retries_on_empty_then_succeeds():
    gen = _make_generator(max_attempts=3)
    fake = _FakeAnalyzer(["", "", "## Cash Flow\n\n| Metric | Value |"])
    result = gen.generate(_make_bundle(), fake)
    assert len(fake.calls) == 3
    assert "## Cash Flow" in result


def test_generate_fail_open_after_all_empty():
    gen = _make_generator(max_attempts=2)
    fake = _FakeAnalyzer(["", ""])
    result = gen.generate(_make_bundle(), fake)
    assert result == "Error: empty content"
    assert len(fake.calls) == 2


def test_generate_fail_open_on_exception():
    class _Boom:
        def generate_text(self, prompt, max_tokens=None, temperature=None):
            raise RuntimeError("llm down")

    gen = _make_generator(max_attempts=2, retry_backoff_seconds=0.0)
    assert gen.generate(_make_bundle(), _Boom()) == "Error: llm down"


def test_generate_passes_allow_reasoning_fallback_false():
    gen = _make_generator()
    fake = _FakeAnalyzer(["## Cash Flow\n\n| Metric | Value |"])
    gen.generate(_make_bundle(), fake)
    # The generator must forward allow_reasoning_fallback=False so the LLM's
    # reasoning (chain-of-thought) fallback never leaks into the table block.
    assert fake.last_allow_reasoning_fallback is False


def test_prompt_contains_table_sections_and_data_conventions():
    gen = _make_generator()
    prompt = gen._build_prompt(_make_bundle(), "en")
    assert "## Income Statement" in prompt
    assert "## Balance Sheet" in prompt
    assert "## Cash Flow" in prompt
    assert "## Key Ratios" in prompt
    assert "Free Cash Flow" in prompt
    assert "AAPL" in prompt
    assert "2026-06-27 (Q3)" in prompt  # context table period label fed to the LLM


def test_prompt_localization():
    gen = _make_generator()
    for lang in ("zh", "ko", "en"):
        prompt = gen._build_prompt(_make_bundle(), lang)
        assert prompt.strip()
