"""
price_feed.py
-------------
Live fuel price fetcher using the EIA v2 API.

SECRETS FORMAT (in .streamlit/secrets.toml or Streamlit Cloud → Secrets):

    [eia]
    api_key = "your32charkey"

    # Optional — only if you have an OPIS subscription:
    [opis]
    api_key  = "your-opis-key"
    terminal = "HOUSTON"

EIA API key registration (free, instant):
    https://www.eia.gov/opendata/register.php
"""

from __future__ import annotations

import traceback
import urllib.parse
from datetime import datetime
from typing import Optional

import requests
import streamlit as st


# ── Fallback prices ($/gallon, approximate US 2025 averages) ──────────────────
_FALLBACK: dict[str, float] = {
    "Gasoline":    3.35,
    "Diesel":      3.75,
    "Jet Fuel":    2.90,
    "Heating Oil": 3.60,
    "E85":         2.80,
    "Premium":     3.90,
}
_FALLBACK_DATE = "Static default — no live data"

# ── Verified EIA v2 series IDs ────────────────────────────────────────────────
# Route:  /v2/petroleum/pri/gnd/data/
# Unit:   cents per gallon -> we divide by 100 to get $/gallon
# Docs:   https://www.eia.gov/opendata/browser/petroleum/pri/gnd
_EIA_SERIES: dict[str, str] = {
    "REG":    "EMD_EPD2D_PTE_NUS_DPG",
    "ULSD":      "EMD_EPM0D_PTE_NUS_DPG",
    "Heating Oil": "EMA_EPM0HO_PTE_NUS_DPG",
    "PREM":     "EMD_EPDC_PTE_NUS_DPG",
}

_EIA_BASE = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
_TIMEOUT  = 10


# ── Result type ────────────────────────────────────────────────────────────────

class PriceResult:
    __slots__ = ("price", "unit", "source", "as_of", "is_live", "is_stale",
                 "error", "raw_response", "http_status")

    def __init__(
        self,
        price:        float,
        unit:         str  = "$/gallon",
        source:       str  = "default",
        as_of:        str  = _FALLBACK_DATE,
        is_live:      bool = False,
        is_stale:     bool = True,
        error:        str  = "",
        raw_response: str  = "",
        http_status:  int  = 0,
    ):
        self.price        = price
        self.unit         = unit
        self.source       = source
        self.as_of        = as_of
        self.is_live      = is_live
        self.is_stale     = is_stale
        self.error        = error
        self.raw_response = raw_response
        self.http_status  = http_status

    def badge_html(self) -> str:
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
            f'letter-spacing:0.05em;font-family:monospace;">{label}</span>'
        )


# ── EIA fetcher ────────────────────────────────────────────────────────────────

def _fetch_eia(product: str, api_key: Optional[str] = None) -> PriceResult:
    series = _EIA_SERIES.get(product)
    if not series:
        return PriceResult(
            price  = _FALLBACK.get(product, 3.00),
            source = f"Default — no EIA series for '{product}'",
            error  = f"No series mapped. Known: {list(_EIA_SERIES.keys())}",
        )

    params: dict = {
        "frequency":          "weekly",
        "data[0]":            "value",
        "facets[series][]":   series,
        "sort[0][column]":    "period",
        "sort[0][direction]": "desc",
        "length":             1,
        "out":                "json",
    }
    if api_key:
        params["api_key"] = api_key

    raw_text    = ""
    http_status = 0

    try:
        resp        = requests.get(_EIA_BASE, params=params, timeout=_TIMEOUT)
        http_status = resp.status_code
        raw_text    = resp.text[:800]
        resp.raise_for_status()

        body = resp.json()
        rows = body.get("response", {}).get("data", [])

        if not rows:
            return PriceResult(
                price        = _FALLBACK.get(product, 3.00),
                source       = "Default — EIA returned no data rows",
                error        = (
                    f"Series '{series}' returned 0 rows. "
                    "Series may be inactive. Check: "
                    "https://www.eia.gov/opendata/browser/petroleum/pri/gnd"
                ),
                raw_response = raw_text,
                http_status  = http_status,
            )

        row   = rows[0]
        value = row.get("value")

        if value is None or str(value).strip() in ("", "None", "null"):
            return PriceResult(
                price        = _FALLBACK.get(product, 3.00),
                source       = "Default — EIA value was null",
                error        = f"Row returned but value=null. Row data: {row}",
                raw_response = raw_text,
                http_status  = http_status,
            )

        cents   = float(value)
        dollars = round(cents / 100.0, 3)
        period  = str(row.get("period", ""))

        stale = True
        if period:
            try:
                dt    = datetime.strptime(period, "%Y-%m-%d")
                stale = (datetime.now() - dt).days > 10
            except ValueError:
                pass

        return PriceResult(
            price        = dollars,
            unit         = "$/gallon",
            source       = "EIA API — weekly retail" + (" (with key)" if api_key else " (no key)"),
            as_of        = period,
            is_live      = True,
            is_stale     = stale,
            raw_response = raw_text,
            http_status  = http_status,
        )

    except requests.exceptions.ConnectionError as exc:
        return PriceResult(
            price=_FALLBACK.get(product, 3.00),
            source="Default — connection refused",
            error=f"ConnectionError: {exc}",
            raw_response=raw_text, http_status=http_status,
        )
    except requests.exceptions.Timeout:
        return PriceResult(
            price=_FALLBACK.get(product, 3.00),
            source=f"Default — timed out after {_TIMEOUT}s",
            error="EIA did not respond in time. Try again.",
            raw_response=raw_text, http_status=http_status,
        )
    except requests.exceptions.HTTPError:
        return PriceResult(
            price=_FALLBACK.get(product, 3.00),
            source=f"Default — HTTP {http_status}",
            error=(
                f"HTTP {http_status}. "
                + ("Bad or missing API key. " if http_status in (401, 403) else "")
                + f"Response: {raw_text[:300]}"
            ),
            raw_response=raw_text, http_status=http_status,
        )
    except Exception:
        return PriceResult(
            price=_FALLBACK.get(product, 3.00),
            source="Default — unexpected error",
            error=traceback.format_exc()[-400:],
            raw_response=raw_text, http_status=http_status,
        )


# ── OPIS stub ──────────────────────────────────────────────────────────────────

def _fetch_opis(product: str, api_key: str, terminal: str = "") -> PriceResult:
    raise NotImplementedError("OPIS stub — implement once you have credentials.")


# ── Main fetch function (no module-level cache so key changes take effect) ─────

def get_live_prices(products: tuple[str, ...]) -> dict[str, PriceResult]:
    """
    Fetch prices for each product. Reads secrets fresh on every call —
    no stale cache from before the key was added.
    """
    eia_cfg  = st.secrets.get("eia",  {})
    opis_cfg = st.secrets.get("opis", {})
    eia_key  = eia_cfg.get("api_key", "").strip()
    opis_key = opis_cfg.get("api_key", "").strip()

    results: dict[str, PriceResult] = {}

    for product in products:
        if opis_key:
            try:
                results[product] = _fetch_opis(
                    product, opis_key, opis_cfg.get("terminal", "")
                )
                continue
            except (NotImplementedError, Exception):
                pass

        results[product] = _fetch_eia(product, api_key=eia_key or None)

    return results


# ── Debug panel ────────────────────────────────────────────────────────────────

def render_price_debug_panel(products: tuple[str, ...]) -> None:
    """
    Drop this into the Price Sensitivity tab to diagnose feed issues.
    Shows: secrets detection, HTTP status, raw response, full errors.
    """
    with st.expander("🔧 Price Feed Debug Panel", expanded=True):

        eia_cfg  = st.secrets.get("eia",  {})
        opis_cfg = st.secrets.get("opis", {})
        eia_key  = eia_cfg.get("api_key", "").strip()
        opis_key = opis_cfg.get("api_key", "").strip()

        # ── Secrets check ──────────────────────────────────────────────────────
        st.markdown("**Step 1 — Secrets detection**")
        c1, c2 = st.columns(2)

        with c1:
            if eia_key:
                st.success(
                    f"✅ EIA key found\n\n"
                    f"Value (redacted): `{eia_key[:6]}...{eia_key[-4:]}`\n\n"
                    f"Length: {len(eia_key)} characters"
                )
            else:
                st.error(
                    "❌ **EIA key NOT found.**\n\n"
                    "Expected format in Streamlit Cloud Secrets:\n"
                    "```\n[eia]\napi_key = \"yourkey\"\n```\n\n"
                    "Common mistakes:\n"
                    "- `[eia] api_key = ...` on one line (wrong)\n"
                    "- Extra spaces around the `=`\n"
                    "- Key wrapped in the wrong quote type"
                )

        with c2:
            if opis_key:
                st.success(f"✅ OPIS key found (`{opis_key[:4]}...`)")
            else:
                st.info("ℹ️ No OPIS key — EIA will be used")

        st.markdown("---")
        st.markdown("**Step 2 — Live fetch (bypasses all caching)**")

        if st.button("🔄 Clear Cache & Force Refresh", key="debug_force_fetch"):
            st.cache_data.clear()
            st.rerun()

        for product in products:
            series = _EIA_SERIES.get(product, "NO SERIES MAPPED")

            # Show the exact URL being called (key redacted)
            display_params = {
                "frequency":          "weekly",
                "data[0]":            "value",
                "facets[series][]":   series,
                "sort[0][column]":    "period",
                "sort[0][direction]": "desc",
                "length":             "1",
                "out":                "json",
                "api_key":            f"{eia_key[:6]}...{eia_key[-4:]}" if eia_key else "(none)",
            }
            display_url = _EIA_BASE + "?" + urllib.parse.urlencode(display_params)

            st.markdown(f"**{product}** — series `{series}`")
            st.code(display_url, language="text")

            result = _fetch_eia(product, api_key=eia_key or None)

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("HTTP Status", result.http_status or "—")
            mc2.metric("Price",       f"${result.price:.3f}")
            mc3.metric("Live",        "✅" if result.is_live else "❌")
            mc4.metric("Stale",       "⚠️ Yes" if result.is_stale else "✅ No")

            if result.error:
                st.error(f"**Error detail:** {result.error}")

            if result.raw_response:
                st.markdown("**Raw API response:**")
                st.code(result.raw_response, language="json")

            st.markdown("---")


def price_source_note(result: PriceResult) -> str:
    parts = [f"Source: {result.source}"]
    if result.as_of and result.as_of != _FALLBACK_DATE:
        parts.append(f"As of: {result.as_of}")
    if result.error:
        parts.append(f"⚠️ {result.error[:100]}")
    return " · ".join(parts)
