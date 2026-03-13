"""
status_engine.py
----------------
Evaluates allocation status for every (location, product, customer) combination
based on current tank inventory levels and active lockouts.

Rules:
  - For each (location, product):
      available = tank_level - sum(lockouts for that location+product)
      if available <= 0:
          customers who OWN a lockout  → ACTIVE   (they have reserved inventory)
          all other customers          → INACTIVE  (no inventory left for them)
      else:
          all customers                → ACTIVE

Returns a dict keyed by (location, product, customer) -> {
    "status": "active" | "inactive",
    "reason": str or None,          # shown in badge if inactive
    "locked_by": list[str]          # customer names holding lockouts
}
"""

from __future__ import annotations
from typing import Any


def evaluate_statuses(
    forecast_df,           # full pandas DataFrame with columns: location, product, customer
    tank_levels: dict,     # {(location, product): float}
    lockouts: list[dict],  # [{"location", "product", "customer", "amount"}, ...]
) -> dict[tuple, dict[str, Any]]:
    """
    Evaluate allocation statuses across all location/product/customer combos.

    Returns
    -------
    dict keyed by (location, product, customer) ->
        {
            "status":    "active" | "inactive",
            "reason":    human-readable reason string (None if active),
            "locked_by": list of customer names holding lockouts for this loc+product
        }
    """
    statuses: dict[tuple, dict] = {}

    # Group lockouts by (location, product)
    lockout_map: dict[tuple, list[dict]] = {}
    for lo in lockouts:
        key = (lo["location"], lo["product"])
        lockout_map.setdefault(key, []).append(lo)

    # Get every unique (location, product, customer) combo from the forecast
    combos = (
        forecast_df[["location", "product", "customer"]]
        .drop_duplicates()
        .values
        .tolist()
    )

    # Pre-compute per (location, product): available inventory and locked customers
    lp_cache: dict[tuple, dict] = {}
    for loc, prod, _ in combos:
        lp_key = (loc, prod)
        if lp_key in lp_cache:
            continue

        tank_vol   = tank_levels.get(lp_key, 0.0)
        los        = lockout_map.get(lp_key, [])
        total_lock = sum(lo["amount"] for lo in los)
        available  = tank_vol - total_lock
        locked_customers = list({lo["customer"] for lo in los})

        lp_cache[lp_key] = {
            "tank_vol":         tank_vol,
            "total_lock":       total_lock,
            "available":        available,
            "locked_customers": locked_customers,
        }

    # Assign status to every combo
    for loc, prod, cust in combos:
        lp_key  = (loc, prod)
        cache   = lp_cache[lp_key]
        combo_key = (loc, prod, cust)

        if cache["available"] <= 0 and cache["total_lock"] > 0:
            # Inventory fully consumed by lockouts
            if cust in cache["locked_customers"]:
                statuses[combo_key] = {
                    "status":    "active",
                    "reason":    None,
                    "locked_by": cache["locked_customers"],
                }
            else:
                locked_names = ", ".join(cache["locked_customers"])
                statuses[combo_key] = {
                    "status":    "inactive",
                    "reason":    f"Inventory fully locked by: {locked_names}",
                    "locked_by": cache["locked_customers"],
                }
        else:
            # Enough inventory available for everyone
            statuses[combo_key] = {
                "status":    "active",
                "reason":    None,
                "locked_by": cache["locked_customers"],
            }

    return statuses


def get_status(
    statuses: dict,
    location: str,
    product: str,
    customer: str,
) -> dict[str, Any]:
    """
    Convenience helper — fetch a single status entry.
    Returns active with no reason if the combo isn't found.
    """
    return statuses.get(
        (location, product, customer),
        {"status": "active", "reason": None, "locked_by": []}
    )


def inactive_count(statuses: dict) -> int:
    """Return the number of inactive allocations across all combos."""
    return sum(1 for v in statuses.values() if v["status"] == "inactive")
