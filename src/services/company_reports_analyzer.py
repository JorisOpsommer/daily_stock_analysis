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
    ("NetCashProvidedByUsedInInvestingActivities", "Investing Cash Flow"),
    ("NetCashProvidedByUsedInFinancingActivities", "Financing Cash Flow"),
    ("PaymentsForRepurchaseOfCommonStock", "Share Buybacks"),
    ("PaymentsOfDividendsCommonStock", "Dividends Paid"),
]


class CompanyReportsAnalyzer:
    """Compose a prompt from a `CompanyReportsBundle` and run one LLM call."""

    def __init__(self, max_tokens: int = 2000, temperature: float = 0.3) -> None:
        # Low temperature: we want precise financial reasoning, not creative prose.
        self._max_tokens = max(256, int(max_tokens or 2000))
        self._temperature = float(temperature)

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
            "[company_reports] starting LLM analysis for %s: %d filing(s), language=%s, max_tokens=%d, temperature=%.2f",
            bundle.ticker,
            len(bundle.filings),
            lang,
            self._max_tokens,
            self._temperature,
        )
        prompt = self._build_prompt(bundle, lang)
        logger.debug(
            "[company_reports] prompt built for %s: %d chars",
            bundle.ticker,
            len(prompt),
        )
        try:
            text = analyzer.generate_text(
                prompt,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[company_reports] LLM analysis failed for %s (fail-open): %s",
                bundle.ticker,
                exc,
            )
            return ""
        if not text:
            logger.warning(
                "[company_reports] LLM returned empty response for %s", bundle.ticker
            )
            return ""
        result = str(text).strip()
        logger.info(
            "[company_reports] LLM analysis complete for %s: %d chars returned",
            bundle.ticker,
            len(result),
        )
        return result

    # ------------------------------------------------------------------ internals

    def _build_prompt(self, bundle: CompanyReportsBundle, report_language: str) -> str:
        table = self._build_context_table(bundle)
        currency_hint = bundle.currency or "USD"
        n = len(bundle.filings)

        # ------------------------------------------------------------------
        # The analysis framework below mirrors how a Buffett-style value
        # investor reads 10-Q filings: focus on durable competitive advantage,
        # owner earnings, capital allocation discipline, and balance sheet
        # strength.  The LLM gets raw numbers in the table and is asked to
        # compute key ratios and render an actionable verdict.
        # ------------------------------------------------------------------

        if report_language == "zh":
            return (
                f"你是一位巴菲特风格的价值投资分析师，正在为一位认真考虑长期持有 {bundle.ticker} 的投资者"
                f"撰写尽职调查备忘录。以下是该公司最近 {n} 份 SEC 10-Q 季报的关键财务数据"
                f"（金额单位默认 {currency_hint}，除非行内另有说明）。\n\n"
                f"{table}\n\n"
                "数据口径说明（重要）：\n"
                "- **利润表**：如标题标注 `(Quarterly)`，为**当季**数据；如标注 `(YTD)`，为**年初至今累计**。\n"
                "- **资产负债表**：为**期末时点**数据。\n"
                "- **现金流量表**：10-Q 规定现金流量表**只提供年初至今累计（YTD）**数据，不提供单季数据。"
                "如需当季现金流，请用**本期 YTD − 上一份 10-Q 的 YTD**做差分（若上一份为 Q1，则 Q1 YTD 即为 Q1 单季）。\n\n"
                "请基于以上数据，撰写一份 15-25 行的中文 Markdown 分析，依次覆盖：\n\n"
                "**1. 盈利质量与护城河信号**\n"
                "- 毛利率与营业利润率的走势（对每季计算数值），毛利率持续 > 40% 是护城河的重要信号\n"
                "- 净利率趋势；SG&A 占营收比例是否稳定或下降（规模效应）\n"
                "- R&D 投入趋势（维持竞争力 vs. 拖累利润）\n\n"
                "**2. 资产负债表健康度**\n"
                "- 计算 负债 / 股东权益 比率（每期末），判断杠杆是否合理\n"
                "- 现金 + 短期投资 vs. 总负债的覆盖情况\n"
                "- 应收账款与存货增速是否大幅超过营收增速（可能是收入质量恶化信号）\n"
                "- 商誉占总资产比重是否过高（收购风险）\n"
                "- 留存收益趋势：公司是否在持续积累价值\n\n"
                "**3. 自由现金流与资本配置**\n"
                "- 使用 YTD 数据计算 FCF = 经营现金流 − 资本支出；如可能，用 YTD 差分推算当季 FCF\n"
                "- 结合利润表口径评估：FCF 是否持续覆盖同口径净利润（>100% 为优质），差分时口径需一致\n"
                "- 股票回购与分红金额（同为 YTD），判断管理层是否在回馈股东\n"
                "- 资本支出趋势：维持性 CapEx 还是扩张性 CapEx\n\n"
                "**4. 每股价值与稀释**\n"
                "- EPS 趋势，基本 vs. 稀释 EPS 差异是否在扩大（稀释警示）\n"
                "- 流通股数是否在减少（回购缩股）还是增加（稀释）\n\n"
                "**5. 一段话投资结论**\n"
                "- 用 2-3 句话总结：这家公司是否具备持久竞争优势？财务趋势是在改善、稳定还是恶化？"
                "作为价值投资者，当前季报数据给出的信号是什么？\n\n"
                "要求：\n"
                "- 所有比率请计算出具体数字（如毛利率 42.3%），不要只说'提高'或'下降'\n"
                "- 引用现金流数字时，明确标注 `YTD` 或 `当季（差分）`，避免混淆\n"
                "- 直接输出 Markdown 正文，不要加最外层标题、代码块或额外说明\n"
                "- 不要重复数据表格，只做分析和推理\n"
                "- 数据为空的行请忽略"
            )
        if report_language == "ko":
            return (
                f"당신은 버핏 스타일의 가치투자 분석가입니다. {bundle.ticker} 에 장기 투자를 "
                f"진지하게 고려하는 투자자를 위한 실사 메모를 작성합니다. 다음은 해당 기업의 "
                f"최근 {n} 개 SEC 10-Q 분기보고서의 핵심 재무 데이터입니다"
                f"(금액 단위는 별도 표기가 없으면 {currency_hint}).\n\n"
                f"{table}\n\n"
                "데이터 기준(중요):\n"
                "- **손익계산서**: 제목에 `(Quarterly)` 표기 시 **해당 분기** 값, `(YTD)` 표기 시 **연초 누계** 값.\n"
                "- **재무상태표**: **기말 시점** 값.\n"
                "- **현금흐름표**: 10-Q 규정상 **연초 누계(YTD)만** 제공되며 단일 분기 값은 없음. "
                "당해 분기 현금흐름이 필요하면 **현재 YTD − 직전 10-Q의 YTD** 로 차분해서 산출(Q1이 직전이면 Q1 YTD 가 곧 Q1 단일 분기).\n\n"
                "위 데이터를 기반으로 15~25 줄의 한국어 마크다운 분석을 작성하세요:\n\n"
                "**1. 수익성 & 해자(moat) 신호**\n"
                "- 매출총이익률/영업이익률 추이 (각 분기 수치 계산), 총이익률 > 40%는 해자 신호\n"
                "- 순이익률 추이; SG&A/매출 비율이 안정적이거나 하락 중인지 (규모의 경제)\n"
                "- R&D 투자 추이\n\n"
                "**2. 재무건전성**\n"
                "- 부채/자기자본 비율 (각 기말 계산)\n"
                "- 현금 + 단기투자 vs 총부채 커버리지\n"
                "- 매출채권/재고 증가율이 매출 증가율을 초과하는지\n"
                "- 영업권 비중, 이익잉여금 추이\n\n"
                "**3. 잉여현금흐름 & 자본배분**\n"
                "- YTD 기준 FCF = 영업CF − CapEx; 가능하면 YTD 차분으로 분기 FCF 를 도출\n"
                "- FCF 가 동일 기준의 순이익을 커버하는지 (기준 일치 필요)\n"
                "- 자사주매입/배당 (모두 YTD), 자본배분 판단\n\n"
                "**4. 주당가치 & 희석**\n"
                "- EPS 추이, 발행주식수 변화\n\n"
                "**5. 투자 결론 (2~3 문장)**\n"
                "- 지속적 경쟁우위 여부, 재무 추세, 가치투자자 관점 시그널\n\n"
                "요구사항:\n"
                "- 모든 비율은 구체적 수치로 계산 (예: 총이익률 42.3%)\n"
                "- 현금흐름 수치 인용 시 `YTD` 또는 `분기(차분)` 를 반드시 표기\n"
                "- 마크다운 본문만 출력, 제목/코드블록/추가 설명 금지\n"
                "- 데이터 테이블 반복 금지, 분석과 추론만 작성\n"
                "- 데이터가 없는 항목은 무시"
            )
        # Default: English
        return (
            f"You are a Warren Buffett-style value investing analyst preparing a due diligence "
            f"memo for an investor seriously considering a long-term position in {bundle.ticker}. "
            f"Below are the last {n} SEC 10-Q quarterly reports "
            f"(amounts in {currency_hint} unless the row states otherwise).\n\n"
            f"{table}\n\n"
            "Data conventions (important):\n"
            "- **Income Statement**: section header tagged `(Quarterly)` means the **single quarter**; "
            "`(YTD)` means **year-to-date cumulative**.\n"
            "- **Balance Sheet**: point-in-time snapshot at each period end.\n"
            "- **Cash Flow**: SEC 10-Q filings only publish **year-to-date (YTD) cash-flow statements** "
            "— per-quarter cash flow is never reported directly. To estimate a single quarter, take "
            "**current 10-Q YTD − prior 10-Q YTD** (if the prior filing is Q1, its YTD is already the "
            "Q1 stand-alone figure).\n\n"
            "Based on the data above, write a rigorous 15-25 line Markdown analysis covering:\n\n"
            "**1. Earnings Quality & Moat Signals**\n"
            "- Compute gross margin and operating margin for each period shown. Consistent gross margin "
            "> 40%% is a strong moat indicator.\n"
            "- Net margin trend. Is SG&A as %% of revenue stable or declining (scale economics)?\n"
            "- R&D spending trajectory — sustaining competitive edge vs. margin drag.\n\n"
            "**2. Balance Sheet Strength**\n"
            "- Compute Debt-to-Equity ratio at each period end. Is leverage reasonable?\n"
            "- Cash + short-term investments vs. total liabilities coverage.\n"
            "- Are accounts receivable and inventory growing faster than revenue (revenue quality red flag)?\n"
            "- Goodwill as %% of total assets — acquisition risk.\n"
            "- Retained earnings trend: is the company consistently accumulating value?\n\n"
            "**3. Free Cash Flow & Capital Allocation**\n"
            "- Compute FCF = Operating Cash Flow − CapEx on the YTD figures shown; where possible, "
            "also derive stand-alone quarterly FCF by differencing consecutive YTDs.\n"
            "- Does FCF consistently cover net income (>100%% = high quality earnings)? Compare on the "
            "same basis (YTD vs. YTD, or derived-quarter vs. quarter).\n"
            "- Share buybacks and dividends paid (also YTD) — is management returning capital to shareholders?\n"
            "- CapEx trend: maintenance CapEx or expansion CapEx?\n\n"
            "**4. Per-Share Value & Dilution**\n"
            "- EPS trajectory. Is the gap between basic and diluted EPS widening (dilution warning)?\n"
            "- Is the share count declining (buybacks shrinking float) or rising (dilution)?\n\n"
            "**5. Investment Verdict (2-3 sentences)**\n"
            "- Does this company have a durable competitive advantage? Is the financial trajectory "
            "improving, stable, or deteriorating? What signal does the most recent quarter give "
            "to a value investor?\n\n"
            "Requirements:\n"
            "- Compute all ratios with actual numbers (e.g., gross margin 42.3%%), not just "
            "'increased' or 'decreased'.\n"
            "- When citing cash-flow figures, always label them as `YTD` or `derived quarter` to "
            "avoid conflating cumulative and single-period values.\n"
            "- Return the Markdown body only — no top-level heading, no code fence, no extra commentary.\n"
            "- Do not repeat the data table; analyze and reason over it.\n"
            "- Skip rows where all quarters are blank."
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
