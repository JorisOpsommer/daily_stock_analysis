"""LLM-driven investment-grade analysis over the last N SEC 10-Q filings.

Consumes a `CompanyReportsBundle` from `company_reports_service`, builds a
compact markdown context table with all extracted financial data, and calls
`analyzer.generate_text()` to produce a rigorous value-investor analysis in
the style a Warren Buffett analyst would prepare — covering moat durability,
capital allocation, owner earnings, and margin of safety signals.

Design:
- Fail-open: any exception returns an empty string; the caller renders no
  block when the string is empty.
- Language-aware: prompt language follows the pipeline's `REPORT_LANGUAGE`.
- Token-conscious: only the whitelist of concepts extracted by the service
  is passed to the LLM, but the prompt asks for deep financial reasoning.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.report_language import normalize_report_language
from src.services.company_reports_service import CompanyReportsBundle, FilingSummary

logger = logging.getLogger(__name__)


# Concepts we render as rows in the comparison table. Keep the order stable so
# quarter-over-quarter diffs read consistently across runs.
_INCOME_ROWS: list[tuple[str, str]] = [
    ("Revenue", "Revenue"),
    ("CostOfRevenue", "Cost of Revenue"),
    ("GrossProfit", "Gross Profit"),
    ("OperatingIncomeLoss", "Operating Income"),
    ("OperatingExpenses", "Operating Expenses"),
    ("ResearchAndDevelopmentExpense", "R&D Expense"),
    ("SellingGeneralAndAdministrativeExpense", "SG&A Expense"),
    ("InterestExpense", "Interest Expense"),
    ("DepreciationAndAmortization", "D&A"),
    ("IncomeLossBeforeIncomeTaxes", "Pre-Tax Income"),
    ("IncomeTaxExpenseBenefit", "Income Tax Expense"),
    ("NetIncomeLoss", "Net Income"),
    ("EarningsPerShareBasic", "EPS (Basic)"),
    ("EarningsPerShareDiluted", "EPS (Diluted)"),
    ("WeightedAverageNumberOfSharesOutstandingDiluted", "Shares Out (Diluted)"),
]

_BALANCE_ROWS: list[tuple[str, str]] = [
    ("Assets", "Total Assets"),
    ("CurrentAssets", "Current Assets"),
    ("CashAndCashEquivalentsAtCarryingValue", "Cash & Equivalents"),
    ("ShortTermInvestments", "Short-Term Investments"),
    ("AccountsReceivableNetCurrent", "Accounts Receivable"),
    ("InventoryNet", "Inventory"),
    ("Goodwill", "Goodwill"),
    ("IntangibleAssetsNetExcludingGoodwill", "Other Intangibles"),
    ("PropertyPlantAndEquipmentNet", "PP&E (Net)"),
    ("AccountsPayableCurrent", "Accounts Payable"),
    ("CurrentLiabilities", "Current Liabilities"),
    ("LongTermDebt", "Long-Term Debt"),
    ("ShortTermBorrowings", "Short-Term Borrowings"),
    ("Liabilities", "Total Liabilities"),
    ("StockholdersEquity", "Stockholders' Equity"),
    ("RetainedEarningsAccumulatedDeficit", "Retained Earnings"),
    ("TreasuryStockValue", "Treasury Stock"),
    ("CommonStockSharesOutstanding", "Shares Outstanding"),
]

_CASHFLOW_ROWS: list[tuple[str, str]] = [
    ("NetCashProvidedByUsedInOperatingActivities", "Operating Cash Flow"),
    ("PaymentsToAcquirePropertyPlantAndEquipment", "CapEx"),
    ("DepreciationDepletionAndAmortization", "D&A (CF)"),
    ("ShareBasedCompensation", "Stock-Based Comp"),
    ("NetCashProvidedByUsedInInvestingActivities", "Investing Cash Flow"),
    ("NetCashProvidedByUsedInFinancingActivities", "Financing Cash Flow"),
    ("PaymentsForRepurchaseOfCommonStock", "Share Buybacks"),
    ("PaymentsOfDividendsCommonStock", "Dividends Paid"),
]


class CompanyReportsAnalyzer:
    """Compose a prompt from a `CompanyReportsBundle` and run one LLM call."""

    def __init__(
        self,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        # Low temperature: we want precise financial reasoning, not creative prose.
        self._max_tokens = max(256, int(max_tokens or 2000))
        self._temperature = float(temperature)
        # Retry the LLM call on empty/failed responses before giving up. Empty
        # responses are a known transient failure mode (the model is reached but
        # returns blank output), so a bounded retry materially improves yield.
        self._max_attempts = max(1, int(max_attempts or 1))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds or 0.0))

    def analyze(
        self,
        bundle: CompanyReportsBundle,
        analyzer: Any,
        report_language: str | None = None,
    ) -> str:
        """Return LLM-generated markdown, or an empty string on failure."""
        if bundle is None or bundle.is_empty:
            logger.debug(
                "[company_reports] analyzer skipped for %s: bundle is None or empty",
                getattr(bundle, "ticker", "?"),
            )
            return ""
        if analyzer is None or not hasattr(analyzer, "generate_text"):
            logger.warning(
                "[company_reports] analyzer skipped for %s: LLM analyzer unavailable or missing generate_text",
                bundle.ticker,
            )
            return ""
        lang = normalize_report_language(report_language)
        logger.info(
            "[company_reports] starting LLM analysis for %s: %d filing(s), language=%s, max_tokens=%d, temperature=%.2f, max_attempts=%d",
            bundle.ticker,
            len(bundle.filings),
            lang,
            self._max_tokens,
            self._temperature,
            self._max_attempts,
        )
        prompt = self._build_prompt(bundle, lang)
        logger.debug(
            "[company_reports] prompt built for %s: %d chars",
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
                    "[company_reports] LLM analysis attempt %d/%d failed for %s in %dms: %s",
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
                    "[company_reports] LLM returned empty response for %s on attempt %d/%d after %dms",
                    bundle.ticker,
                    attempt,
                    self._max_attempts,
                    duration_ms,
                )
                if attempt < self._max_attempts:
                    self._sleep_before_retry(attempt, bundle.ticker)
                    continue
                return ""
            result = str(text).strip()
            if result:
                logger.info(
                    "[company_reports] LLM analysis complete for %s on attempt %d/%d: %d chars returned in %dms",
                    bundle.ticker,
                    attempt,
                    self._max_attempts,
                    len(result),
                    duration_ms,
                )
                return result
            logger.warning(
                "[company_reports] LLM returned blank (whitespace-only) response for %s on attempt %d/%d after %dms",
                bundle.ticker,
                attempt,
                self._max_attempts,
                duration_ms,
            )
            if attempt < self._max_attempts:
                self._sleep_before_retry(attempt, bundle.ticker)

        if last_error is not None:
            logger.warning(
                "[company_reports] LLM analysis failed for %s after %d attempt(s) (fail-open): %s",
                bundle.ticker,
                self._max_attempts,
                last_error,
            )
        else:
            logger.warning(
                "[company_reports] LLM returned empty response for %s after %d attempt(s) (fail-open)",
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
            "[company_reports] retrying LLM analysis for %s in %.1fs (attempt %d/%d)",
            ticker,
            delay,
            attempt,
            self._max_attempts,
        )
        try:
            time.sleep(delay)
        except Exception:  # noqa: BLE001
            logger.debug(
                "[company_reports] sleep interrupted before retry for %s", ticker
            )

    # ------------------------------------------------------------------ internals

    def _build_prompt(self, bundle: CompanyReportsBundle, report_language: str) -> str:
        table = self._build_context_table(bundle)
        currency_hint = bundle.currency or "USD"
        n = len(bundle.filings)

        # ------------------------------------------------------------------
        # The analysis framework below mirrors how Warren Buffett actually
        # evaluates a business for a long-term concentrated position:
        #   - Return on capital (ROE / ROIC) is the single most important
        #     compounding signal.
        #   - Owner Earnings (Buffett's own definition, Berkshire 1986 letter)
        #     replaces reported earnings as the true cash yield.
        #   - Balance-sheet durability (interest coverage, current/quick,
        #     debt/equity) determines whether the moat can survive a downturn.
        #   - Book value per share growth is the historical Berkshire scorecard.
        # The LLM receives raw XBRL numbers via the table and is asked to
        # compute every ratio explicitly — no hand-waving allowed.
        #
        # Formatting rules are strict because downstream messengers (Feishu /
        # Telegram / web) render Markdown, and some render KaTeX math when they
        # see `\(...\)` / `\$...\$`. The LLM must emit plain ASCII.
        # ------------------------------------------------------------------

        if report_language == "zh":
            return self._build_prompt_zh(bundle, table, currency_hint, n)
        if report_language == "ko":
            return self._build_prompt_ko(bundle, table, currency_hint, n)
        return self._build_prompt_en(bundle, table, currency_hint, n)

    @staticmethod
    def _build_prompt_en(
        bundle: CompanyReportsBundle,
        table: str,
        currency_hint: str,
        n: int,
    ) -> str:
        return (
            f"You are a Warren Buffett-style value investing analyst preparing a due-diligence "
            f"memo for an investor seriously considering a long-term concentrated position in "
            f"{bundle.ticker}. Below are the last {n} SEC 10-Q quarterly reports "
            f"(amounts in {currency_hint} unless the row states otherwise).\n\n"
            f"{table}\n\n"
            "Data conventions (important):\n"
            "- Income Statement: section header tagged (Quarterly) means the single quarter; "
            "(YTD) means year-to-date cumulative.\n"
            "- Balance Sheet: point-in-time snapshot at each period end.\n"
            "- Cash Flow: SEC 10-Q filings only publish year-to-date (YTD) cash-flow statements "
            "— per-quarter cash flow is never reported directly. To estimate a single quarter, "
            "take current 10-Q YTD − prior 10-Q YTD (if the prior filing is Q1, its YTD is already "
            "the Q1 stand-alone figure).\n"
            "- Annualization: to compare quarterly numbers against Buffett's annual thresholds, "
            "multiply the latest single quarter by 4, or use trailing four quarters when four "
            "sequential quarters are present.\n\n"
            "Write a rigorous Markdown due-diligence memo using the seven numbered sections below. "
            "Compute every ratio with actual numbers — never say only 'increased' or 'decreased'. "
            "If a required input is missing, state which input is missing and skip that specific "
            "ratio. Never fabricate values.\n\n"
            "## 1. Business Quality & Moat Signals\n"
            "- Gross margin, operating margin, net margin per period (show each number).\n"
            "- Buffett heuristics: consistent gross margin > 40% and net margin > 20% suggest a "
            "durable moat. State explicitly whether each threshold is met.\n"
            "- SG&A as % of revenue trend (operating leverage).\n"
            "- R&D as % of revenue trend (moat defense vs margin drag).\n"
            "- Revenue growth quarter over quarter and, when 4+ quarters are shown, implied "
            "annualized growth (CAGR).\n\n"
            "## 2. Return on Capital (Buffett's core focus)\n"
            "- ROE (annualized) = (Net Income × 4) / Stockholders' Equity for each period. "
            "Buffett floor: consistently > 15%. Show every value and label pass/fail.\n"
            "- ROA (annualized) = (Net Income × 4) / Total Assets for each period.\n"
            "- ROIC (annualized) = (Operating Income × (1 − effective tax rate) × 4) / "
            "(Stockholders' Equity + Long-Term Debt + Short-Term Borrowings − Cash & Equivalents). "
            "Buffett floor: > 12%. Show every value and label pass/fail.\n"
            "- Effective tax rate = Income Tax Expense / Pre-Tax Income per period. If pre-tax "
            "income is missing, approximate using a 21% US federal statutory rate and say so.\n\n"
            "## 3. Balance Sheet & Financial Durability\n"
            "- Debt-to-Equity = (Long-Term Debt + Short-Term Borrowings) / Stockholders' Equity "
            "per period. Buffett prefers < 0.5; anything > 1.0 requires justification.\n"
            "- Current ratio = Current Assets / Current Liabilities per period. Healthy > 1.5.\n"
            "- Quick ratio = (Current Assets − Inventory) / Current Liabilities. Healthy > 1.0.\n"
            "- Interest coverage = Operating Income / Interest Expense per period. Buffett floor: > 5x.\n"
            "- Cash + Short-Term Investments vs Total Liabilities coverage (defensive posture).\n"
            "- Goodwill as % of Total Assets — high goodwill signals aggressive M&A and impairment risk.\n\n"
            "## 4. Earnings Quality & Owner Earnings\n"
            "- Growth-rate reality check: is Accounts Receivable growing faster than Revenue? "
            "Is Inventory growing faster than Revenue? Both are classic red flags for channel "
            "stuffing or obsolete stock. Compute each growth rate.\n"
            "- Owner Earnings (Buffett, 1986 Berkshire letter) for the most recent YTD period: "
            "Net Income + D&A − CapEx (treat total CapEx as a proxy for maintenance CapEx unless "
            "there is a clear expansion signal). Show the full calculation.\n"
            "- Stock-Based Compensation as % of revenue (if reported) — Buffett treats SBC as a "
            "real cash-equivalent expense that dilutes owners; flag if > 5% of revenue.\n"
            "- Retained Earnings trajectory — is the company genuinely compounding book value, "
            "or eroding it through losses / buyback-driven equity reduction?\n\n"
            "## 5. Free Cash Flow & Capital Allocation\n"
            "- FCF (YTD) = Operating Cash Flow − CapEx for each YTD period shown.\n"
            "- FCF conversion = FCF / Net Income on the same basis (YTD vs YTD). > 100% indicates "
            "high-quality earnings; < 60% is a warning.\n"
            "- FCF margin = FCF / Revenue on the same basis.\n"
            "- Where possible, derive stand-alone quarterly FCF by differencing consecutive YTDs.\n"
            "- Capital returned to shareholders (Buybacks + Dividends, YTD). If both rows are empty "
            "for every period, write explicitly: 'the company did not repurchase stock or pay "
            "dividends in the periods shown' — do NOT say 'data not provided'.\n"
            "- CapEx intensity = CapEx / Revenue. Is this an asset-light compounder or capex-heavy?\n\n"
            "## 6. Per-Share Value & Dilution\n"
            "- Diluted EPS trajectory (show numbers).\n"
            "- Book Value per Share = Stockholders' Equity / Shares Outstanding per period. This is "
            "Berkshire's own historical scorecard — compute it and show the sequential change.\n"
            "- Diluted share count change across the periods shown (%). Rising float destroys "
            "per-share value even when net income grows.\n"
            "- Gap between Basic and Diluted EPS — a widening gap signals dilutive convertibles / "
            "unvested equity.\n\n"
            "## 7. Investment Verdict (Buffett Lens)\n"
            "Write 4-6 sentences answering, in order:\n"
            "1) Does this business have a durable competitive advantage (moat)?\n"
            "2) Is management allocating capital wisely (reinvestment, buybacks, dividends, M&A)?\n"
            "3) Is the balance sheet defensive enough to survive a 2008-style downturn?\n"
            "4) Given the trajectory of ROE / ROIC / owner earnings / book value per share, is "
            "this the kind of business Buffett would want to own for a decade?\n"
            "5) What is the single biggest risk visible in the last {n} quarters of data?\n"
            "6) One-line verdict: STRONG BUY / BUY / WATCH / AVOID from a value-investor lens, "
            "with a one-clause justification.\n\n"
            "Formatting requirements (strict — violating these breaks downstream rendering):\n"
            "- Return the Markdown body only. No top-level heading, no code fence, no preamble, "
            "no closing summary line.\n"
            "- Use plain ASCII parentheses ( and ). NEVER write \\( or \\) — those are LaTeX "
            "escapes that render as math in our messengers.\n"
            "- Use plain % (not \\%), plain $ (not \\$), plain & (not \\&).\n"
            "- When citing cash-flow or income-statement figures, label them YTD, Quarterly, or "
            "'derived quarter' (for YTD differences) to avoid conflating periods.\n"
            "- Skip rows where every quarter is blank; do not fabricate values.\n"
            "- When a Buffett heuristic threshold is met or missed, say so explicitly "
            "(e.g. 'ROE 22.4% — clears the 15% Buffett floor' or 'Interest coverage 3.1x — "
            "below the 5x Buffett floor')."
        ).replace("{n}", str(n))

    @staticmethod
    def _build_prompt_zh(
        bundle: CompanyReportsBundle,
        table: str,
        currency_hint: str,
        n: int,
    ) -> str:
        return (
            f"你是一位巴菲特风格的价值投资分析师，正在为一位认真考虑长期集中持有 {bundle.ticker} 的投资者"
            f"撰写尽职调查备忘录。以下是该公司最近 {n} 份 SEC 10-Q 季报的关键财务数据"
            f"（金额单位默认 {currency_hint}，除非行内另有说明）。\n\n"
            f"{table}\n\n"
            "数据口径说明（重要）：\n"
            "- 利润表：如标题标注 (Quarterly)，为当季数据；如标注 (YTD)，为年初至今累计。\n"
            "- 资产负债表：为期末时点数据。\n"
            "- 现金流量表：10-Q 规定现金流量表只提供年初至今累计（YTD）数据，不提供单季数据。"
            "如需当季现金流，请用 本期 YTD − 上一份 10-Q 的 YTD 做差分（若上一份为 Q1，则 Q1 YTD 即为 Q1 单季）。\n"
            "- 年化：与巴菲特年度阈值比较时，将最近单季数据 × 4 得到年化值，或在有 4 个连续季度时用滚动 TTM。\n\n"
            "请基于以上数据，撰写一份严谨的中文 Markdown 尽调备忘录，依次覆盖以下 7 节。"
            "所有比率必须给出具体数字，不能只说 '提高' 或 '下降'。"
            "如果某个必需输入缺失，请指明缺什么并跳过对应比率，绝不虚构数值。\n\n"
            "## 1. 业务质量与护城河信号\n"
            "- 每期计算毛利率、营业利润率、净利率（列出数字）。\n"
            "- 巴菲特经验：毛利率持续 > 40% 且净利率 > 20% 提示护城河，请明确指出是否达标。\n"
            "- SG&A / 营收比例走势（规模效应）。\n"
            "- R&D / 营收比例走势（是维护护城河还是拖累利润）。\n"
            "- 营收环比增速；有 4 个季度时给出隐含年化增速（CAGR）。\n\n"
            "## 2. 资本回报（巴菲特最看重）\n"
            "- ROE（年化）=（净利润 × 4）/ 股东权益，每期计算。巴菲特底线：持续 > 15%。列出每期数值并判断是否达标。\n"
            "- ROA（年化）=（净利润 × 4）/ 总资产，每期计算。\n"
            "- ROIC（年化）=（营业利润 × (1 − 有效税率) × 4）/（股东权益 + 长期负债 + 短期借款 − 现金及等价物）。"
            "巴菲特底线：> 12%。列出每期数值并判断是否达标。\n"
            "- 有效税率 = 所得税费用 / 税前利润。若税前利润缺失，采用 21% 美国联邦法定税率近似并说明。\n\n"
            "## 3. 资产负债表与财务稳健性\n"
            "- 负债 / 权益 =（长期负债 + 短期借款）/ 股东权益，每期计算。巴菲特偏好 < 0.5；> 1.0 需明确理由。\n"
            "- 流动比率 = 流动资产 / 流动负债，每期计算。健康值 > 1.5。\n"
            "- 速动比率 =（流动资产 − 存货）/ 流动负债，每期计算。健康值 > 1.0。\n"
            "- 利息覆盖倍数 = 营业利润 / 利息费用，每期计算。巴菲特底线：> 5 倍。\n"
            "- 现金 + 短期投资 vs 总负债覆盖情况（防御性）。\n"
            "- 商誉占总资产比重 — 过高提示激进并购与减值风险。\n\n"
            "## 4. 盈利质量与股东盈余（Owner Earnings）\n"
            "- 增速对照：应收账款是否比营收增长更快？存货是否比营收增长更快？两者都是渠道压货 / "
            "存货滞销的经典红旗信号，请计算增速。\n"
            "- 股东盈余（巴菲特 1986 年伯克希尔股东信定义），针对最近一期 YTD：净利润 + D&A − 资本支出"
            "（除非有明确扩张信号，否则将总 CapEx 视为维护性 CapEx 代理）。列出完整计算。\n"
            "- 股票薪酬 / 营收比例（若披露）— 巴菲特视 SBC 为真实的现金等价成本；> 5% 请标注为稀释警示。\n"
            "- 留存收益走势 — 公司是在真实累积账面价值，还是被亏损 / 回购缩表侵蚀？\n\n"
            "## 5. 自由现金流与资本配置\n"
            "- FCF（YTD）= 经营现金流 − CapEx，每个 YTD 期都计算。\n"
            "- FCF 转化率 = FCF / 净利润（同口径 YTD/YTD）。> 100% 为高质量盈利；< 60% 为警示。\n"
            "- FCF 利润率 = FCF / 营收（同口径）。\n"
            "- 若可能，用 YTD 差分推算单季 FCF。\n"
            "- 回馈股东资本（回购 + 分红，YTD）。若所有期两行都为空，请明确写：'该公司在所示期间未回购股票或派息'，"
            "不要说 '数据未提供'。\n"
            "- CapEx 强度 = CapEx / 营收。判断是轻资产复利型还是重资本型企业。\n\n"
            "## 6. 每股价值与稀释\n"
            "- 稀释 EPS 走势（列数字）。\n"
            "- 每股账面价值 = 股东权益 / 流通股数，每期计算。这是伯克希尔历史上自己的记分卡 — "
            "计算并给出环比变化。\n"
            "- 期间内稀释股数变化（%）。流通股上升会侵蚀每股价值，即便净利润在增长。\n"
            "- 基本 vs 稀释 EPS 差距 — 差距扩大提示可转债 / 未归属股权稀释。\n\n"
            "## 7. 投资结论（巴菲特视角）\n"
            "用 4-6 句话依次回答：\n"
            "1）这家公司是否具备持久竞争优势（护城河）？\n"
            "2）管理层的资本配置是否明智（再投资 / 回购 / 分红 / 并购）？\n"
            "3）资产负债表能否抵御 2008 式衰退？\n"
            "4）从 ROE / ROIC / 股东盈余 / 每股账面价值的走势看，这家公司是否值得持有十年？\n"
            "5）最近 " + str(n) + " 份季报中最大的单一风险是什么？\n"
            "6）一句话判定：STRONG BUY / BUY / WATCH / AVOID（价值投资视角），并给出一句理由。\n\n"
            "格式要求（严格 — 违反会破坏下游渲染）：\n"
            "- 只输出 Markdown 正文，无最外层标题、代码块、开场白或收尾语。\n"
            "- 使用普通 ASCII 圆括号 ( 和 )，绝不写 \\( 或 \\) — 这些是 LaTeX 转义，会在通知端被渲染为公式。\n"
            "- 使用普通 %（不要 \\%）、普通 $（不要 \\$）、普通 &（不要 \\&）。\n"
            "- 引用现金流或利润表数字时，明确标注 YTD、Quarterly 或 '推算单季'（YTD 差分）。\n"
            "- 每期都为空的行请忽略，不要虚构数值。\n"
            "- 达到或未达到巴菲特阈值时请明说，例如 'ROE 22.4% — 达到 15% 巴菲特底线' 或 "
            "'利息覆盖 3.1 倍 — 低于 5 倍巴菲特底线'。"
        )

    @staticmethod
    def _build_prompt_ko(
        bundle: CompanyReportsBundle,
        table: str,
        currency_hint: str,
        n: int,
    ) -> str:
        return (
            f"당신은 워런 버핏 스타일의 가치투자 분석가로서, {bundle.ticker} 에 장기 집중 투자를 "
            f"진지하게 고려하는 투자자를 위한 실사 메모를 작성합니다. 아래는 최근 {n} 개 SEC 10-Q "
            f"분기보고서의 핵심 재무 데이터입니다(별도 표기 없으면 통화는 {currency_hint}).\n\n"
            f"{table}\n\n"
            "데이터 기준(중요):\n"
            "- 손익계산서: 헤더가 (Quarterly)이면 해당 분기, (YTD)이면 연초 누계.\n"
            "- 재무상태표: 기말 시점 스냅샷.\n"
            "- 현금흐름표: 10-Q 규정상 연초 누계(YTD)만 제공. 단일 분기 현금흐름은 "
            "현재 10-Q YTD − 직전 10-Q YTD 로 산출(직전이 Q1이면 Q1 YTD 가 곧 Q1 단일 분기).\n"
            "- 연율화: 버핏 연간 기준과 비교하려면 최근 분기 × 4 또는 4개 분기 TTM 사용.\n\n"
            "위 데이터를 기반으로 다음 7개 섹션을 갖춘 엄격한 한국어 마크다운 실사 메모를 작성하세요. "
            "모든 비율은 실제 수치로 계산하고, '증가'/'감소' 로만 서술하지 마세요. "
            "필수 입력이 없으면 무엇이 없는지 명시하고 해당 비율은 건너뛰세요. 절대 값을 지어내지 마세요.\n\n"
            "## 1. 사업 품질 & 해자 신호\n"
            "- 각 기간의 매출총이익률, 영업이익률, 순이익률(수치 제시).\n"
            "- 버핏 휴리스틱: 총이익률 > 40% 지속 및 순이익률 > 20%는 해자 신호. 충족 여부 명시.\n"
            "- SG&A/매출 비율 추이(운영 레버리지).\n"
            "- R&D/매출 비율 추이(해자 방어 vs 마진 훼손).\n"
            "- 매출 QoQ 성장률; 4개 분기 이상이면 연율 성장(CAGR) 제시.\n\n"
            "## 2. 자본수익률(버핏의 핵심)\n"
            "- ROE(연율) = (순이익 × 4) / 자기자본, 매 기간 계산. 버핏 하한: 지속 > 15%. 전 기간 값 제시 및 통과/미달 표기.\n"
            "- ROA(연율) = (순이익 × 4) / 총자산, 매 기간 계산.\n"
            "- ROIC(연율) = (영업이익 × (1 − 유효세율) × 4) / (자기자본 + 장기부채 + 단기차입금 − 현금및등가물). "
            "버핏 하한: > 12%. 전 기간 값 제시 및 통과/미달 표기.\n"
            "- 유효세율 = 법인세비용 / 세전이익. 세전이익이 없으면 21% 미국 연방 법정세율 근사 및 표기.\n\n"
            "## 3. 재무건전성\n"
            "- 부채/자본 = (장기부채 + 단기차입금) / 자기자본, 매 기간. 버핏 선호 < 0.5; > 1.0 이면 근거 필요.\n"
            "- 유동비율 = 유동자산 / 유동부채, 매 기간. 건전 > 1.5.\n"
            "- 당좌비율 = (유동자산 − 재고) / 유동부채, 매 기간. 건전 > 1.0.\n"
            "- 이자보상배수 = 영업이익 / 이자비용, 매 기간. 버핏 하한: > 5배.\n"
            "- 현금 + 단기투자 vs 총부채 커버리지(방어 자세).\n"
            "- 영업권/총자산 비중 — 과도하면 공격적 M&A 및 손상 위험.\n\n"
            "## 4. 이익 품질 & 오너 어닝스\n"
            "- 성장률 대조: 매출채권/재고 증가율이 매출 증가율보다 빠른가? 채널 재고 밀어내기/재고 노후화의 전형 신호.\n"
            "- 오너 어닝스(버핏 1986 버크셔 서한 정의) — 최근 YTD 기준: 순이익 + D&A − CapEx"
            "(확장 신호가 명확하지 않으면 총 CapEx 를 유지 CapEx 대용으로 사용). 전체 계산 제시.\n"
            "- 주식보상비용/매출 비율(공시 시) — 버핏은 SBC 를 실질 현금성 비용으로 취급; > 5% 이면 희석 경고.\n"
            "- 이익잉여금 추이 — 실제로 장부가치를 복리로 축적 중인지, 손실/자사주매입으로 잠식 중인지 판단.\n\n"
            "## 5. 잉여현금흐름 & 자본배분\n"
            "- FCF(YTD) = 영업CF − CapEx, 각 YTD 계산.\n"
            "- FCF 전환율 = FCF / 순이익(동일 기준 YTD/YTD). > 100% 고품질; < 60% 경고.\n"
            "- FCF 마진 = FCF / 매출(동일 기준).\n"
            "- 가능하면 YTD 차분으로 분기 FCF 도출.\n"
            "- 주주환원(자사주매입 + 배당, YTD). 모든 기간 두 항목이 비었으면 "
            "'해당 기간 동안 회사는 자사주를 매입하거나 배당을 지급하지 않았다' 라고 명시. "
            "'데이터 미제공' 이라고 하지 말 것.\n"
            "- CapEx 집약도 = CapEx / 매출. 자산 경량형인지 자본집약형인지 판단.\n\n"
            "## 6. 주당가치 & 희석\n"
            "- 희석 EPS 추이(수치).\n"
            "- 주당 장부가치 = 자기자본 / 발행주식수, 매 기간. 버크셔의 오랜 자체 스코어카드 — 순차 변화 제시.\n"
            "- 기간 내 희석주식수 변화(%). 유동주식 증가는 순이익이 늘어도 주당가치를 훼손.\n"
            "- 기본 vs 희석 EPS 격차 — 격차 확대는 전환사채/미기속 주식 희석 경고.\n\n"
            "## 7. 투자 판정(버핏 관점)\n"
            "다음을 순서대로 4-6 문장으로 답하세요:\n"
            "1) 지속적 경쟁우위(해자) 존재?\n"
            "2) 경영진의 자본배분(재투자/자사주/배당/M&A) 이 합리적?\n"
            "3) 대차대조표가 2008 식 침체를 견딜 수 있는 방어력을 가지고 있는가?\n"
            "4) ROE/ROIC/오너 어닝스/주당 장부가치 추세로 볼 때 10년 보유할 만한가?\n"
            "5) 최근 " + str(n) + " 개 분기 데이터에서 가장 큰 단일 리스크는?\n"
            "6) 한 줄 판정: STRONG BUY / BUY / WATCH / AVOID (가치투자 관점) + 짧은 이유.\n\n"
            "포맷 요구사항(엄격 — 위반 시 다운스트림 렌더링 손상):\n"
            "- 마크다운 본문만 출력. 최상위 제목/코드블록/서론/마무리 문장 금지.\n"
            "- 일반 ASCII 괄호 ( ) 만 사용. \\( \\) 절대 금지 — LaTeX 이스케이프로 수식 렌더링됨.\n"
            "- 일반 %, $, & 사용 (역슬래시 이스케이프 금지).\n"
            "- 현금흐름/손익 수치는 YTD, Quarterly, '분기 도출(YTD 차분)' 로 반드시 표기.\n"
            "- 전 기간 비어있는 행은 건너뛰고, 값을 지어내지 마세요.\n"
            "- 버핏 임계값 통과/미달을 명시 (예: 'ROE 22.4% — 15% 버핏 하한 통과' 또는 "
            "'이자보상 3.1배 — 5배 버핏 하한 미달')."
        )

    def _build_context_table(self, bundle: CompanyReportsBundle) -> str:
        filings = bundle.filings
        period_labels = [self._period_label(f) for f in filings]
        header_cells = ["Metric"] + period_labels
        separator = ["---"] + ["---:" for _ in period_labels]

        lines: list[str] = []
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append("| " + " | ".join(separator) + " |")

        def append_section(
            title: str, rows: list[tuple[str, str]], accessor: str, basis_attr: str
        ) -> None:
            section_rows: list[str] = []
            for concept, label in rows:
                cells = [label]
                any_value = False
                for filing in filings:
                    values: dict = getattr(filing, accessor, {}) or {}
                    value = values.get(concept)
                    if value is None:
                        cells.append("")
                    else:
                        any_value = True
                        cells.append(self._format_number(value))
                if any_value:
                    section_rows.append("| " + " | ".join(cells) + " |")
            if section_rows:
                basis = self._section_basis(filings, basis_attr)
                header = f"{title} ({basis})" if basis else title
                lines.append("| **" + header + "** |" + " |" * len(period_labels))
                lines.extend(section_rows)

        append_section(
            "Income Statement",
            _INCOME_ROWS,
            "income_statement",
            "income_period_label",
        )
        append_section(
            "Balance Sheet",
            _BALANCE_ROWS,
            "balance_sheet",
            "balance_period_label",
        )
        append_section(
            "Cash Flow",
            _CASHFLOW_ROWS,
            "cash_flow",
            "cash_flow_period_label",
        )
        return "\n".join(lines)

    @staticmethod
    def _period_label(filing: FilingSummary) -> str:
        period = (filing.period_of_report or "").strip()
        if period:
            return period
        filed = (filing.filing_date or "").strip()
        return filed or filing.form or "?"

    @staticmethod
    def _section_basis(filings: list[FilingSummary], basis_attr: str) -> str:
        """Summarize the reporting basis across filings (Quarterly, YTD, ...).

        edgartools annotates period columns with `(Q1)`/`(Q2)`/`(Q3)`/`(YTD)`
        or leaves them bare for point-in-time balance-sheet dates. We surface
        that suffix so the LLM knows whether a Cash Flow row is a single
        quarter or year-to-date — a distinction the SEC 10-Q form forces
        upon us (cash-flow statements are always YTD in a 10-Q).
        """
        seen: list[str] = []
        for filing in filings:
            label = getattr(filing, basis_attr, "") or ""
            if "(YTD)" in label and "YTD" not in seen:
                seen.append("YTD")
            elif "(Q" in label and "Quarterly" not in seen:
                seen.append("Quarterly")
        return " / ".join(seen)

    @staticmethod
    def _format_number(value: float) -> str:
        try:
            magnitude = abs(float(value))
        except (TypeError, ValueError):
            return ""
        if magnitude >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if magnitude >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if magnitude >= 1_000:
            return f"{value / 1_000:.2f}K"
        return f"{value:.2f}"
