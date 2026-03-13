# inventory_engine.py

import pandas as pd

def simulate_inventory_by_product(
    forecast_df: pd.DataFrame,
    starting_inventory: dict,
    safety_levels: dict
):
    """
    Simulates month-by-month inventory for each product.

    Parameters
    ----------
    forecast_df : DataFrame
        Must contain columns:
        ['date', 'product', 'liftings']

    starting_inventory : dict
        {'ULSD': 1000000, 'REG': 500000, ...}

    safety_levels : dict
        {'ULSD': 200000, 'REG': 100000, ...}

    Returns
    -------
    DataFrame
        Inventory simulation results per month and product
    """

    df = forecast_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M")

    # Aggregate monthly forecast per product
    monthly = (
        df.groupby(["year_month", "product"])["liftings"]
        .sum()
        .reset_index()
        .sort_values(["product", "year_month"])
    )

    results = []

    for product in monthly["product"].unique():

        product_df = monthly[monthly["product"] == product].copy()

        current_inventory = starting_inventory.get(product, 0)
        safety = safety_levels.get(product, 0)

        for _, row in product_df.iterrows():

            forecast = row["liftings"]
            month = row["year_month"]

            usable_inventory = max(current_inventory - safety, 0)

            if forecast > usable_inventory:
                shortage = forecast - usable_inventory
                ending_inventory = safety
                cuts_required = True
            else:
                shortage = 0
                ending_inventory = current_inventory - forecast
                cuts_required = False

            results.append({
                "month": str(month),
                "product": product,
                "beginning_inventory": current_inventory,
                "forecast_liftings": forecast,
                "usable_inventory": usable_inventory,
                "shortage": shortage,
                "ending_inventory": ending_inventory,
                "cuts_required": cuts_required
            })

            # Carry forward inventory
            current_inventory = ending_inventory

    return pd.DataFrame(results)