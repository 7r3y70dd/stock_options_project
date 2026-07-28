"""MarketData.app data provider implementation.

Provides stock quotes, historical candles, and options chains through
MarketData.app's REST API.

Data recency depends on your MarketData.app plan and OPRA/UTP entitlements.
Treat free/trial data as delayed or historical unless your account explicitly
has real-time entitlement.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

import requests

from app.data_sources.data_provider import (
    DataProvider,
    EarningsDate,
    NewsArticle,
    OptionChainEntry,
    PriceBar,
    Quote,
)

logger = logging.getLogger(__name__)


class MarketDataProvider(DataProvider):
    """Data provider backed by MarketData.app."""

    BASE_URL = "https://api.marketdata.app"

    def __init__(
        self,
        token: Optional[str] = None,
        request_timeout_seconds: int = 25,
        strike_limit: Optional[int] = None,
        dte: Optional[int] = None,
    ) -> None:
        self.token = (
            token
            or os.getenv("MARKETDATA_TOKEN")
            or os.getenv("MARKETDATA_API_KEY")
        )

        if not self.token:
            raise ValueError(
                "MarketData.app token is required. Set MARKETDATA_TOKEN in your environment."
            )

        self.request_timeout_seconds = request_timeout_seconds

        # Keep free/trial usage sane. dev_ingest calls get_options_chain(symbol)
        # without an expiration, so default to one expiration near 30 DTE and
        # only a limited set of strikes.
        self.strike_limit = int(os.getenv("MARKETDATA_STRIKE_LIMIT", strike_limit or 12))
        self.dte = int(os.getenv("MARKETDATA_DTE", dte or 30))

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def _request(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        response = requests.get(
            url,
            headers=self._headers(),
            params=params or {},
            timeout=self.request_timeout_seconds,
        )

        # MarketData.app can return 203 from cache with the same body shape as 200.
        if response.status_code not in {200, 203}:
            try:
                body = response.json()
            except Exception:
                body = response.text[:500]
            raise RuntimeError(
                f"MarketData.app HTTP {response.status_code} for {path}: {body}"
            )

        data = response.json()

        if isinstance(data, dict) and data.get("s") == "error":
            raise RuntimeError(f"MarketData.app error for {path}: {data.get('errmsg') or data}")

        return data

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _array_get(data: dict[str, Any], key: str, index: int, default: Any = None) -> Any:
        values = data.get(key)

        if not isinstance(values, list):
            return default

        if index >= len(values):
            return default

        return values[index]

    @staticmethod
    def _timestamp_to_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None

        try:
            return datetime.fromtimestamp(int(value))
        except Exception:
            return None

    @staticmethod
    def _timestamp_to_date(value: Any) -> str:
        if value is None:
            return ""

        # MarketData.app returns expiration as a Unix timestamp.
        try:
            return datetime.fromtimestamp(int(value)).date().isoformat()
        except Exception:
            return str(value)[:10]

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get latest available stock quote for a symbol."""
        ticker = symbol.upper().strip()

        try:
            data = self._request(
                f"/v1/stocks/quotes/{ticker}/",
                params={"extended": "false"},
            )

            if data.get("s") == "no_data":
                logger.warning("No MarketData.app quote for %s", ticker)
                return None

            # Single-symbol endpoint still returns array-shaped response.
            price = (
                self._safe_float(self._array_get(data, "last", 0))
                or self._safe_float(self._array_get(data, "mid", 0))
            )

            if price is None:
                logger.warning("No MarketData.app quote price for %s: %s", ticker, data)
                return None

            return Quote(
                symbol=ticker,
                price=price,
                bid=self._safe_float(self._array_get(data, "bid", 0)),
                ask=self._safe_float(self._array_get(data, "ask", 0)),
                volume=self._safe_int(self._array_get(data, "volume", 0)),
                timestamp=self._timestamp_to_datetime(self._array_get(data, "updated", 0)),
            )
        except Exception as exc:
            logger.warning("Error fetching MarketData.app quote for %s: %s", ticker, exc)
            return None

    def get_price_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "daily",
    ) -> list[PriceBar]:
        """Get stock OHLCV candles."""
        ticker = symbol.upper().strip()

        resolution_map = {
            "daily": "D",
            "day": "D",
            "weekly": "W",
            "week": "W",
            "monthly": "M",
            "month": "M",
        }
        resolution = resolution_map.get(interval.lower(), "D")

        try:
            data = self._request(
                f"/v1/stocks/candles/{resolution}/{ticker}/",
                params={
                    "from": start_date,
                    "to": end_date,
                    "adjustsplits": "true",
                },
            )

            if data.get("s") == "no_data":
                return []

            closes = data.get("c") or []
            highs = data.get("h") or []
            lows = data.get("l") or []
            opens = data.get("o") or []
            times = data.get("t") or []
            volumes = data.get("v") or []

            bars: list[PriceBar] = []
            count = min(len(closes), len(highs), len(lows), len(opens), len(times), len(volumes))

            for i in range(count):
                date = self._timestamp_to_date(times[i])

                bars.append(
                    PriceBar(
                        date=date,
                        open=float(opens[i]),
                        high=float(highs[i]),
                        low=float(lows[i]),
                        close=float(closes[i]),
                        volume=int(volumes[i] or 0),
                        adjusted_close=float(closes[i]),
                    )
                )

            return bars
        except Exception as exc:
            logger.warning("Error fetching MarketData.app history for %s: %s", ticker, exc)
            return []

    def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None,
    ) -> list[OptionChainEntry]:
        """Get latest available options chain for an underlying symbol."""
        ticker = symbol.upper().strip()

        params: dict[str, Any] = {
            # Keep credit usage controlled.
            "strikeLimit": self.strike_limit,
            "nonstandard": "false",
            "minOpenInterest": 1,
        }

        if expiration:
            params["expiration"] = expiration
        else:
            # Return one expiration closest to this DTE instead of all expirations.
            params["dte"] = self.dte

        try:
            data = self._request(f"/v1/options/chain/{ticker}/", params=params)

            if data.get("s") == "no_data":
                logger.warning("No MarketData.app options chain for %s", ticker)
                return []

            option_symbols = data.get("optionSymbol") or []
            count = len(option_symbols)

            contracts: list[OptionChainEntry] = []

            for i in range(count):
                contract_type = self._array_get(data, "side", i)
                exp = self._timestamp_to_date(self._array_get(data, "expiration", i))
                strike = self._safe_float(self._array_get(data, "strike", i))

                if not contract_type or not exp or strike is None:
                    continue

                contracts.append(
                    OptionChainEntry(
                        symbol=ticker,
                        expiration=exp,
                        strike=strike,
                        contract_type=str(contract_type).lower(),
                        bid=self._safe_float(self._array_get(data, "bid", i)),
                        ask=self._safe_float(self._array_get(data, "ask", i)),
                        last=self._safe_float(
                            self._array_get(data, "last", i)
                            or self._array_get(data, "mid", i)
                        ),
                        volume=self._safe_int(self._array_get(data, "volume", i)),
                        open_interest=self._safe_int(self._array_get(data, "openInterest", i)),
                        implied_volatility=self._safe_float(self._array_get(data, "iv", i)),
                        delta=self._safe_float(self._array_get(data, "delta", i)),
                        gamma=self._safe_float(self._array_get(data, "gamma", i)),
                        theta=self._safe_float(self._array_get(data, "theta", i)),
                        vega=self._safe_float(self._array_get(data, "vega", i)),
                        rho=None,
                    )
                )

            if not contracts:
                logger.warning("MarketData.app returned no usable options contracts for %s", ticker)

            return contracts
        except Exception as exc:
            logger.warning("Error fetching MarketData.app options chain for %s: %s", ticker, exc)
            return []

    def get_news(self, symbol: str, limit: int = 10) -> list[NewsArticle]:
        """MarketData.app news is not wired here yet."""
        return []

    def get_earnings_date(self, symbol: str) -> Optional[EarningsDate]:
        """MarketData.app earnings endpoint is premium; not wired here yet."""
        return None
