"""LLM-driven tabular overview of the last N SEC 10-Q filings.

Sibling component to `company_reports_analyzer`. Where the analyzer produces
a Warren-Buffett-style narrative memo, this component asks the LLM to render
the same raw XBRL data as clean, comparable Markdown tables — one column per
reporting period (the last N 10-Q quarters) — covering the Income Statement,
Balance Sheet, Cash Flow (incl. Free Cash Flow and Owner Earnings) and a
derived Key Ratios table (margins, ROE/ROA/ROIC, debt/equity, liquidity,
interest coverage, FCF conversion).

Design mirrors `CompanyReportsAnalyzer`:
- Consumes the same `CompanyReportsBundle` from `company_reports_service`.
- Reuses the analyzer's context-table builder so the raw numbers the LLM sees
  are byte-for-byte identical to the narrative path.
- Fail-open: any exception returns an empty string; the caller renders no
  block when the string is empty.
- Language-aware: prompt language follows the pipeline's `REPORT_LANGUAGE`.
- Bounded retry on empty/failed LLM responses (fail-open), same as analyzer.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from src.report_language import normalize_report_language
from src.services.company_reports_analyzer import CompanyReportsAnalyzer
from src.services.company_reports_service import CompanyReportsBundle

logger = logging.getLogger(__name__)


class CompanyReportsTableGenerator:
    """Compose a table-rendering prompt from a `CompanyReportsBundle` and run
    one LLM call that returns a set of Markdown tables."""

    def __init__(
        self,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        # Low temperature: we want precise, deterministic tables, not prose.
        self._max_tokens = max(256, int(max_tokens or 2000))
        self._temperature = float(temperature)
        # Retry on empty/failed responses before giving up (transient blank
        # output is a known failure mode, same as the analyzer).
        self._max_attempts = max(1, int(max_attempts or 1))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds or 0.0))
        # Reuse the analyzer's table builder so the raw numbers fed to the LLM
        # are identical across the narrative and table blocks.
        self._analyzer = CompanyReportsAnalyzer()

    def generate(
        self,
        bundle: CompanyReportsBundle,
        analyzer: Any,
        report_language: str | None = None,
    ) -> str:
        """Return LLM-generated Markdown tables, or an empty string on failure."""
        if bundle is None or bundle.is_empty:
            logger.debug(
                "[company_reports_table] skipped for %s: bundle is None or empty",
                getattr(bundle, "ticker", "?"),
            )
            return ""
        if analyzer is None or not hasattr(analyzer, "generate_text"):
            logger.warning(
                "[company_reports_table] skipped for %s: LLM analyzer unavailable or missing generate_text",
                bundle.ticker,
            )
            return ""
        lang = normalize_report_language(report_language)
        logger.info(
            "[company_reports_table] starting LLM table generation for %s: %d filing(s), language=%s, max_tokens=%d, temperature=%.2f, max_attempts=%d",
            bundle.ticker,
            len(bundle.filings),
            lang,
            self._max_tokens,
            self._temperature,
            self._max_attempts,
        )
        prompt = self._build_prompt(bundle, lang)
        logger.debug(
            "[company_reports_table] prompt built for %s: %d chars",
            bundle.ticker,
            len(prompt),
        )

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            started_at = time.perf_counter()
            try:
                text = analyzer.generate_text(
                    prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                logger.warning(
                    "[company_reports_table] LLM attempt %d/%d failed for %s in %dms: %s",
                    attempt,
                    self._max_attempts,
                    bundle.ticker,
                    duration_ms,
                    exc,
                )
                if attempt < self._max_attempts:
                    self._sleep_before_retry(attempt, bundle.ticker)
                continue
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            if not text:
                logger.warning(
                    "[company_reports_table] LLM returned empty response for %s on attempt %d/%d after %dms",
                    bundle.ticker,
                    attempt,
                    self._max_attempts,
                    duration_ms,
                )
                if attempt < self._max_attempts:
                    self._sleep_before_retry(attempt, bundle.ticker)
                    continue
                return ""
            result = self._sanitize_latex_escapes(str(text).strip())
            if result:
                logger.info(
                    "[company_reports_table] LLM table generation complete for %s on attempt %d/%d: %d chars returned in %dms",
                    bundle.ticker,
                    attempt,
                    self._max_attempts,
                    len(result),
                    duration_ms,
                )
                return result
            logger.warning(
                "[company_reports_table] LLM returned blank (whitespace-only) response for %s on attempt %d/%d after %dms",
                bundle.ticker,
                attempt,
                self._max_attempts,
                duration_ms,
            )
            if attempt < self._max_attempts:
                self._sleep_before_retry(attempt, bundle.ticker)

        if last_error is not None:
            logger.warning(
                "[company_reports_table] LLM generation failed for %s after %d attempt(s) (fail-open): %s",
                bundle.ticker,
                self._max_attempts,
                last_error,
            )
        else:
            logger.warning(
                "[company_reports_table] LLM returned empty response for %s after %d attempt(s) (fail-open)",
                bundle.ticker,
                self._max_attempts,
            )
        return ""

    def _sleep_before_retry(self, attempt: int, ticker: str) -> None:
        """Sleep with linear backoff between LLM retry attempts (fail-open)."""
        if self._retry_backoff_seconds <= 0:
            return
        delay = self._retry_backoff_seconds * attempt
        logger.debug(
            "[company_reports_table] retrying LLM generation for %s in %.1fs (attempt %d/%d)",
            ticker,
            delay,
            attempt,
            self._max_attempts,
        )
        try:
            time.sleep(delay)
        except Exception:  # noqa: BLE001
            logger.debug(
                "[company_reports_table] sleep interrupted before retry for %s", ticker
            )

    # ------------------------------------------------------------------ internals

    def _build_prompt(self, bundle: CompanyReportsBundle, report_language: str) -> str:
        table = self._analyzer._build_context_table(bundle)
        currency_hint = bundle.currency or "USD"
        n = len(bundle.filings)
        ticker = bundle.ticker

        conventions = _DATA_CONVENTIONS

        if report_language == "zh":
            return _build_prompt_zh(ticker, table, currency_hint, n, conventions)
        if report_language == "ko":
            return _build_prompt_ko(ticker, table, currency_hint, n, conventions)
        return _build_prompt_en(ticker, table, currency_hint, n, conventions)

    @staticmethod
    def _sanitize_latex_escapes(text: str) -> str:
        """Strip LaTeX escape backslashes so downstream renderers never treat
        table text as math. Mirrors the analyzer's defensive sanitizer."""
        if "\\" not in text:
            return text
        return re.sub(r"\\([()$%&_#{}~^|<>+=\-*/!.,:;])", r"\1", text)


# Shared data conventions embedded in every table prompt (kept identical to the
# analyzer's wording so the model treats the numbers the same way).
_DATA_CONVENTIONS = (
    "- Income Statement: section header tagged (Quarterly) means the single quarter; "
    "(YTD) means year-to-date cumulative.\n"
    "- Balance Sheet: point-in-time snapshot at each period end.\n"
    "- All amounts are abbreviated: B = billion, M = million, K = thousand (e.g. "
    "12.5B = 12,500,000,000). Convert to raw units before computing any ratio.\n"
    "- Cash Flow: SEC 10-Q filings only publish year-to-date (YTD) cash-flow statements "
    "— per-quarter cash flow is never reported directly. To estimate a single quarter, "
    "take current 10-Q YTD − prior 10-Q YTD (if the prior filing is Q1, its YTD is already "
    "the Q1 stand-alone figure).\n"
    "- Annualization: to compare quarterly numbers against annual thresholds, multiply the "
    "latest single quarter by 4, or use trailing four quarters when present."
)


def _build_prompt_en(
    ticker: str,
    table: str,
    currency_hint: str,
    n: int,
    conventions: str,
) -> str:
    return (
        f"You are a meticulous financial data analyst. Below are the last {n} SEC 10-Q "
        f"quarterly reports for {ticker} (amounts in {currency_hint} unless a row states "
        f"otherwise). Convert the raw XBRL figures into clean, comparable Markdown tables "
        f"so an investor can scan the last {n} quarters at a glance.\n\n"
        f"{table}\n\n"
        f"Data conventions (important):\n{conventions}\n\n"
        "Output ONLY the Markdown tables below, in this exact order, with no top-level "
        "heading, no code fence, no preamble, and no trailing commentary. Every table has "
        "one column per reporting period, using the exact period label shown above (e.g. "
        "`2026-06-27 (Q3)` or `2026-06-27 (YTD)`), plus a leading 'Metric' column.\n\n"
        "## Income Statement\n"
        "Rows: Revenue, Gross Profit, Gross Margin %, Operating Income, Operating Margin %, "
        "Net Income, Net Margin %, EPS (Diluted). Use the quarterly basis where available.\n\n"
        "## Balance Sheet\n"
        "Rows: Total Assets, Current Assets, Cash & Equivalents, Short-Term Investments, "
        "Total Debt (Long-Term + Short-Term), Stockholders' Equity, Book Value / Share.\n\n"
        "## Cash Flow\n"
        "Rows: Operating Cash Flow, CapEx, Free Cash Flow, FCF Conversion % (FCF / Net Income), "
        "Share Buybacks, Dividends Paid, Owner Earnings (Net Income + D&A − CapEx). Label each "
        "row YTD or 'derived quarter' (for YTD differences) to avoid conflating periods.\n\n"
        "## Key Ratios\n"
        "Compute each ratio per period from the raw numbers above and show it as a row: "
        "Gross Margin %, Operating Margin %, Net Margin %, ROE (annualized, Net Income × 4 / "
        "Stockholders' Equity), ROA (annualized), ROIC (annualized, Operating Income × (1 − "
        "effective tax rate) × 4 / (Stockholders' Equity + Long-Term Debt + Short-Term "
        "Borrowings − Cash & Equivalents)), Debt/Equity, Current Ratio, Quick Ratio, Interest "
        "Coverage (Operating Income / Interest Expense), FCF Conversion %, Book Value / Share.\n\n"
        "Formatting requirements:\n"
        "- Use plain ASCII only. NEVER write LaTeX escapes like \\( \\) \\$ \\% \\& — use plain "
        "( ) $ % &.\n"
        "- Use a consistent abbreviation scale per section (all M, or all B) and state it once "
        "in the section header, e.g. `## Income Statement (in $M)`.\n"
        "- Every number must be computed explicitly from the provided data; if an input is "
        "missing so a metric cannot be computed, write `N/A`. Never fabricate values.\n"
        "- Skip any row where every period is blank.\n"
        "- Keep tables compact: one Metric row per line, aligned pipe tables.\n"
    )


def _build_prompt_zh(
    ticker: str,
    table: str,
    currency_hint: str,
    n: int,
    conventions: str,
) -> str:
    return (
        f"你是一名严谨的财务数据分析师。以下是 {ticker} 最近 {n} 份 SEC 10-Q 季报"
        f"（除非某行另有说明，金额单位为 {currency_hint}）。请把原始 XBRL 数字整理成清晰、"
        f"可横向对比的 Markdown 表格，让投资者一眼扫过最近 {n} 个季度。\n\n"
        f"{table}\n\n"
        f"数据约定（重要）：\n{conventions}\n\n"
        "只输出下面这些 Markdown 表格，严格按顺序，不要标题行、不要代码围栏、不要前言、"
        "不要结尾评论。每个表格一列对应一个报告期，列名使用上面给出的时期标签（如 "
        "`2026-06-27 (Q3)` 或 `2026-06-27 (YTD)`），再加一列“指标”。\n\n"
        "## 利润表\n"
        "行：营业收入、毛利润、毛利率 %、营业利润、营业利润率 %、净利润、净利率 %、"
        "稀释每股收益。有季度口径时用季度口径。\n\n"
        "## 资产负债表\n"
        "行：总资产、流动资产、现金及等价物、短期投资、总有息负债（长期+短期）、"
        "股东权益、每股账面价值。\n\n"
        "## 现金流量表\n"
        "行：经营活动现金流、资本开支、自由现金流、FCF 转化率 %（FCF/净利润）、回购、"
        "分红、股东盈余（净利润 + 折旧摊销 − 资本开支）。每行标注 YTD 或“推算季度”"
        "（由 YTD 差值得到），避免口径混淆。\n\n"
        "## 关键比率\n"
        "根据上面的原始数字逐期计算并各占一行：毛利率 %、营业利润率 %、净利率 %、"
        "ROE（年化，净利润×4/股东权益）、ROA（年化）、ROIC（年化，营业利润×(1−有效税率)×4/"
        "（股东权益+长期债务+短期借款−现金及等价物））、资产负债率、流动比率、速动比率、"
        "利息覆盖倍数（营业利润/利息费用）、FCF 转化率 %、每股账面价值。\n\n"
        "格式要求：\n"
        "- 只用纯 ASCII。绝对不要写 \\( \\) \\$ \\% \\& 之类的 LaTeX 转义，一律用 ( ) $ % &。\n"
        "- 每个小节内金额缩写尺度要一致（都用 M 或都用 B），并在小节标题中标出，如 "
        "`## 利润表（单位：百万美元）`。\n"
        "- 每个数字都必须由给定数据显式计算；若某指标因输入缺失无法计算，写 `N/A`。"
        "绝不编造数值。\n"
        "- 所有时期都为空的整行直接省略。\n"
        "- 表格紧凑：每行一个指标，用对齐的管道表格。\n"
    )


def _build_prompt_ko(
    ticker: str,
    table: str,
    currency_hint: str,
    n: int,
    conventions: str,
) -> str:
    return (
        f"당신은 꼼꼼한 재무 데이터 분석가입니다. 아래는 {ticker}의 최근 {n}개 SEC 10-Q "
        f"분기 보고서입니다(별도 표시가 없는 한 금액 단위는 {currency_hint}). 원시 XBRL "
        f"수치를 깔끔하고 비교 가능한 Markdown 표로 정리하여 투자자가 최근 {n}개 분기를 "
        f"한눈에 파악할 수 있게 하세요.\n\n"
        f"{table}\n\n"
        f"데이터 규칙(중요):\n{conventions}\n\n"
        "아래 Markdown 표만 정확한 순서대로 출력하세요. 상위 제목, 코드 펜스, 머리말, "
        "끝맺음 코멘트는 넣지 마세요. 각 표는 보고 기간마다 한 열을 가지며, 위에 표시된 "
        "기간 라벨(예: `2026-06-27 (Q3)` 또는 `2026-06-27 (YTD)`)을 열 이름으로 사용하고 "
        "맨 앞에 '지표' 열을 둡니다.\n\n"
        "## 손익계산서\n"
        "행: 매출, 매출총이익, 매출총이익률 %, 영업이익, 영업이익률 %, 순이익, 순이익률 %, "
        "희석 EPS. 가능하면 분기 기준을 사용하세요.\n\n"
        "## 대차대조표\n"
        "행: 총자산, 유동자산, 현금 및 현금성자산, 단기투자, 총부채(장기+단기), "
        "주주자본, 주당 장부가치.\n\n"
        "## 현금흐름표\n"
        "행: 영업활동현금흐름, 자본지출, 잉여현금흐름(FCF), FCF 전환율 %(FCF/순이익), "
        "자사주매입, 배당금, 주주이익(순이익 + 감가상각 − 자본지출). 각 행에 YTD 또는 "
        "'추정 분기'(YTD 차이)를 표시해 기간 혼동을 피하세요.\n\n"
        "## 핵심 비율\n"
        "위 원시 수치로 기간별로 계산해 한 행씩: 매출총이익률 %, 영업이익률 %, 순이익률 %, "
        "ROE(연환산, 순이익×4/주주자본), ROA(연환산), ROIC(연환산, 영업이익×(1−실효세율)×4/"
        "(주주자본+장기부채+단기차입−현금및현금성자산)), 부채비율, 유동비율, 당좌비율, "
        "이자보상배율(영업이익/이자비용), FCF 전환율 %, 주당 장부가치.\n\n"
        "형식 요구사항:\n"
        "- 순수 ASCII만 사용하세요. \\( \\) \\$ \\% \\& 같은 LaTeX 이스케이프를 절대 쓰지 "
        "말고 ( ) $ % &를 그대로 쓰세요.\n"
        "- 각 섹션 내 금액 축약 단위는 일관되게(전부 M 또는 전부 B) 하고 섹션 제목에 한 번 "
        "명시하세요(예: `## 손익계산서 (백만 달러)`).\n"
        "- 모든 숫자는 제공된 데이터로 명시적으로 계산하세요. 입력이 없어 계산할 수 없으면 "
        "`N/A`를 쓰세요. 값을 절대 지어내지 마세요.\n"
        "- 모든 기간이 빈 행은 생략하세요.\n"
        "- 표를 간결하게: 지표당 한 줄, 정렬된 파이프 표.\n"
    )
