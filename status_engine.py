"""
status_engine.py
----------------
Evaluates allocation status for every (location, product, customer) combination
based on current tank inventory levels and active lockouts.

CUTOFF MODES
────────────
hard_cutoff=False  (Standard Mode — default)
  When available inventory <= 0:
    - Customers who OWN a lockout  → ACTIVE   (their inventory is reserved)
    - All other customers          → INACTIVE

hard_cutoff=True  (Hard Cut Mode)
  When available inventory <= 0:
    - ALL customers                → INACTIVE (full supply stop, no exceptions)

Returns a dict keyed by (location, product, customer) -> {
    "status":    "active" | "inactive",
    "reason":    str or None,
    "locked_by": list[str]
}
"""

from __future__ import annotations
from typing import Any


def evaluate_statuses(
    forecast_df,
    tank_levels:  dict,
    lockouts:     list[dict],
    hard_cutoff:  bool = False,
) -> dict[tuple, dict[str, Any]]:

    statuses: dict[tuple, dict] = {}

    # Group lockouts by (location, product)
    lockout_map: dict[tuple, list[dict]] = {}
    for lo in lockouts:
        key = (lo["location"], lo["product"])
        lockout_map.setdefault(key, []).append(lo)

    # All unique (location, product, customer) combos from forecast
    combos = (
        forecast_df[["location", "product", "customer"]]
        .drop_duplicates()
        .values
        .tolist()
    )

    # Pre-compute per (location, product)
    lp_cache: dict[tuple, dict] = {}
    for loc, prod, _ in combos:
        lp_key = (loc, prod)
        if lp_key in lp_cache:
            continue
        tank_vol         = tank_levels.get(lp_key, 0.0)
        los              = lockout_map.get(lp_key, [])
        total_lock       = sum(lo["amount"] for lo in los)
        available        = tank_vol - total_lock
        locked_customers = list({lo["customer"] for lo in los})
        lp_cache[lp_key] = {
            "tank_vol":         tank_vol,
            "total_lock":       total_lock,
            "available":        available,
            "locked_customers": locked_customers,
        }

    # Assign status
    for loc, prod, cust in combos:
        lp_key    = (loc, prod)
        cache     = lp_cache[lp_key]
        combo_key = (loc, prod, cust)

        if cache["available"] <= 0 and cache["total_lock"] > 0:
            if hard_cutoff:
                # Hard Cut: everyone inactive, no exceptions
                statuses[combo_key] = {
                    "status":    "inactive",
                    "reason":    "Hard cut active — inventory at zero (all allocations stopped)",
                    "locked_by": cache["locked_customers"],
                }
            elif cust in cache["locked_customers"]:
                # Standard: locked customer stays active
                statuses[combo_key] = {
                    "status":    "active",
                    "reason":    None,
                    "locked_by": cache["locked_customers"],
                }
            else:
                # Standard: unprotected customer goes inactive
                locked_names = ", ".join(cache["locked_customers"])
                statuses[combo_key] = {
                    "status":    "inactive",
                    "reason":    f"Inventory fully locked by: {locked_names}",
                    "locked_by": cache["locked_customers"],
                }

        elif cache["available"] <= 0 and cache["total_lock"] == 0:
            # Zero inventory, no lockouts — everyone inactive regardless of mode
            statuses[combo_key] = {
                "status":    "inactive",
                "reason":    "Inventory at zero — no supply available",
                "locked_by": [],
            }

        else:
            statuses[combo_key] = {
                "status":    "active",
                "reason":    None,
                "locked_by": cache["locked_customers"],
            }

    return statuses


def get_status(
    statuses: dict,
    location: str,
    product:  str,
    customer: str,
) -> dict[str, Any]:
    return statuses.get(
        (location, product, customer),
        {"status": "active", "reason": None, "locked_by": []}
    )


def inactive_count(statuses: dict) -> int:
    return sum(1 for v in statuses.values() if v["status"] == "inactive")
