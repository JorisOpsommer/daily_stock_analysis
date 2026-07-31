"""SEC EDGAR company reports fetcher (10-Q via edgartools).

Only used when INCLUDE_COMPANY_REPORTS=true and the ticker matches
`is_us_stock_code`. edgartools is imported lazily inside `fetch()` so a
missing dependency never blocks module import for users who leave the
feature off.

Design:
- Fail-open: any exception at the batch or per-filing level returns an empty
  bundle (or a bundle with fewer filings); it never raises to the pipeline.
- Bounded: caller-side timeout via a daemon thread + `.join(timeout=...)`,
  matching the pattern already used in `data_provider/base._run_with_timeout`.
- Cheap prompt: only a small whitelist of key line items is extracted, keeping
  the downstream LLM prompt compact and comparable across filings.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Whitelist of income-statement / balance-sheet / cash-flow line items to try
# extracting from each 10-Q. Kept intentionally small so the LLM prompt stays
# short and quarter-over-quarter comparisons are easy to read. Values are
# best-effort; any missing concept is silently skipped for that filing.
_INCOME_STATEMENT_CONCEPTS: list[str] = [
    "Revenues",
    "Revenue",
    "TotalRevenue",
    "CostOfRevenue",
    "GrossProfit",
    "OperatingIncomeLoss",
    "OperatingExpenses",
    "ResearchAndDevelopmentExpense",
    "SellingGeneralAndAdministrativeExpense",
    "InterestExpense",
    "DepreciationAndAmortization",
    # Pretax income + tax expense enable effective-tax-rate and NOPAT/ROIC math,
    # which are core Buffett-style capital-return metrics.
    "IncomeLossBeforeIncomeTaxes",
    "IncomeTaxExpenseBenefit",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "WeightedAverageNumberOfSharesOutstandingDiluted",
]

_BALANCE_SHEET_CONCEPTS: list[str] = [
    "Assets",
    "CurrentAssets",
    "CashAndCashEquivalentsAtCarryingValue",
    "ShortTermInvestments",
    "AccountsReceivableNetCurrent",
    "InventoryNet",
    "Goodwill",
    "IntangibleAssetsNetExcludingGoodwill",
    "PropertyPlantAndEquipmentNet",
    "AccountsPayableCurrent",
    "CurrentLiabilities",
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "ShortTermBorrowings",
    "Liabilities",
    "StockholdersEquity",
    "RetainedEarningsAccumulatedDeficit",
    "TreasuryStockValue",
    "CommonStockSharesOutstanding",
]

_CASHFLOW_CONCEPTS: list[str] = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "DepreciationDepletionAndAmortization",
    # Buffett treats share-based compensation as a real cash-equivalent expense;
    # exposing it lets the analyzer flag "cosmetic" earnings.
    "ShareBasedCompensation",
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsOfDividendsCommonStock",
]


@dataclass
class FilingSummary:
    """Compact snapshot of a single 10-Q filing suitable for LLM comparison."""

    form: str
    filing_date: str = ""
    period_of_report: str = ""
    # Standardized concept -> numeric value (as reported by the filing).
    income_statement: dict[str, float] = field(default_factory=dict)
    balance_sheet: dict[str, float] = field(default_factory=dict)
    cash_flow: dict[str, float] = field(default_factory=dict)
    # Column labels used when extracting each statement (e.g.
    # `2026-06-27 (Q3)` for a quarterly income statement, `2026-06-27 (YTD)`
    # for a year-to-date cash-flow statement, or `2026-06-27` for the
    # point-in-time balance sheet). Consumers use these to disambiguate
    # quarterly vs. YTD figures in downstream analysis.
    income_period_label: str = ""
    balance_period_label: str = ""
    cash_flow_period_label: str = ""
    # Free-form notes we managed to extract (e.g. reporting currency, unit).
    notes: dict[str, str] = field(default_factory=dict)


@dataclass
class CompanyReportsBundle:
    """Collection of the last N 10-Q filings for a single US ticker."""

    ticker: str
    filings: list[FilingSummary] = field(default_factory=list)
    # Reporting currency reported by the most recent filing (e.g. "USD").
    currency: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.filings


class CompanyReportsService:
    """Wrapper around edgartools that returns a compact `CompanyReportsBundle`.

    Instantiate once per pipeline. `set_identity()` is called lazily on first
    `fetch()` with the email address from `SEC_EDGAR_IDENTITY`; changing it at
    runtime therefore requires a restart, which matches how other SDK-scoped
    config (e.g. Longbridge region) already behaves.
    """

    def __init__(
        self,
        identity: str | None,
        filing_count: int = 4,
        fetch_timeout_seconds: float = 20.0,
    ) -> None:
        self._identity = (identity or "").strip() or None
        self._filing_count = max(1, min(int(filing_count or 1), 8))
        self._fetch_timeout_seconds = max(1.0, float(fetch_timeout_seconds or 20.0))
        self._identity_configured = False
        self._identity_lock = threading.Lock()

    @property
    def is_available(self) -> bool:
        """True when the service has an SEC identity configured.

        Does NOT check whether edgartools is importable; that check happens
        inside `fetch()` so a missing package produces a single warning at
        first use rather than blocking init.
        """
        return self._identity is not None

    def fetch(self, ticker: str) -> CompanyReportsBundle | None:
        """Fetch the last N 10-Q filings for `ticker`.

        Returns `None` when the feature is unusable (missing identity, missing
        edgartools, or the batch timed out). Returns an empty bundle when the
        ticker has no 10-Q filings (rare, but possible for very new IPOs).
        """
        if not self._identity:
            logger.debug(
                "[company_reports] fetch skipped: SEC_EDGAR_IDENTITY not configured"
            )
            return None
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return None
        logger.info(
            "[company_reports] fetching %s (count=%d, timeout=%.1fs)",
            symbol,
            self._filing_count,
            self._fetch_timeout_seconds,
        )

        result_holder: dict[str, CompanyReportsBundle | None] = {"value": None}
        error_holder: dict[str, BaseException | None] = {"error": None}

        def _run() -> None:
            try:
                result_holder["value"] = self._fetch_impl(symbol)
            except BaseException as exc:  # noqa: BLE001 — thread boundary
                error_holder["error"] = exc

        worker = threading.Thread(
            target=_run,
            name=f"company-reports-{symbol}",
            daemon=True,
        )
        worker.start()
        worker.join(timeout=self._fetch_timeout_seconds)
        if worker.is_alive():
            logger.warning(
                "[company_reports] fetch timed out after %.1fs for %s (fail-open)",
                self._fetch_timeout_seconds,
                symbol,
            )
            return None
        if error_holder["error"] is not None:
            logger.warning(
                "[company_reports] fetch failed for %s (fail-open): %s",
                symbol,
                error_holder["error"],
            )
            return None
        return result_holder["value"]

    # ------------------------------------------------------------------ internals

    def _ensure_identity(self) -> bool:
        """Call `edgar.set_identity()` once per process. Returns False on failure."""
        if self._identity_configured:
            return True
        with self._identity_lock:
            if self._identity_configured:
                return True
            if not self._identity:
                return False
            try:
                from edgar import set_identity  # type: ignore
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[company_reports] edgartools not importable (fail-open): %s. "
                    "Install `edgartools` or set INCLUDE_COMPANY_REPORTS=false.",
                    exc,
                )
                return False
            try:
                set_identity(self._identity)
                self._identity_configured = True
                logger.info(
                    "[company_reports] SEC EDGAR identity configured: %s",
                    self._identity,
                )
                return True
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[company_reports] set_identity failed (fail-open): %s",
                    exc,
                )
                return False

    def _fetch_impl(self, symbol: str) -> CompanyReportsBundle | None:
        if not self._ensure_identity():
            return None
        try:
            from edgar import Company  # type: ignore
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[company_reports] edgartools import failed (fail-open): %s", exc
            )
            return None

        try:
            company = Company(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "[company_reports] Company(%s) lookup failed (fail-open): %s",
                symbol,
                exc,
            )
            return None
        logger.debug("[company_reports] Company(%s) resolved via SEC EDGAR", symbol)

        try:
            filings_iter = company.get_filings(form="10-Q")
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "[company_reports] get_filings(10-Q) failed for %s (fail-open): %s",
                symbol,
                exc,
            )
            return None

        selected = self._select_recent(filings_iter, self._filing_count)
        if not selected:
            logger.info("[company_reports] no 10-Q filings found for %s", symbol)
            return CompanyReportsBundle(ticker=symbol)
        logger.info(
            "[company_reports] selected %d 10-Q filing(s) for %s", len(selected), symbol
        )

        bundle = CompanyReportsBundle(ticker=symbol)
        for filing in selected:
            summary = self._extract_filing_summary(filing)
            if summary is None:
                continue
            bundle.filings.append(summary)
            if bundle.currency is None:
                currency = summary.notes.get("currency")
                if currency:
                    bundle.currency = currency
        logger.info(
            "[company_reports] bundle complete for %s: %d/%d filing(s) extracted, currency=%s",
            symbol,
            len(bundle.filings),
            len(selected),
            bundle.currency or "unknown",
        )
        return bundle

    @staticmethod
    def _select_recent(filings_iter: Any, count: int) -> list[Any]:
        """Pick the `count` most recent filings from whatever edgartools returns.

        edgartools has changed the return shape across versions (list-like,
        pandas-backed `Filings`, generator). We probe common APIs in order.
        """
        if filings_iter is None:
            return []
        # Preferred: .head(n) on Filings collection.
        head = getattr(filings_iter, "head", None)
        if callable(head):
            try:
                head_result = head(count)
                return list(head_result)
            except Exception:  # noqa: BLE001
                pass
        # Fallback: slicing.
        try:
            return list(filings_iter[:count])
        except Exception:  # noqa: BLE001
            pass
        # Last resort: iterate and stop.
        collected: list[Any] = []
        try:
            for item in filings_iter:
                collected.append(item)
                if len(collected) >= count:
                    break
        except Exception:  # noqa: BLE001
            return collected
        return collected

    def _extract_filing_summary(self, filing: Any) -> FilingSummary | None:
        """Extract a compact summary from one filing; fail-open per filing."""
        try:
            form = str(getattr(filing, "form", "") or "10-Q")
            filing_date = self._safe_str(getattr(filing, "filing_date", ""))
            period = self._safe_str(
                getattr(filing, "period_of_report", None)
                or getattr(filing, "report_date", None)
                or ""
            )
        except Exception:  # noqa: BLE001
            return None

        summary = FilingSummary(
            form=form,
            filing_date=filing_date,
            period_of_report=period,
        )

        try:
            obj = filing.obj()
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "[company_reports] filing.obj() failed (%s / %s): %s",
                form,
                filing_date,
                exc,
            )
            return summary  # keep header, empty values — better than dropping

        financials = getattr(obj, "financials", None)
        if financials is None:
            return summary

        income, income_label = self._extract_concepts(
            financials,
            "income_statement",
            _INCOME_STATEMENT_CONCEPTS,
            prefer_quarterly=True,
        )
        balance, balance_label = self._extract_concepts(
            financials, "balance_sheet", _BALANCE_SHEET_CONCEPTS
        )
        cashflow, cashflow_label = self._extract_concepts(
            financials, "cash_flow_statement", _CASHFLOW_CONCEPTS
        )
        summary.income_statement = income
        summary.balance_sheet = balance
        summary.cash_flow = cashflow
        summary.income_period_label = income_label
        summary.balance_period_label = balance_label
        summary.cash_flow_period_label = cashflow_label
        logger.debug(
            "[company_reports] filing %s (%s): income=%d [%s], balance=%d [%s], cashflow=%d [%s] concept(s) extracted",
            form,
            period or filing_date or "?",
            len(income),
            income_label or "-",
            len(balance),
            balance_label or "-",
            len(cashflow),
            cashflow_label or "-",
        )

        currency = self._infer_currency(financials)
        if currency:
            summary.notes["currency"] = currency
        return summary

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        try:
            return str(value)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _extract_concepts(
        financials: Any,
        statement_attr: str,
        concepts: list[str],
        prefer_quarterly: bool = False,
    ) -> tuple[dict[str, float], str]:
        """Pull a small set of concepts from an edgartools financial statement.

        edgartools `Statement.to_dataframe()` returns a DataFrame with a
        `concept` column (e.g. `us-gaap_NetIncomeLoss`), a `standard_concept`
        column with edgartools' own canonical names (e.g. `NetIncome`), a
        `dimension` bool flag for segment/breakdown rows, and one column per
        reporting period (e.g. `2026-06-27 (Q3)`, `2026-06-27 (YTD)`). We
        match aliases against both `concept` and `standard_concept`, filter
        out dimensional rows, and pick a value column. When
        `prefer_quarterly` is True, the leftmost `(Q…)` column is preferred
        so income statements reflect the current quarter rather than YTD;
        otherwise the leftmost period column wins (which for 10-Q cash-flow
        statements is YTD, as SEC filings do not report per-quarter cash
        flow). Returns the extracted values and the column label used.
        """
        try:
            statement_fn = getattr(financials, statement_attr, None)
            statement = statement_fn() if callable(statement_fn) else statement_fn
        except Exception:  # noqa: BLE001
            return {}, ""
        if statement is None:
            return {}, ""

        try:
            import pandas as pd  # type: ignore
        except Exception:  # noqa: BLE001
            return {}, ""

        df: Any = None
        try:
            if isinstance(statement, pd.DataFrame):
                df = statement
            else:
                to_df = getattr(statement, "to_dataframe", None)
                if callable(to_df):
                    df = to_df()
        except Exception:  # noqa: BLE001
            return {}, ""
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {}, ""

        # Drop segment/breakdown rows so we only match top-level line items.
        if "dimension" in df.columns:
            try:
                df = df[~df["dimension"].fillna(False).astype(bool)]
            except Exception:  # noqa: BLE001
                pass
        if df.empty:
            return {}, ""

        # Identify period value columns (anything starting with YYYY-MM-DD).
        import re

        date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}")
        period_cols = [
            c for c in df.columns if isinstance(c, str) and date_pat.match(c)
        ]
        if not period_cols:
            return {}, ""
        value_col = period_cols[0]
        if prefer_quarterly:
            quarterly = next(
                (c for c in period_cols if "(Q" in c),
                None,
            )
            if quarterly is not None:
                value_col = quarterly

        # Build fast lookups from XBRL concept and standard_concept to value.
        by_concept: dict[str, float] = {}
        by_std: dict[str, float] = {}
        if "concept" in df.columns:
            for key, raw in zip(df["concept"], df[value_col]):
                if key is None:
                    continue
                key_str = str(key).strip()
                if not key_str or key_str.lower() == "nan":
                    continue
                numeric = _coerce_float(raw)
                if numeric is not None and key_str not in by_concept:
                    by_concept[key_str] = numeric
        if "standard_concept" in df.columns:
            for key, raw in zip(df["standard_concept"], df[value_col]):
                if key is None:
                    continue
                key_str = str(key).strip()
                if not key_str or key_str.lower() == "nan":
                    continue
                numeric = _coerce_float(raw)
                if numeric is not None and key_str not in by_std:
                    by_std[key_str] = numeric

        out: dict[str, float] = {}
        for concept in concepts:
            for alias in _concept_aliases(concept):
                # Match XBRL concept name (with or without namespace prefix).
                for name in (alias, f"us-gaap_{alias}", f"dei_{alias}"):
                    if name in by_concept:
                        out[concept] = by_concept[name]
                        break
                if concept in out:
                    break
                # Match edgartools standard_concept column.
                if alias in by_std:
                    out[concept] = by_std[alias]
                    break
                # Suffix match for company-specific namespaces (e.g. aapl_).
                suffix = f"_{alias}"
                hit = next(
                    (v for k, v in by_concept.items() if k.endswith(suffix)),
                    None,
                )
                if hit is not None:
                    out[concept] = hit
                    break

        if not out:
            logger.debug(
                "[company_reports] _extract_concepts(%s): no concepts resolved (value_col=%s, rows=%d)",
                statement_attr,
                value_col,
                len(df),
            )
        return out, value_col

    @staticmethod
    def _infer_currency(financials: Any) -> str | None:
        # edgartools exposes get_currency_symbol() on the Financials object.
        symbol_fn = getattr(financials, "get_currency_symbol", None)
        if callable(symbol_fn):
            try:
                sym = symbol_fn()
            except Exception:  # noqa: BLE001
                sym = None
            if isinstance(sym, str) and sym.strip():
                mapping = {
                    "$": "USD",
                    "US$": "USD",
                    "€": "EUR",
                    "£": "GBP",
                    "¥": "CNY",
                    "HK$": "HKD",
                    "NT$": "TWD",
                    "₩": "KRW",
                    "₹": "INR",
                }
                stripped = sym.strip()
                return mapping.get(stripped, stripped.upper())
        for attr in ("currency", "reporting_currency", "unit"):
            value = getattr(financials, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
        return None


# Map canonical concept -> alternative XBRL tags or attribute names.
# Aliases are matched against both the `concept` column (with/without
# `us-gaap_` prefix) and the `standard_concept` column that edgartools
# renders in `Statement.to_dataframe()`.
_ALIAS_MAP: dict[str, list[str]] = {
    "Revenue": [
        "Revenue",
        "Revenues",
        "TotalRevenue",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "Revenues": [
        "Revenues",
        "Revenue",
        "TotalRevenue",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "TotalRevenue": ["TotalRevenue", "Revenues", "Revenue"],
    "CostOfRevenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfSales",
    ],
    "GrossProfit": ["GrossProfit"],
    "OperatingIncomeLoss": ["OperatingIncomeLoss"],
    "OperatingExpenses": [
        "OperatingExpenses",
        "TotalOperatingExpenses",
        "CostsAndExpenses",
    ],
    "ResearchAndDevelopmentExpense": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenses",
    ],
    "SellingGeneralAndAdministrativeExpense": [
        "SellingGeneralAndAdministrativeExpense",
        "SellingGeneralAndAdminExpenses",
        "GeneralAndAdministrativeExpense",
    ],
    "NetIncomeLoss": [
        "NetIncomeLoss",
        "NetIncome",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "IncomeLossBeforeIncomeTaxes": [
        # Formal XBRL tags for pre-tax income vary widely across filers.
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterest",
        "IncomeBeforeIncomeTaxes",
        "IncomeLossBeforeIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
        "PretaxIncome",
        "IncomeBeforeTax",
    ],
    "IncomeTaxExpenseBenefit": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxExpense",
        "IncomeTaxesPaid",
        "ProvisionForIncomeTaxes",
    ],
    "LongTermDebt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
    "ShortTermBorrowings": [
        "ShortTermBorrowings",
        "ShortTermDebt",
        "CommercialPaper",
        "CurrentPortionOfLongTermDebt",
        "LongTermDebtCurrent",
    ],
    "InterestExpense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNet",
    ],
    "DepreciationAndAmortization": [
        "DepreciationAndAmortization",
        "DepreciationDepletionAndAmortization",
        "DepreciationExpense",
        "Depreciation",
    ],
    "AccountsReceivableNetCurrent": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
        "ReceivablesNetCurrent",
        "TradeReceivables",
    ],
    "InventoryNet": [
        "InventoryNet",
        "Inventories",
        "InventoryFinishedGoods",
    ],
    "AccountsPayableCurrent": [
        "AccountsPayableCurrent",
        "AccountsPayable",
        "AccountsPayableTradeCurrent",
        "TradeAndOtherPayablesCurrent",
    ],
    "Assets": ["Assets"],
    "CurrentAssets": ["CurrentAssets", "AssetsCurrent", "CurrentAssetsTotal"],
    "CurrentLiabilities": [
        "CurrentLiabilities",
        "LiabilitiesCurrent",
        "CurrentLiabilitiesTotal",
    ],
    "Liabilities": ["Liabilities"],
    "IntangibleAssetsNetExcludingGoodwill": [
        "IntangibleAssetsNetExcludingGoodwill",
        "IntangibleAssetsNetExcludingGoodwillNoncurrent",
        "IntangibleAssetsNet",
        "OtherIntangibleAssetsNet",
    ],
    "PropertyPlantAndEquipmentNet": [
        "PropertyPlantAndEquipmentNet",
        "PlantPropertyEquipmentNet",
        "PropertyPlantAndEquipment",
    ],
    "StockholdersEquity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "RetainedEarningsAccumulatedDeficit": [
        "RetainedEarningsAccumulatedDeficit",
        "RetainedEarnings",
    ],
    "CashAndCashEquivalentsAtCarryingValue": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndMarketableSecurities",
    ],
    "TreasuryStockValue": ["TreasuryStockValue", "TreasuryStockCommonValue"],
    "CommonStockSharesOutstanding": [
        "CommonStockSharesOutstanding",
        "CommonStockSharesIssued",
        "EntityCommonStockSharesOutstanding",
    ],
    "WeightedAverageNumberOfSharesOutstandingDiluted": [
        "WeightedAverageNumberOfSharesOutstandingDiluted",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "SharesFullyDilutedAverage",
    ],
    "NetCashProvidedByUsedInOperatingActivities": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashFromOperatingActivities",
    ],
    "NetCashProvidedByUsedInInvestingActivities": [
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashFromInvestingActivities",
    ],
    "NetCashProvidedByUsedInFinancingActivities": [
        "NetCashProvidedByUsedInFinancingActivities",
        "NetCashFromFinancingActivities",
    ],
    "PaymentsToAcquirePropertyPlantAndEquipment": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditures",
        "CapitalExpenses",
        "PurchaseOfPropertyPlantAndEquipment",
    ],
    "DepreciationDepletionAndAmortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationExpense",
    ],
    "ShareBasedCompensation": [
        "ShareBasedCompensation",
        "StockBasedCompensation",
        "ShareBasedPaymentArrangementNoncashExpense",
        "AllocatedShareBasedCompensationExpense",
    ],
    "PaymentsForRepurchaseOfCommonStock": [
        "PaymentsForRepurchaseOfCommonStock",
        "PaymentsForRepurchaseOfEquity",
        "RepurchaseOfCommonStock",
        "StockRepurchasedDuringPeriodValue",
    ],
    "PaymentsOfDividendsCommonStock": [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
        "DividendsPaid",
        "Dividends",
    ],
    "ShortTermInvestments": [
        "ShortTermInvestments",
        "MarketableSecuritiesCurrent",
        "AvailableForSaleSecuritiesCurrent",
    ],
    "Goodwill": ["Goodwill"],
    "EarningsPerShareBasic": ["EarningsPerShareBasic"],
    "EarningsPerShareDiluted": ["EarningsPerShareDiluted"],
}


def _concept_aliases(concept: str) -> list[str]:
    """Return the canonical concept plus common alias spellings."""
    return _ALIAS_MAP.get(concept, [concept])


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        # pandas NaN / numpy nan safe check
        import math

        as_float = float(value)
        if math.isnan(as_float) or math.isinf(as_float):
            return None
        return as_float
    except (TypeError, ValueError):
        return None
    except Exception:  # noqa: BLE001
        return None
