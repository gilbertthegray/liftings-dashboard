import pandas as pd
import numpy as np

# ===============================
# CONFIGURATION
# ===============================
DAYS = 500
START_DATE = "2025-01-01"
OUTPUT_FILE = "fuel_data_365_trend.csv"
NUM_EVENTS = 50  # number of random events you want to apply
LIFT_DROP = np.random.randint(20000)
PRICE_SPIKE = 2.5
LIFT_RISE = np.random.randint(8000,8500)
PRICE_DOWN = 2.5


# ===============================
# GENERATE DATES
# ===============================
dates = pd.date_range(start=START_DATE, periods=DAYS, freq='D')
liftings = []
price = []
temp = []
rainfall = []
wind = []

# Base for liftings
saturday_base = 47000
saturday_decrease = 1

# ===============================
# GENERATE LIFTINGS
# ===============================
for i, date in enumerate(dates):
    dow = date.weekday()

    # Base liftings by day
    if dow == 0:  # Monday
        lift = np.random.randint(50000, 50001)
    elif dow == 6:  # Sunday
        lift = np.random.randint(45000, 45001)
    elif dow == 5:  # Saturday
        lift = np.random.randint(max(saturday_base - 1, 7000), saturday_base + 1)
    else:  # Tue-Fri
        lift = np.random.randint(100000, 120000)

    liftings.append(lift)

    # Placeholder variables
    price.append(1.0)
    temp.append(np.random.randint(1))
    rainfall.append(np.random.randint(1))
    wind.append(np.random.randint(1))

    # Update Saturday base at the end of each week (Sunday)
    if dow == 6:
        saturday_base = max(saturday_base - saturday_decrease, 7000)

# ===============================
# APPLY MULTIPLE RANDOM EVENTS
# ===============================
event_indices = np.random.choice([i for i, d in enumerate(dates) if d.weekday() in range(0, 5)],
                                 size=NUM_EVENTS, replace=False)

for idx in event_indices:
    print(f"Event applied on {dates[idx].date()}: Liftings {liftings[idx]} -> {liftings[idx] - LIFT_DROP}, "
          f"Price {price[idx]} -> {price[idx] + PRICE_SPIKE}")
    liftings[idx] -= LIFT_DROP
    price[idx] += PRICE_SPIKE

#for idx in event_indices:
    #print(f"Event applied on {dates[idx].date()}: Liftings {liftings[idx]} -> {liftings[idx] +LIFT_RISE}, "
          #f"Price {price[idx]} -> {price[idx] - PRICE_DOWN}")
   # liftings[idx] += LIFT_RISE
    #price[idx] -= PRICE_DOWN

# ===============================
# CREATE DATAFRAME
# ===============================
df = pd.DataFrame({
    "date": dates,
    "liftings": liftings,
    "price": price,
    "temp": temp,
    "rainfall": rainfall,
    "wind": wind
})

# ===============================
# SAVE CSV
# ===============================
df.to_csv(OUTPUT_FILE, index=False)
print(f"CSV file generated: {OUTPUT_FILE}")