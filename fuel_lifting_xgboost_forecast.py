import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from datetime import timedelta

# ===============================
# CONFIG
# ===============================

DATA_FILE = "fuel_data_365_trend.csv"
FORECAST_DAYS = 100
TEST_SPLIT = 0.2
MAX_LIFT = 200000
MIN_LIFT = 2000
OUTPUT_FILE = "monthly_fuel_headers.csv"
# ===============================
# FUTURE PRICE CONTROL
# ===============================

USE_PRICE_SCENARIO = True

# Staged future price events
PRICE_EVENTS = [
   #{"day": 60, "type": "set", "value": 2.5},     # force price = 1
    #{"day": 90, "type": "set", "value": 3.5},
    #{"day": 95, "type": "set", "value": 5.5},
    #{"day": 100, "type": "set", "value": 3.5},
]

# Optional steady daily drift (set to 0 to disable)
DAILY_PRICE_DRIFT = 0.0


# ===============================
# LOAD DATA
# ===============================

df = pd.read_csv(DATA_FILE)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")
df.set_index("date", inplace=True)

df["liftings"] = df["liftings"].clip(MIN_LIFT, MAX_LIFT)


# ===============================
# FEATURE ENGINEERING
# ===============================

def create_features(data):
    df = data.copy()

    for lag in [1,2,3,7,14,21,30]:
        df[f'lag_{lag}'] = df['liftings'].shift(lag)
        df["price_x_lag1"] = df["price"] * df["lag_1"]

    df["rolling_mean_7"] = df["liftings"].rolling(7).mean()
    df["rolling_mean_30"] = df["liftings"].rolling(30).mean()

    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month

    return df


df = create_features(df)
df = df.dropna()

# ===============================
# SPLIT
# ===============================

train_size = int(len(df) * (1 - TEST_SPLIT))

train = df.iloc[:train_size]
test = df.iloc[train_size:]

X_train = train.drop("liftings", axis=1)
y_train = train["liftings"]

X_test = test.drop("liftings", axis=1)
y_test = test["liftings"]

feature_columns = X_train.columns

# ===============================
# MODEL
# ===============================

model = XGBRegressor(
    n_estimators=2000,
    max_depth=6,
    learning_rate=0.02,
    subsample=0.8,
    colsample_bytree=.4,
    gamma=0,
    random_state=42,
)

model.fit(
    X_train,
    y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

# ===============================
# EVALUATION
# ===============================

preds = model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, preds))
mape = mean_absolute_percentage_error(y_test, preds) * 100

print("\nModel Performance:")
print(f"RMSE: {rmse:.2f}")
print(f"MAPE: {mape:.2f}%")

# ===============================
# FUTURE FORECAST
# ===============================

future_predictions = []
last_data = df.copy()

print("\nGenerating 120-Day Forecast:\n")

current_price = last_data["price"].iloc[-1]

for i in range(FORECAST_DAYS):

    next_date = last_data.index[-1] + timedelta(days=1)
    next_row = pd.DataFrame(index=[next_date])

    # ---------------------------------
    # FUTURE PRICE MANIPULATION LOGIC
    # ---------------------------------

    if USE_PRICE_SCENARIO:

        # Apply daily drift
        current_price *= (1 + DAILY_PRICE_DRIFT)

        # Apply staged events
        for event in PRICE_EVENTS:
            if i + 1 == event["day"]:
                if event["type"] == "add":
                    current_price += event["value"]
                elif event["type"] == "set":
                    current_price = event["value"]
                elif event["type"] == "pct":
                    current_price *= (1 + event["value"])

    next_row["price"] = current_price

    # Carry other exogenous vars
    for col in ["temp", "rainfall", "wind"]:
        next_row[col] = last_data[col].iloc[-1]

    # Calendar
    next_row["day_of_week"] = next_date.dayofweek
    next_row["month"] = next_date.month

    # Lags
    for lag in [1,2,3,7,14,21,30]:
        next_row[f"lag_{lag}"] = last_data["liftings"].iloc[-lag]

    # Rolling means
    next_row["rolling_mean_7"] = last_data["liftings"].iloc[-7:].mean()
    next_row["rolling_mean_30"] = last_data["liftings"].iloc[-30:].mean()

    next_row = next_row.reindex(columns=feature_columns)

    prediction = model.predict(next_row)[0]
    prediction = np.clip(prediction, MIN_LIFT, MAX_LIFT)

    print(f"{next_date.date()} | Price: {current_price:.2f} -> {prediction:,.0f}")

    append_row = next_row.copy()
    append_row["liftings"] = prediction

    future_predictions.append((next_date, prediction))
    last_data = pd.concat([last_data, append_row])

forecast_df = pd.DataFrame(
    future_predictions, columns=["date", "forecast"]
).set_index("date")

# ===============================
# PLOT
# ===============================

plt.figure(figsize=(12,6))
plt.plot(df.index, df["liftings"], label="Historical")
plt.plot(forecast_df.index, forecast_df["forecast"],
         linestyle="--", label="120-Day Forecast")
plt.legend()
plt.show()

df.to_csv(OUTPUT_FILE, index=False)
print(f"CSV file generated: {OUTPUT_FILE}")