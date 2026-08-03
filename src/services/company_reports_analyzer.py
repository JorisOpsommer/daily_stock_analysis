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
            "- All amounts are abbreviated: B = billion, M = million, K = thousand (e.g. "
            "12.5B = 12,500,000,000). Convert to raw units before computing any ratio.\n"
            "- Cash Flow: SEC 10-Q filings only publish year-to-date (YTD) cash-flow statements "
            "— per-quarter cash flow is never reported directly. To estimate a single quarter, "
            "take current 10-Q YTD − prior 10-Q YTD (if the prior filing is Q1, its YTD is already "
            "the Q1 stand-alone figure).\n"
            "- Annualization: to compare quarterly numbers against Buffett's annual thresholds, "
            "multiply the latest single quarter by 4, or use trailing four quarters when four "
            "sequential quarters are present.\n\n"
            "Work through the following seven analysis steps INTERNALLY. Do NOT print the "
            "detailed per-period numbers for steps 1-6 — compute them in your head, use them "
            "only to reach your conclusions, and then report just the synthesis below.\n\n"
            "1. Business Quality & Moat Signals: gross margin, operating margin, net margin "
            "per period; Buffett heuristics (consistent gross margin > 40% and net margin > 20% "
            "suggest a durable moat); SG&A and R&D as % of revenue trend; revenue growth "
            "quarter over quarter and implied annualized growth (CAGR) when 4+ quarters are shown.\n"
            "2. Return on Capital (Buffett's core focus): annualized ROE = (Net Income × 4) / "
            "Stockholders' Equity (Buffett floor > 15%); annualized ROA = (Net Income × 4) / "
            "Total Assets; annualized ROIC = (Operating Income × (1 − effective tax rate) × 4) / "
            "(Stockholders' Equity + Long-Term Debt + Short-Term Borrowings − Cash & Equivalents) "
            "(Buffett floor > 12%); effective tax rate = Income Tax Expense / Pre-Tax Income "
            "(approximate 21% US statutory rate if pre-tax income is missing and say so).\n"
            "3. Balance Sheet & Financial Durability: debt-to-equity = (Long-Term Debt + "
            "Short-Term Borrowings) / Stockholders' Equity (Buffett prefers < 0.5; > 1.0 needs "
            "justification); current ratio (> 1.5 healthy); quick ratio = (Current Assets − "
            "Inventory) / Current Liabilities (> 1.0 healthy); interest coverage = Operating "
            "Income / Interest Expense (Buffett floor > 5x); Cash + Short-Term Investments vs "
            "Total Liabilities; Goodwill as % of Total Assets.\n"
            "4. Earnings Quality & Owner Earnings: are Accounts Receivable or Inventory growing "
            "faster than Revenue (red flags); Owner Earnings (Buffett 1986) for the most recent "
            "YTD = Net Income + D&A − CapEx; Stock-Based Compensation as % of revenue (flag if "
            "> 5%); Retained Earnings trajectory.\n"
            "5. Free Cash Flow & Capital Allocation: FCF (YTD) = Operating Cash Flow − CapEx; "
            "FCF conversion = FCF / Net Income (> 100% high quality, < 60% warning); FCF margin; "
            "derived stand-alone quarterly FCF by differencing consecutive YTDs; capital returned "
            "to shareholders (Buybacks + Dividends); CapEx intensity = CapEx / Revenue.\n"
            "6. Per-Share Value & Dilution: diluted EPS trajectory; Book Value per Share = "
            "Stockholders' Equity / Shares Outstanding; diluted share count change (rising float "
            "destroys per-share value); gap between Basic and Diluted EPS.\n"
            "7. Analyst Remarks (Buffett Lens): synthesize everything above.\n\n"
            "Let's now create our answer, we want to provide an answer FOR ONLY THE FOLLOWING BELOW in this exact order, with no other content:\n\n"
            "First, write a remarks paragraph of at most 4 sentences summarizing the most "
            "notable findings that a long-term value investor would care about. Optionally, and "
            "ONLY if valuable, add one more sentence comparing this company to a well-known "
            "direct competitor, starting with 'vs. competitors:'. Do NOT invent or assert specific "
            "peer numbers (margins, growth, valuation) — the competitor's financials are not in "
            "your input data. Only reference a peer's approximate relative position if you are "
            "highly confident of it from widely-known public knowledge; otherwise state that a "
            "grounded peer comparison would require pulling the competitor's filings. Keep it to "
            "1–2 sentences and frame it as directional, not precise.\n"
            "Second, recap each of the seven steps above in a compact bullet list, in order, as "
            "Warren Buffett's conclusion for that step:\n"
            "- Business Quality & Moat Signals: <conclusion>\n"
            "- Return on Capital: <conclusion>\n"
            "- Balance Sheet & Financial Durability: <conclusion>\n"
            "- Earnings Quality & Owner Earnings: <conclusion>\n"
            "- Free Cash Flow & Capital Allocation: <conclusion>\n"
            "- Per-Share Value & Dilution: <conclusion>\n"
            "Each recap bullet may be up to 3 lines, but every conclusion must be backed by the "
            "actual numbers you computed in the steps above — never say only 'increased' or "
            "'decreased'. If a required input is missing, state which input is missing and skip "
            "that specific ratio. Never fabricate values.\n"
            "End with a single line stating the single biggest risk you see in the data, "
            "e.g. 'Biggest risk: ...'.\n"
            "\n"
            "Some formatting requirements: \n"
            "- Keep bullets tight: one line where possible, up to three where the data requires it — plain ASCII, no LaTeX escapes."
            "- Return the Markdown body only: no top-level heading, no code fence, no preamble, and nothing after the biggest-risk line. \n"
            "- Use plain ASCII parentheses ( and ). NEVER write \\( or \\) — those are LaTeX "
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
        return "todo"

    @staticmethod
    def _build_prompt_ko(
        bundle: CompanyReportsBundle,
        table: str,
        currency_hint: str,
        n: int,
    ) -> str:
        return "todo"

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
