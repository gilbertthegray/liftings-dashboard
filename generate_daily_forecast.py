import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# -----------------------------
# CONFIGURATION
# -----------------------------
start_date = datetime.today().date()
num_days = 100

locations = ["A", "B", "C"]
products = ["REG", "PREM", "ULSD"]

# Base daily liftings per product
base_liftings = {
    "REG": 50000,
    "PREM": 30000,
    "ULSD": 70000
}

# Random variation percentage (+/-)
variation_pct = 0.15  # 15%

# -----------------------------
# GENERATE DATA
# -----------------------------
data = []

for day in range(num_days):
    current_date = start_date + timedelta(days=day)

    for location in locations:
        for product in products:

            base = base_liftings[product]

            # Add daily variation
            variation = np.random.uniform(
                -variation_pct,
                variation_pct
            )

            liftings = base * (1 + variation)

            data.append({
                "date": current_date,
                "location": location,
                "product": product,
                "liftings": round(liftings, 0)
            })

# -----------------------------
# CREATE DATAFRAME
# -----------------------------
df = pd.DataFrame(data)

# Sort cleanly
df = df.sort_values(["date", "location", "product"])

# -----------------------------
# SAVE CSV
# -----------------------------
df.to_csv("daily_forecast_batchplanner.csv", index=False)

print("daily_forecast_batchplanner.csv created successfully.")
print(df.head())