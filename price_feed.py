"""
price_feed.py
-------------
Fetches current fuel rack/retail prices to use as the baseline
in the Price Sensitivity tab.

ABOUT OPIS (industry standard):
  OPIS (Oil Price Information Service) is the gold-standard source for
  rack, DTW, and spot fuel prices used by terminals, distributors, and
  refiners across North America. It requires a paid subscription.

  If your company has OPIS access:
    1. Get your API key from your OPIS account manager
    2. Add to secrets.toml:  [opis]  api_key = "your-key"
    3. The fetch_opis_price() stub below shows where to plug it in

OTHER INDUSTRY SOURCES:
  - OPIS (opisnet.com)        — rack/DTW/spot, paid, most granular
  - Platts (spglobal.com)     — spot/futures benchmarks, paid
  - DTNGM (dtn.com)           — terminal rack prices, paid
  - GasBuddy API              — retail pump prices, freemium
  - EIA (eia.gov)             — weekly retail/wholesale, FREE ✓

WHAT THIS MODULE USES (free, no key required by default):
  EIA (U.S. Energy Information Administration) weekly retail prices.
  These are the most authoritative publicly available benchmarks in
  the US and are standard for planning and analysis when real-time
  rack prices are not needed.

  With a free EIA API key (register at eia.gov/opendata):
    - Higher rate limits
    - More series available

HOW TO GET AN EIA API KEY (optional, free):
  1. Go to https://www.eia.gov/opendata/register.php
  2. Register with your email — key arrives instantly
  3. Add to secrets.toml:  [eia]  api_key = "your-32-char-key"

FALLBACK CHAIN:
  1. EIA API with key (if [eia] api_key in secrets.toml)
  2. EIA API without key (rate-limited but free)
  3. Static defaults (always works, shown as "Offline / Default")
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import requests
import streamlit as st


# ── Fallback prices ($/gallon, approximate US mid-2025 averages) ──────────────
_FALLBACK: dict[str, float] = {
    "Gasoline":    3.35,
    "Diesel":      3.75,
    "Jet Fuel":    2.90,
    "Heating Oil": 3.60,
    "E85":         2.80,
    "Premium":     3.90,
    "Default":     3.00,
}
_FALLBACK_DATE = "Static default (no live data)"

# EIA weekly series IDs → (series_id, unit_label)
# All EIA petroleum series are in cents/gallon → we divide by 100
_EIA_SERIES: dict[str, str] = {
    "Gasoline":    "EMD_EPD2D_PTE_NUS_DPG",   # Regular gasoline, US retail
    "Diesel":      "EMD_EPM0D_PTE_NUS_DPG",   # No. 2 diesel, US retail
    "Heating Oil": "EMA_EPM0HO_PTE_NUS_DPG",  # No. 2 heating oil, US retail
    "Premium":     "EMD_EPDC_PTE_NUS_DPG",    # Premium gasoline, US retail
}

_EIA_BASE = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
_TIMEOUT  = 6   # seconds


# ── Result type ────────────────────────────────────────────────────────────────

class PriceResult:
    __slots__ = ("price", "unit", "source", "as_of", "is_live", "is_stale", "error")

    def __init__(
        self,
        price:    float,
        unit:     str  = "$/gallon",
        source:   str  = "default",
        as_of:    str  = _FALLBACK_DATE,
        is_live:  bool = False,
        is_stale: bool = True,
        error:    str  = "",
    ):
        self.price    = price
        self.unit     = unit
        self.source   = source
        self.as_of    = as_of
        self.is_live  = is_live
        self.is_stale = is_stale
        self.error    = error

    def badge_html(self) -> str:
        """Return a small HTML status pill for display next to the price."""
        if self.is_live and not self.is_stale:
            color, label = "#10B981", "LIVE"
        elif self.is_live and self.is_stale:
            color, label = "#F59E0B", "STALE"
        else:
            color, label = "#475569", "DEFAULT"

        return (
            f'<span style="background:{color}22;color:{color};'
            f'border:1px solid {color}55;border-radius:4px;'
            f'padding:1px 7px;font-size:10px;font-weight:700;'
            f'letter-spacing:0.05em;font-family:monospace;">'
            f'{label}</span>'
        )


# ── EIA fetcher ────────────────────────────────────────────────────────────────

def _fetch_eia(product: str, api_key: Optional[str] = None) -> PriceResult:
    """Fetch latest EIA weekly retail price for a product."""
    series = _EIA_SERIES.get(product)
    if not series:
        return PriceResult(
            price  = _FALLBACK.get(product, _FALLBACK["Default"]),
            source = f"Default (no EIA series mapped for '{product}')",
        )

    params: dict = {
        "frequency":            "weekly",
        "data[0]":              "value",
        "facets[series][]":     series,
        "sort[0][column]":      "period",
        "sort[0][direction]":   "desc",
        "length":               1,
        "out":                  "json",
    }
    if api_key:
        params["api_key"] = api_key

    try:
        resp = requests.get(_EIA_BASE, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json().get("response", {}).get("data", [])

        if not rows:
            raise ValueError("EIA returned empty data")

        row     = rows[0]
        cents   = float(row["value"])
        dollars = round(cents / 100.0, 3)
        period  = row.get("period", "")

        stale = True
        if period:
            try:
                dt    = datetime.strptime(period, "%Y-%m-%d")
                stale = (datetime.now() - dt).days > 10
            except ValueError:
                pass

        return PriceResult(
            price    = dollars,
            unit     = "$/gallon",
            source   = "EIA (weekly retail)",
            as_of    = period,
            is_live  = True,
            is_stale = stale,
        )

    except requests.exceptions.ConnectionError:
        return PriceResult(
            price  = _FALLBACK.get(product, _FALLBACK["Default"]),
            source = "Default (no internet connection)",
            error  = "ConnectionError",
        )
    except Exception as exc:
        return PriceResult(
            price  = _FALLBACK.get(product, _FALLBACK["Default"]),
            source = f"Default (EIA error: {type(exc).__name__})",
            error  = str(exc)[:120],
        )


# ── OPIS stub ──────────────────────────────────────────────────────────────────

def _fetch_opis(product: str, api_key: str, terminal: str = "") -> PriceResult:
    """
    OPIS rack price fetcher stub — requires a paid OPIS subscription.

    TO ACTIVATE:
      1. Obtain your API credentials from your OPIS account manager
         at https://www.opisnet.com
      2. Confirm which endpoint your subscription covers:
           Rack:   https://api.opisnet.com/v1/rack/prices
           DTW:    https://api.opisnet.com/v1/dtw/prices
           Spot:   https://api.opisnet.com/v1/spot/prices
      3. Replace the URL, headers, and params below with your details
      4. Add to secrets.toml:
             [opis]
             api_key  = "your-key"
             terminal = "HOUSTON"    # optional terminal code
      5. In get_live_prices() below, call _fetch_opis() instead of _fetch_eia()

    Typical OPIS rack request (example — confirm with your rep):
        headers = {"Authorization": f"Bearer {api_key}"}
        params  = {"product": product, "terminal": terminal, "date": "latest"}
        resp    = requests.get("https://api.opisnet.com/v1/rack/prices",
                               headers=headers, params=params, timeout=8)
        price   = resp.json()["price"]   # already in $/gallon
    """
    raise NotImplementedError(
        "OPIS requires a paid subscription. "
        "Contact your OPIS account manager or visit https://www.opisnet.com. "
        "Once you have credentials, implement this function following the "
        "instructions in the docstring above."
    )


# ── Main public function ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_live_prices(products: tuple[str, ...]) -> dict[str, PriceResult]:
    """
    Fetch current prices for the given product tuple.
    Cached for 1 hour — EIA only updates weekly anyway.

    Priority:
      1. OPIS (if [opis] api_key in secrets.toml)
      2. EIA with key (if [eia] api_key in secrets.toml)
      3. EIA without key (free, rate-limited)
      4. Static fallback
    """
    # Check for OPIS key first
    opis_key = st.secrets.get("opis", {}).get("api_key", "")
    # Check for EIA key
    eia_key  = st.secrets.get("eia",  {}).get("api_key", "")

    results: dict[str, PriceResult] = {}

    for product in products:
        if opis_key:
            try:
                terminal = st.secrets.get("opis", {}).get("terminal", "")
                results[product] = _fetch_opis(product, opis_key, terminal)
                continue
            except NotImplementedError:
                pass   # OPIS not implemented yet — fall through to EIA
            except Exception:
                pass   # OPIS failed — fall through to EIA

        # EIA (with or without key)
        results[product] = _fetch_eia(product, api_key=eia_key or None)

    return results


def price_source_note(result: PriceResult) -> str:
    """Return a plain-text source note for display under a price."""
    parts = [f"Source: {result.source}"]
    if result.as_of and result.as_of != _FALLBACK_DATE:
        parts.append(f"As of: {result.as_of}")
    if result.error:
        parts.append(f"Error: {result.error}")
    return " · ".join(parts)
