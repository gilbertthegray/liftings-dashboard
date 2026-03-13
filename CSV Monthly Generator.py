import pandas as pd
import numpy as np

# ==================================
# CONFIG
# ==================================

START_DATE = "2022-01-01"
MONTHS = 36
OUTPUT_FILE = "monthly_fuel_liftings.csv"

np.random.seed(42)

# ==================================
# STRUCTURE
# ==================================

locations = ["A", "B", "C", "D"]

customers = [
    "Eve Fuel",
    "Johnny Pop",
    "Branded Fuel",
    "Unbranded Fuel",
    "Rack"
]

products = ["ULSD", "REG", "PREM"]

# ==================================
# BASE PRODUCT VOLUMES (per month baseline)
# ==================================

product_base = {
    "ULSD": 120000,
    "REG": 95000,
    "PREM": 40000
}

# ==================================
# CUSTOMER SHARE WEIGHTS
# ==================================

customer_weight = {
    "Eve Fuel": 0.22,
    "Johnny Pop": 0.18,
    "Branded Fuel": 0.35,
    "Unbranded Fuel": 0.20,
    "Rack": 0.5
}

# ==================================
# LOCATION SCALING
# ==================================

location_scale = {
    "A": 1.00,
    "B": 0.90,
    "C": 1.15,
    "D": 0.75
}

# ==================================
# DATE RANGE (MONTHLY)
# ==================================

dates = pd.date_range(start=START_DATE, periods=MONTHS, freq="MS")

rows = []

for date in dates:

    # Mild seasonality factor
    month_factor = 1 + 0.05 * np.sin(2 * np.pi * date.month / 12)

    for location in locations:

        for product in products:

            base_volume = (
                product_base[product]
                * location_scale[location]
                * month_factor
            )

            for customer in customers:

                volume = (
                    base_volume
                    * customer_weight[customer]
                    * np.random.normal(1.0, 0.03)  # small noise
                )

                rows.append([
                    date,
                    location,
                    customer,
                    product,
                    round(volume, 0)
                ])

# ==================================
# CREATE DATAFRAME
# ==================================

df = pd.DataFrame(
    rows,
    columns=["date", "location", "customer", "product", "liftings"]
)

df.to_csv(OUTPUT_FILE, index=False)

print(f"\nMonthly CSV generated: {OUTPUT_FILE}")