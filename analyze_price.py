import pandas as pd
import numpy as np

# ===============================
# LOAD DATA
# ===============================
df = pd.read_csv("fuel_data_365_trend.csv", parse_dates=['date'])
df = df.sort_values('date')
df.set_index('date', inplace=True)

# ===============================
# CALCULATE PERCENT CHANGE AND DIRECTION
# ===============================
# Percent change in liftings and price
df['liftings_pct_change'] = df['liftings'].pct_change().fillna(0) * 100
df['price_pct_change'] = df['price'].pct_change().fillna(0) * 100

# Direction: +1 up, -1 down, 0 no change
df['liftings_direction'] = np.sign(df['liftings_pct_change'])
df['price_direction'] = np.sign(df['price_pct_change'])

# ===============================
# CORRELATION BETWEEN PRICE AND LIFTINGS
# ===============================
# Use vectorized correlation
corr = df['price'].corr(df['liftings'])
corr_pct = df['price_pct_change'].corr(df['liftings_pct_change'])

print(f"Correlation (absolute): {corr:.4f}")
print(f"Correlation (% change): {corr_pct:.4f}")

# ===============================
# EFFECT PER PRICE RANGE
# ===============================
# Define price bins
bins = [0, 1, 2, 3, 4, 5, np.inf]
labels = ['0-1', '1-2', '2-3', '3-4', '4-5', '>5']
df['price_range'] = pd.cut(df['price'], bins=bins, labels=labels)

# Calculate median liftings change per price range (absolute & percent)
range_effects = df.groupby('price_range').agg(
    median_liftings_abs_change=('liftings', lambda x: x.diff().median()),
    median_liftings_pct_change=('liftings_pct_change', 'median'),
    direction=('liftings_direction', lambda x: 'positive' if x.mean() > 0 else 'negative' if x.mean() < 0 else 'neutral')
).reset_index()

# Map back to dataframe
effect_abs = dict(zip(range_effects['price_range'], range_effects['median_liftings_abs_change']))
effect_pct = dict(zip(range_effects['price_range'], range_effects['median_liftings_pct_change']))
direction_map = dict(zip(range_effects['price_range'], range_effects['direction']))

df['expected_liftings_abs_change'] = df['price_range'].map(effect_abs).fillna(0)
df['expected_liftings_pct_change'] = df['price_range'].map(effect_pct).fillna(0)
df['expected_liftings_direction'] = df['price_range'].map(direction_map).fillna('neutral')

# ===============================
# SAVE RESULTS
# ===============================
print("\nAnalysis complete. Saved to 'fuel_data_price_effect_correlation.csv'")