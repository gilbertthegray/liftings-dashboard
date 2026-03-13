import streamlit as st
import pandas as pd
import calendar
import numpy as np
from datetime import timedelta
from inventory_simulation import simulate_inventory_by_product
from auth import check_password, logout

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="Liftings Forecast Dashboard",
    layout="wide"
)

# ==========================================================
# AUTH GATE — nothing renders below until login succeeds
# ==========================================================
if not check_password():
    st.stop()

# ---- Logged-in header ----
col_title, col_user = st.columns([6, 1])
with col_title:
    st.title("Monthly Liftings Forecast Dashboard")
with col_user:
    st.markdown(f"👤 **{st.session_state.get('username', '')}**")
    if st.button("Sign Out", key="signout"):
        logout()

# ==========================================================
# LOAD DATA
# ==========================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("monthly_fuel_headers.csv")
    except FileNotFoundError:
        st.error("monthly_fuel_headers.csv not found.")
        st.stop()

    required_cols = ["date", "location", "customer", "product", "liftings"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["liftings"] = pd.to_numeric(df["liftings"], errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")

    return df


df = load_data()

@st.cache_data
def load_daily_data():
    try:
        df = pd.read_csv("daily_forecast_batchplanner.csv")
    except FileNotFoundError:
        st.error("daily_forecast_batchplanner.csv not found.")
        st.stop()

    required_cols = ["date", "location", "product", "liftings"]

    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing column in daily file: {col}")
            st.stop()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["liftings"] = pd.to_numeric(df["liftings"], errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")

    return df


daily_df = load_daily_data()

# ==========================================================
# MAIN TOP TABS
# ==========================================================
forecast_tab, alloc_tab, inventory_tab, batch_tab, price_sim_tab, tanks_tab = st.tabs([
    "📊 Forecast",
    "📦 Allocations",
    "🏭 Inventory Simulation",
    "🚚 Batch Planner",
    "💹 Price Sensitivity",
    "🛢️ Tank Levels"
])

# ==========================================================
# ======================= FORECAST TAB =====================
# ==========================================================
with forecast_tab:

    st.subheader("Forecast Viewer")

    month_options = sorted(df["year_month"].dropna().unique())

    selected_month = st.selectbox(
        "Select Month",
        month_options,
        key="forecast_month"
    )

    selected_customer = st.multiselect(
        "Select Customer",
        sorted(df["customer"].unique()),
        default=sorted(df["customer"].unique()),
        key="forecast_customer"
    )

    selected_product = st.multiselect(
        "Select Product",
        sorted(df["product"].unique()),
        default=sorted(df["product"].unique()),
        key="forecast_product"
    )

    scale_percent = st.number_input(
        "Scale Forecast (%)",
        min_value=-100,
        max_value=500,
        value=0,
        step=5,
        key="forecast_scale"
    )

    scale_factor = 1 + (scale_percent / 100)

    filtered_df = df[
        (df["year_month"] == selected_month) &
        (df["customer"].isin(selected_customer)) &
        (df["product"].isin(selected_product))
    ].copy()

    if filtered_df.empty:
        st.warning("No data matches filters.")
    else:
        filtered_df["Scaled_Forecast"] = (
            filtered_df["liftings"] * scale_factor
        )

        locations = sorted(filtered_df["location"].unique())
        location_tabs = st.tabs(locations)

        for i, location in enumerate(locations):
            with location_tabs[i]:

                st.markdown(f"### {location}")

                location_df = filtered_df[
                    filtered_df["location"] == location
                ]

                st.dataframe(location_df, use_container_width=True)

                col1, col2 = st.columns(2)

                col1.metric(
                    "Original Total",
                    f"{location_df['liftings'].sum():,.0f}"
                )

                col2.metric(
                    "Scaled Total",
                    f"{location_df['Scaled_Forecast'].sum():,.0f}"
                )

# ==========================================================
# ====================== ALLOCATIONS TAB ===================
# ==========================================================
with alloc_tab:

    st.subheader("Allocation Breakdown")

    month_options = sorted(df["year_month"].dropna().unique())

    selected_month = st.selectbox(
        "Select Month",
        month_options,
        key="alloc_month"
    )

    month_df = df[df["year_month"] == selected_month]

    selected_location = st.selectbox(
        "Select Location",
        sorted(month_df["location"].unique()),
        key="alloc_location"
    )

    location_df = month_df[
        month_df["location"] == selected_location
    ]

    selected_customer = st.selectbox(
        "Select Customer",
        sorted(location_df["customer"].unique()),
        key="alloc_customer"
    )

    customer_df = location_df[
        location_df["customer"] == selected_customer
    ]

    selected_product = st.selectbox(
        "Select Product",
        sorted(customer_df["product"].unique()),
        key="alloc_product"
    )

    allocation_row = customer_df[
        customer_df["product"] == selected_product
    ]

    if allocation_row.empty:
        st.warning("No allocation found.")
    else:
        total = allocation_row["liftings"].sum()

        month_dt = pd.to_datetime(selected_month)
        days_in_month = calendar.monthrange(
            month_dt.year,
            month_dt.month
        )[1]

        weekly = total / 4
        daily = total / days_in_month

        col1, col2, col3 = st.columns(3)

        col1.metric("Monthly Total", f"{total:,.0f}")
        col2.metric("Weekly (÷4)", f"{weekly:,.0f}")
        col3.metric("Daily", f"{daily:,.0f}")

        st.markdown("---")
        st.dataframe(allocation_row, use_container_width=True)

# ==========================================================
# ================= INVENTORY SIMULATION TAB ===============
# ==========================================================
with inventory_tab:

    st.subheader("Inventory Setup")

    selected_location = st.selectbox(
        "Select Location",
        sorted(df["location"].unique()),
        key="inv_location"
    )

    location_df = df[df["location"] == selected_location]

    products = sorted(location_df["product"].unique())

    starting_inventory = {}
    safety_levels = {}

    for product in products:

        col1, col2 = st.columns(2)

        with col1:
            starting_inventory[product] = st.number_input(
                f"{product} Starting Inventory",
                min_value=0.0,
                value=500000.0,
                step=10000.0,
                key=f"inv_start_{selected_location}_{product}"
            )

        with col2:
            safety_levels[product] = st.number_input(
                f"{product} Safety Level",
                min_value=0.0,
                value=100000.0,
                step=10000.0,
                key=f"inv_safety_{selected_location}_{product}"
            )

    if st.button("Run Inventory Simulation", key="inv_run"):

        sim_df = simulate_inventory_by_product(
            forecast_df=location_df,
            starting_inventory=starting_inventory,
            safety_levels=safety_levels
        )

        st.subheader("Simulation Results")
        st.dataframe(sim_df, use_container_width=True)

# ==========================================================
# ====================== BATCH PLANNER TAB =================
# ==========================================================
with batch_tab:

    st.subheader("Batch Scheduling Planner")

    monthly_planner, daily_planner = st.tabs([
        "📅 Monthly Forecast",
        "📆 Daily Forecast"
    ])

    with monthly_planner:

        selected_location = st.selectbox(
            "Select Location",
            sorted(df["location"].unique()),
            key="batch_monthly_location"
        )

        location_df = df[df["location"] == selected_location]

        month_options = sorted(location_df["year_month"].unique())

        selected_month = st.selectbox(
            "Select Month",
            month_options,
            key="batch_monthly_month"
        )

        month_df = location_df[
            location_df["year_month"] == selected_month
        ]

        selected_product = st.selectbox(
            "Select Product",
            sorted(month_df["product"].unique()),
            key="batch_monthly_product"
        )

        product_df = month_df[
            month_df["product"] == selected_product
        ]

        monthly_liftings = product_df["liftings"].sum()

        month_dt = pd.to_datetime(selected_month)
        days_in_month = calendar.monthrange(
            month_dt.year,
            month_dt.month
        )[1]

        daily_burn = monthly_liftings / days_in_month

        st.markdown("### Inventory Inputs")

        col1, col2, col3 = st.columns(3)

        beginning_inventory = col1.number_input(
            "Beginning Inventory",
            0.0, 999999999.0, 1000000.0,
            key="batch_monthly_begin"
        )

        safety_level = col2.number_input(
            "Safety Level",
            0.0, 999999999.0, 200000.0,
            key="batch_monthly_safety"
        )

        max_capacity = col3.number_input(
            "Max Capacity",
            0.0, 999999999.0, 1200000.0,
            key="batch_monthly_max"
        )

        lead_time_days = st.number_input(
            "Lead Time (Days)",
            0, 60, 5,
            key="batch_monthly_lead"
        )

        if daily_burn > 0:

            usable_inventory = beginning_inventory - safety_level
            days_until_safety = usable_inventory / daily_burn

            safety_hit_date = month_dt + timedelta(days=days_until_safety)
            order_date = safety_hit_date - timedelta(days=lead_time_days)
            batch_needed = max_capacity - safety_level

            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            col1.metric("Daily Burn", f"{daily_burn:,.0f}")
            col2.metric("Safety Hit Date", safety_hit_date.strftime("%Y-%m-%d"))
            col3.metric("Order By Date", order_date.strftime("%Y-%m-%d"))

            st.metric("Recommended Batch Size", f"{batch_needed:,.0f}")

    with daily_planner:

        selected_location = st.selectbox(
            "Select Location",
            sorted(daily_df["location"].unique()),
            key="batch_daily_location"
        )

        location_df = daily_df[
            daily_df["location"] == selected_location
        ]

        month_options = sorted(location_df["year_month"].unique())

        selected_month = st.selectbox(
            "Select Month",
            month_options,
            key="batch_daily_month"
        )

        month_df = location_df[
            location_df["year_month"] == selected_month
        ]

        selected_product = st.selectbox(
            "Select Product",
            sorted(month_df["product"].unique()),
            key="batch_daily_product"
        )

        product_df = month_df[
            month_df["product"] == selected_product
        ].sort_values("date")

        if product_df.empty:
            st.warning("No daily data available.")
            st.stop()

        daily_burn_avg = product_df["liftings"].mean()

        st.markdown("### Inventory Inputs")

        col1, col2, col3 = st.columns(3)

        beginning_inventory = col1.number_input(
            "Beginning Inventory",
            0.0, 999999999.0, 1000000.0,
            key="batch_daily_begin"
        )

        safety_level = col2.number_input(
            "Safety Level",
            0.0, 999999999.0, 200000.0,
            key="batch_daily_safety"
        )

        max_capacity = col3.number_input(
            "Max Capacity",
            0.0, 999999999.0, 1200000.0,
            key="batch_daily_max"
        )

        lead_time_days = st.number_input(
            "Lead Time (Days)",
            0, 60, 5,
            key="batch_daily_lead"
        )

        inventory = beginning_inventory
        hit_date = None

        for _, row in product_df.iterrows():
            inventory -= row["liftings"]
            if inventory <= safety_level:
                hit_date = row["date"]
                break

        if hit_date:

            order_date = hit_date - timedelta(days=lead_time_days)
            batch_needed = max_capacity - inventory

            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            col1.metric("Avg Daily Burn", f"{daily_burn_avg:,.0f}")
            col2.metric("Safety Hit Date", hit_date.strftime("%Y-%m-%d"))
            col3.metric("Order By Date", order_date.strftime("%Y-%m-%d"))

            st.metric("Recommended Batch Size", f"{batch_needed:,.0f}")

        else:
            st.success("Inventory does not hit safety level this month.")

# ==========================================================
# ================ PRICE SENSITIVITY SIM TAB ===============
# ==========================================================
with price_sim_tab:

    st.subheader("Price Sensitivity Simulation")

    st.markdown(
        """
        Simulate how forecast demand reacts to price changes using **price elasticity of demand**.
        Adjust the base price and elasticity per product at a selected location, then explore
        how volume changes across a range of price scenarios.

        > **Elasticity formula:** `% Δ Demand = Elasticity × % Δ Price`
        > - Elasticity = **-1.0** → 1% price increase causes 1% demand drop (unit elastic)
        > - Elasticity closer to **0** → inelastic (demand barely reacts to price)
        > - Elasticity below **-1** → elastic (demand is very price-sensitive)
        """
    )

    st.markdown("---")

    # ---- Filters ----
    col_loc, col_month = st.columns(2)

    with col_loc:
        ps_location = st.selectbox(
            "Select Location",
            sorted(df["location"].unique()),
            key="ps_location"
        )

    with col_month:
        ps_month_options = sorted(
            df[df["location"] == ps_location]["year_month"].unique()
        )
        ps_month = st.selectbox(
            "Select Month",
            ps_month_options,
            key="ps_month"
        )

    ps_df = df[
        (df["location"] == ps_location) &
        (df["year_month"] == ps_month)
    ].copy()

    if ps_df.empty:
        st.warning("No data for the selected location and month.")
        st.stop()

    products = sorted(ps_df["product"].unique())

    st.markdown("### Price & Elasticity Inputs")
    st.caption(
        "Set a base price and price elasticity of demand for each product. "
        "These are used to simulate demand response to price changes."
    )

    # ---- Per-product parameter inputs ----
    product_params = {}

    for product in products:
        baseline_liftings = ps_df[ps_df["product"] == product]["liftings"].sum()

        with st.expander(f"⚙️ {product}  —  Baseline Liftings: {baseline_liftings:,.0f}", expanded=True):
            col1, col2, col3 = st.columns(3)

            base_price = col1.number_input(
                "Base Price ($/unit)",
                min_value=0.01,
                value=3.00,
                step=0.05,
                format="%.2f",
                key=f"ps_base_price_{product}"
            )

            elasticity = col2.number_input(
                "Price Elasticity",
                min_value=-10.0,
                max_value=0.0,
                value=-0.8,
                step=0.1,
                format="%.2f",
                key=f"ps_elasticity_{product}",
                help="Typical fuel elasticity is between -0.3 (inelastic) and -1.5 (elastic). Must be ≤ 0."
            )

            sim_price = col3.number_input(
                "Simulated Price ($/unit)",
                min_value=0.01,
                value=round(base_price * 1.10, 2),
                step=0.05,
                format="%.2f",
                key=f"ps_sim_price_{product}"
            )

            product_params[product] = {
                "baseline_liftings": baseline_liftings,
                "base_price": base_price,
                "elasticity": elasticity,
                "sim_price": sim_price
            }

    st.markdown("---")

    # ---- Run Simulation ----
    if st.button("▶ Run Price Sensitivity Simulation", key="ps_run", type="primary"):

        st.markdown("### Simulation Results")

        # ---- Single price-point results ----
        results = []

        for product, params in product_params.items():
            pct_price_change = (
                (params["sim_price"] - params["base_price"]) / params["base_price"]
            )
            pct_demand_change = params["elasticity"] * pct_price_change
            sim_liftings = params["baseline_liftings"] * (1 + pct_demand_change)
            delta_liftings = sim_liftings - params["baseline_liftings"]

            baseline_revenue = params["baseline_liftings"] * params["base_price"]
            sim_revenue = sim_liftings * params["sim_price"]
            delta_revenue = sim_revenue - baseline_revenue

            results.append({
                "Product": product,
                "Base Price": params["base_price"],
                "Sim Price": params["sim_price"],
                "Price Δ%": f"{pct_price_change * 100:+.1f}%",
                "Elasticity": params["elasticity"],
                "Demand Δ%": f"{pct_demand_change * 100:+.1f}%",
                "Baseline Liftings": params["baseline_liftings"],
                "Simulated Liftings": sim_liftings,
                "Δ Liftings": delta_liftings,
                "Baseline Revenue": baseline_revenue,
                "Simulated Revenue": sim_revenue,
                "Δ Revenue": delta_revenue,
            })

        results_df = pd.DataFrame(results)

        # ---- Summary metrics ----
        total_baseline_liftings = results_df["Baseline Liftings"].sum()
        total_sim_liftings = results_df["Simulated Liftings"].sum()
        total_baseline_rev = results_df["Baseline Revenue"].sum()
        total_sim_rev = results_df["Simulated Revenue"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Baseline Liftings",
            f"{total_baseline_liftings:,.0f}"
        )
        m2.metric(
            "Simulated Liftings",
            f"{total_sim_liftings:,.0f}",
            delta=f"{total_sim_liftings - total_baseline_liftings:+,.0f}"
        )
        m3.metric(
            "Baseline Revenue",
            f"${total_baseline_rev:,.0f}"
        )
        m4.metric(
            "Simulated Revenue",
            f"${total_sim_rev:,.0f}",
            delta=f"${total_sim_rev - total_baseline_rev:+,.0f}"
        )

        st.markdown("#### Product-Level Breakdown")

        display_df = results_df[[
            "Product", "Base Price", "Sim Price", "Price Δ%", "Elasticity",
            "Demand Δ%", "Baseline Liftings", "Simulated Liftings", "Δ Liftings",
            "Baseline Revenue", "Simulated Revenue", "Δ Revenue"
        ]].copy()

        # Format numeric columns for display
        display_df["Baseline Liftings"] = display_df["Baseline Liftings"].map("{:,.0f}".format)
        display_df["Simulated Liftings"] = display_df["Simulated Liftings"].map("{:,.0f}".format)
        display_df["Δ Liftings"] = display_df["Δ Liftings"].map("{:+,.0f}".format)
        display_df["Baseline Revenue"] = display_df["Baseline Revenue"].map("${:,.0f}".format)
        display_df["Simulated Revenue"] = display_df["Simulated Revenue"].map("${:,.0f}".format)
        display_df["Δ Revenue"] = display_df["Δ Revenue"].map("${:+,.0f}".format)
        display_df["Base Price"] = display_df["Base Price"].map("${:.2f}".format)
        display_df["Sim Price"] = display_df["Sim Price"].map("${:.2f}".format)

        st.dataframe(display_df, use_container_width=True)

        # ---- Price sweep: demand curve across a range of prices ----
        st.markdown("---")
        st.markdown("#### Demand Curve — Price Sweep")
        st.caption(
            "Shows how simulated liftings change across a ±50% price range from the base price. "
            "One chart per product."
        )

        sweep_pct_range = np.linspace(-0.50, 0.50, 101)  # -50% to +50%

        for product, params in product_params.items():
            sweep_prices = params["base_price"] * (1 + sweep_pct_range)
            sweep_demand_changes = params["elasticity"] * sweep_pct_range
            sweep_liftings = params["baseline_liftings"] * (1 + sweep_demand_changes)
            sweep_revenue = sweep_liftings * sweep_prices

            sweep_df = pd.DataFrame({
                "Price ($/unit)": sweep_prices,
                "Simulated Liftings": sweep_liftings,
                "Simulated Revenue ($)": sweep_revenue,
            })

            # Mark the baseline and simulated price points
            sweep_df["Scenario"] = "Range"
            baseline_row = pd.DataFrame({
                "Price ($/unit)": [params["base_price"]],
                "Simulated Liftings": [params["baseline_liftings"]],
                "Simulated Revenue ($)": [
                    params["baseline_liftings"] * params["base_price"]
                ],
                "Scenario": ["Base Price"]
            })
            sim_liftings_point = params["baseline_liftings"] * (
                1 + params["elasticity"] * (
                    (params["sim_price"] - params["base_price"]) / params["base_price"]
                )
            )
            sim_row = pd.DataFrame({
                "Price ($/unit)": [params["sim_price"]],
                "Simulated Liftings": [sim_liftings_point],
                "Simulated Revenue ($)": [sim_liftings_point * params["sim_price"]],
                "Scenario": ["Simulated Price"]
            })

            st.markdown(f"**{product}**")

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.caption("Demand (Liftings) vs Price")
                st.line_chart(
                    sweep_df.set_index("Price ($/unit)")[["Simulated Liftings"]],
                    use_container_width=True
                )

            with chart_col2:
                st.caption("Revenue vs Price")
                st.line_chart(
                    sweep_df.set_index("Price ($/unit)")[["Simulated Revenue ($)"]],
                    use_container_width=True
                )

            # Revenue-maximizing price
            max_rev_idx = sweep_df["Simulated Revenue ($)"].idxmax()
            max_rev_price = sweep_df.loc[max_rev_idx, "Price ($/unit)"]
            max_rev_liftings = sweep_df.loc[max_rev_idx, "Simulated Liftings"]
            max_rev_value = sweep_df.loc[max_rev_idx, "Simulated Revenue ($)"]

            st.info(
                f"💡 **Revenue-maximizing price for {product}:** "
                f"${max_rev_price:.2f}/unit → "
                f"{max_rev_liftings:,.0f} liftings → "
                f"${max_rev_value:,.0f} revenue"
            )

            st.markdown("")

        # ---- Downloadable results ----
        st.markdown("---")
        csv_out = results_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Download Price Simulation Results CSV",
            data=csv_out,
            file_name=f"price_simulation_{ps_location}_{ps_month}.csv",
            mime="text/csv",
            key="ps_download"
        )


# ==========================================================
# ====================== TANK LEVELS TAB ===================
# ==========================================================
with tanks_tab:

    st.subheader("Tank Inventory Levels")
    st.caption("Enter current inventory for each product at the selected location. Lockouts reserve volume for a specific customer.")

    # ---- Session state init ----
    if "tank_levels" not in st.session_state:
        st.session_state["tank_levels"] = {}   # key: (location, product) -> float
    if "lockouts" not in st.session_state:
        st.session_state["lockouts"] = []       # list of dicts: {location, product, customer, amount}
    if "show_lockout_dialog" not in st.session_state:
        st.session_state["show_lockout_dialog"] = False

    # ---- Location selector ----
    tank_location = st.selectbox(
        "Select Location",
        sorted(df["location"].unique()),
        key="tank_location"
    )

    tank_products = sorted(df[df["location"] == tank_location]["product"].unique())
    tank_customers = sorted(df[df["location"] == tank_location]["customer"].unique())

    # ---- Max capacity input (shared for all tanks at location) ----
    tank_max_capacity = st.number_input(
        "Max Tank Capacity (per product)",
        min_value=1000.0,
        max_value=999_999_999.0,
        value=1_000_000.0,
        step=50_000.0,
        key="tank_max_capacity",
        help="Maximum volume each tank can hold. Used to calculate fill percentage."
    )

    st.markdown("---")
    st.markdown("### Enter Current Inventory Levels")

    # ---- Per-product inventory inputs ----
    col_inputs = st.columns(min(len(tank_products), 4))
    for i, product in enumerate(tank_products):
        key = (tank_location, product)
        current_val = st.session_state["tank_levels"].get(key, 0.0)
        with col_inputs[i % 4]:
            new_val = st.number_input(
                f"{product}",
                min_value=0.0,
                max_value=float(tank_max_capacity),
                value=current_val,
                step=10_000.0,
                key=f"tank_input_{tank_location}_{product}"
            )
            st.session_state["tank_levels"][key] = new_val

    st.markdown("---")

    # ---- Lockout dialog trigger ----
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔒 Lock Out Inventory", type="primary", key="open_lockout_btn"):
            st.session_state["show_lockout_dialog"] = True

    # ---- Lockout dialog (rendered inline as an expander-style form) ----
    if st.session_state["show_lockout_dialog"]:
        with st.container():
            st.markdown(
                """
                <div style="
                    background: #1e2a3a;
                    border: 1px solid #3a5068;
                    border-radius: 10px;
                    padding: 24px 28px;
                    margin: 16px 0;
                ">
                <h4 style="color:#e8f4fd; margin-bottom:4px;">🔒 Lock Out Inventory</h4>
                <p style="color:#7fa8c9; font-size:13px; margin-bottom:16px;">
                    Reserve a volume of product at this location for a specific customer.
                    Locked-out inventory will appear separately on the tank visual.
                </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            d_col1, d_col2 = st.columns(2)

            with d_col1:
                lockout_location = st.selectbox(
                    "Location",
                    sorted(df["location"].unique()),
                    index=sorted(df["location"].unique()).index(tank_location),
                    key="lockout_location"
                )
                lockout_product = st.selectbox(
                    "Product",
                    sorted(df[df["location"] == lockout_location]["product"].unique()),
                    key="lockout_product"
                )

            with d_col2:
                lockout_customers = sorted(df[df["location"] == lockout_location]["customer"].unique())
                lockout_customer = st.selectbox(
                    "Customer",
                    lockout_customers,
                    key="lockout_customer"
                )
                lockout_amount = st.number_input(
                    "Amount to Lock Out",
                    min_value=1.0,
                    max_value=float(tank_max_capacity),
                    value=50_000.0,
                    step=5_000.0,
                    key="lockout_amount"
                )

            btn_col1, btn_col2, _ = st.columns([1, 1, 4])

            with btn_col1:
                if st.button("✅ Submit", type="primary", key="lockout_submit"):
                    st.session_state["lockouts"].append({
                        "location": lockout_location,
                        "product": lockout_product,
                        "customer": lockout_customer,
                        "amount": lockout_amount
                    })
                    st.session_state["show_lockout_dialog"] = False
                    st.success(f"Locked out {lockout_amount:,.0f} of {lockout_product} for {lockout_customer} at {lockout_location}.")
                    st.rerun()

            with btn_col2:
                if st.button("Cancel", key="lockout_cancel"):
                    st.session_state["show_lockout_dialog"] = False
                    st.rerun()

    # ---- Build tank SVGs ----
    st.markdown("---")
    st.markdown("### Tank Visualization")

    # Filter lockouts for current location
    location_lockouts = [
        lo for lo in st.session_state["lockouts"]
        if lo["location"] == tank_location
    ]

    def build_tank_svg(product, current_volume, max_capacity, lockouts_for_product):
        """
        Build an SVG vertical cylindrical tank showing:
        - Available inventory (blue gradient)
        - Locked-out inventory segments (amber, stacked above available)
        - Empty space (dark)
        - Labels and percentage
        """
        W, H = 160, 320
        tank_x, tank_y = 30, 20
        tank_w, tank_h = 100, 260
        ellipse_ry = 14  # ellipse height for top/bottom caps

        total_lockout = sum(lo["amount"] for lo in lockouts_for_product)
        available = max(0.0, current_volume - total_lockout)
        pct_available = min(available / max_capacity, 1.0) if max_capacity > 0 else 0
        pct_lockout = min(total_lockout / max_capacity, 1.0) if max_capacity > 0 else 0
        pct_total = min(pct_available + pct_lockout, 1.0)

        # Pixel heights within the tank body
        fill_h_available = pct_available * tank_h
        fill_h_lockout = pct_lockout * tank_h
        fill_h_total = fill_h_available + fill_h_lockout

        # Y positions (tank fills from bottom)
        bottom_y = tank_y + tank_h
        available_top_y = bottom_y - fill_h_available
        lockout_top_y = available_top_y - fill_h_lockout

        pct_display = int(pct_total * 100)

        # Color choices
        if pct_total > 0.6:
            fluid_color1, fluid_color2 = "#1a6fa8", "#2596d4"
        elif pct_total > 0.3:
            fluid_color1, fluid_color2 = "#1a6fa8", "#2596d4"
        else:
            fluid_color1, fluid_color2 = "#a83232", "#d44040"

        lockout_color1, lockout_color2 = "#b87c1a", "#e8a825"

        svg_parts = [f'''<svg width="{W}" height="{H+60}" xmlns="http://www.w3.org/2000/svg" font-family="monospace">''']

        # Defs: gradients
        svg_parts.append(f'''
  <defs>
    <linearGradient id="grad_avail_{product}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{fluid_color1}" stop-opacity="0.85"/>
      <stop offset="50%" stop-color="{fluid_color2}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{fluid_color1}" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="grad_lock_{product}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{lockout_color1}" stop-opacity="0.85"/>
      <stop offset="50%" stop-color="{lockout_color2}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{lockout_color1}" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="tank_body_{product}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#0d1f30" stop-opacity="1"/>
      <stop offset="40%" stop-color="#142840" stop-opacity="1"/>
      <stop offset="100%" stop-color="#0d1f30" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="clip_{product}">
      <rect x="{tank_x}" y="{tank_y}" width="{tank_w}" height="{tank_h}"/>
    </clipPath>
  </defs>''')

        # Tank body background (empty)
        svg_parts.append(f'''
  <rect x="{tank_x}" y="{tank_y}" width="{tank_w}" height="{tank_h}"
        fill="url(#tank_body_{product})" rx="0"/>'''  )

        # Available fluid fill
        if fill_h_available > 0:
            svg_parts.append(f'''
  <rect x="{tank_x}" y="{available_top_y:.1f}" width="{tank_w}" height="{fill_h_available:.1f}"
        fill="url(#grad_avail_{product})" clip-path="url(#clip_{product})"/>'''  )

        # Lockout fluid fill (stacked above available)
        if fill_h_lockout > 0:
            svg_parts.append(f'''
  <rect x="{tank_x}" y="{lockout_top_y:.1f}" width="{tank_w}" height="{fill_h_lockout:.1f}"
        fill="url(#grad_lock_{product})" clip-path="url(#clip_{product})"/>'''  )

        # Fluid surface shimmer line (available)
        if fill_h_available > 2:
            svg_parts.append(f'''
  <ellipse cx="{tank_x + tank_w//2}" cy="{available_top_y:.1f}" rx="{tank_w//2}" ry="{ellipse_ry//2}"
           fill="{fluid_color2}" opacity="0.4"/>'''  )

        # Fluid surface shimmer line (lockout)
        if fill_h_lockout > 2:
            svg_parts.append(f'''
  <ellipse cx="{tank_x + tank_w//2}" cy="{lockout_top_y:.1f}" rx="{tank_w//2}" ry="{ellipse_ry//2}"
           fill="{lockout_color2}" opacity="0.5"/>'''  )

        # Tank border / shell
        svg_parts.append(f'''
  <rect x="{tank_x}" y="{tank_y}" width="{tank_w}" height="{tank_h}"
        fill="none" stroke="#3a6080" stroke-width="2" rx="2"/>'''  )

        # Top cap ellipse
        svg_parts.append(f'''
  <ellipse cx="{tank_x + tank_w//2}" cy="{tank_y}" rx="{tank_w//2}" ry="{ellipse_ry}"
           fill="#0d1f30" stroke="#3a6080" stroke-width="2"/>'''  )

        # Bottom cap ellipse
        svg_parts.append(f'''
  <ellipse cx="{tank_x + tank_w//2}" cy="{tank_y + tank_h}" rx="{tank_w//2}" ry="{ellipse_ry}"
           fill="#0a1825" stroke="#3a6080" stroke-width="2"/>'''  )

        # Tick marks (10%, 25%, 50%, 75%, 90%)
        for tick_pct in [0.1, 0.25, 0.5, 0.75, 0.9]:
            tick_y = bottom_y - tick_pct * tank_h
            svg_parts.append(f'''
  <line x1="{tank_x + tank_w - 10}" y1="{tick_y:.1f}" x2="{tank_x + tank_w}" y2="{tick_y:.1f}"
        stroke="#3a6080" stroke-width="1" opacity="0.7"/>
  <text x="{tank_x + tank_w + 4}" y="{tick_y + 4:.1f}" font-size="8" fill="#3a7090" opacity="0.8">{int(tick_pct*100)}%</text>'''  )

        # Percentage text in center
        svg_parts.append(f'''
  <text x="{tank_x + tank_w//2}" y="{tank_y + tank_h//2 + 6}" text-anchor="middle"
        font-size="22" font-weight="bold" fill="white" opacity="0.85">{pct_display}%</text>'''  )

        # Product label at top
        label_y = H + 20
        svg_parts.append(f'''
  <text x="{tank_x + tank_w//2}" y="{label_y}" text-anchor="middle"
        font-size="13" font-weight="bold" fill="#c8dff0">{product}</text>'''  )

        # Volume label
        svg_parts.append(f'''
  <text x="{tank_x + tank_w//2}" y="{label_y + 18}" text-anchor="middle"
        font-size="10" fill="#7fa8c9">{current_volume:,.0f} / {max_capacity:,.0f}</text>'''  )

        svg_parts.append("</svg>")
        return "".join(svg_parts)

    # ---- Render tanks in a row ----
    num_products = len(tank_products)
    tank_cols = st.columns(min(num_products, 5))

    for i, product in enumerate(tank_products):
        key = (tank_location, product)
        current_vol = st.session_state["tank_levels"].get(key, 0.0)
        prod_lockouts = [lo for lo in location_lockouts if lo["product"] == product]

        with tank_cols[i % 5]:
            svg = build_tank_svg(product, current_vol, tank_max_capacity, prod_lockouts)
            st.markdown(f'''<div style="display:flex;justify-content:center;">{svg}</div>''', unsafe_allow_html=True)

            # Show lockout badges below tank
            if prod_lockouts:
                for lo in prod_lockouts:
                    st.markdown(
                        f'''<div style="
                            background:#2a1f05;
                            border:1px solid #b87c1a;
                            border-radius:6px;
                            padding:6px 10px;
                            margin:4px 0;
                            font-size:12px;
                            color:#e8a825;
                        ">
                        🔒 <b>{lo["customer"]}</b><br/>
                        <span style="color:#c8901a;">{lo["amount"]:,.0f} units</span>
                        </div>''',
                        unsafe_allow_html=True
                    )

    # ---- Active lockouts summary table ----
    if location_lockouts:
        st.markdown("---")
        st.markdown("### 🔒 Active Lockouts — " + tank_location)

        lockout_df = pd.DataFrame(location_lockouts)
        lockout_df.columns = ["Location", "Product", "Customer", "Locked Amount"]
        lockout_df["Locked Amount"] = lockout_df["Locked Amount"].map("{:,.0f}".format)

        col_table, col_clear = st.columns([4, 1])
        with col_table:
            st.dataframe(lockout_df, use_container_width=True, hide_index=True)
        with col_clear:
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("🗑️ Clear All Lockouts", key="clear_lockouts"):
                st.session_state["lockouts"] = [
                    lo for lo in st.session_state["lockouts"]
                    if lo["location"] != tank_location
                ]
                st.rerun()


# ==========================================================
# GRAND TOTAL SECTION
# ==========================================================
st.markdown("---")
st.subheader("📈 Grand Totals (All Locations)")

grand_original = filtered_df["liftings"].sum()
grand_scaled = filtered_df["Scaled_Forecast"].sum()

col1, col2 = st.columns(2)

with col1:
    st.metric("Total Original", f"{grand_original:,.0f}")

with col2:
    st.metric("Total Scaled", f"{grand_scaled:,.0f}")

# ==========================================================
# DOWNLOAD BUTTON
# ==========================================================
st.markdown("---")
st.subheader("Export")

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered Forecast CSV",
    data=csv,
    file_name=f"forecast_{selected_month}.csv",
    mime="text/csv"
)
