import streamlit as st
import pandas as pd
import calendar
import numpy as np
from datetime import timedelta, date
from inventory_simulation import simulate_inventory_by_product
from auth import check_password, logout
from status_engine import evaluate_statuses, get_status, inactive_count
from theme import inject_theme, render_header, kpi_row, section_header, status_badge, build_tank_svg
from price_feed import get_live_prices, price_source_note

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="GAM! Dashboard",
    layout="wide",
    page_icon="🛢️"
)

# ==========================================================
# THEME
# ==========================================================
inject_theme()

# ==========================================================
# AUTH GATE
# ==========================================================
if not check_password():
    st.stop()

# ---- Nav bar + sign-out ----
_username = st.session_state.get("username", "")
render_header(_username)

_sc1, _sc2, _sc3 = st.columns([8, 1, 1])
with _sc3:
    if st.button("Sign Out", key="signout"):
        logout()

# ==========================================================
# SESSION STATE DEFAULTS
# ==========================================================
if "tank_levels"          not in st.session_state:
    st.session_state["tank_levels"]          = {}
if "lockouts"             not in st.session_state:
    st.session_state["lockouts"]             = []
if "show_lockout_dialog"  not in st.session_state:
    st.session_state["show_lockout_dialog"]  = False
if "auto_cutoff_enabled"  not in st.session_state:
    st.session_state["auto_cutoff_enabled"]  = False

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

    df["date"]       = pd.to_datetime(df["date"], errors="coerce")
    df["liftings"]   = pd.to_numeric(df["liftings"], errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    return df


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

    df["date"]       = pd.to_datetime(df["date"], errors="coerce")
    df["liftings"]   = pd.to_numeric(df["liftings"], errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    return df


df       = load_data()
daily_df = load_daily_data()

# Shared state reads used across multiple tabs
_tank_levels       = st.session_state["tank_levels"]
_lockouts          = st.session_state["lockouts"]
_hard_cutoff       = st.session_state["auto_cutoff_enabled"]
_all_statuses      = evaluate_statuses(df, _tank_levels, _lockouts,
                                       hard_cutoff=_hard_cutoff)
_n_inactive        = inactive_count(_all_statuses)

# ==========================================================
# MAIN TOP TABS  — Dashboard is index 0 so it loads first
# ==========================================================
(dashboard_tab, forecast_tab, alloc_tab,
 inventory_tab, batch_tab, price_sim_tab, tanks_tab) = st.tabs([
    "🏠 Dashboard",
    "📊 Forecast",
    "📦 Allocations",
    "🏭 Inventory Simulation",
    "🚚 Batch Planner",
    "💹 Price Sensitivity",
    "🛢️ Tank Levels",
])

# ==========================================================
# ======================== DASHBOARD TAB ===================
# ==========================================================
with dashboard_tab:

    section_header("Operations Overview",
                   "Live snapshot across all locations and products")

    _n_lockouts_db   = len(_lockouts)
    _total_liftings  = df["liftings"].sum()
    _loc_count       = df["location"].nunique()
    _prod_count      = df["product"].nunique()
    _cust_count      = df["customer"].nunique()

    # ── Top KPIs ──────────────────────────────────────────────────────────────
    kpi_row([
        {"label": "Locations",            "value": str(_loc_count),
         "icon": "📍", "accent": "#4A9EFF"},
        {"label": "Products",             "value": str(_prod_count),
         "icon": "🛢️", "accent": "#06B6D4"},
        {"label": "Customers",            "value": str(_cust_count),
         "icon": "👥", "accent": "#8B5CF6"},
        {"label": "Active Lockouts",      "value": str(_n_lockouts_db),
         "icon": "🔒",
         "accent": "#F59E0B" if _n_lockouts_db > 0 else "#10B981"},
        {"label": "Inactive Allocations", "value": str(_n_inactive),
         "icon": "🚫",
         "accent": "#EF4444" if _n_inactive > 0 else "#10B981"},
    ])

    st.markdown("---")

    # ── Tank status bars per location ─────────────────────────────────────────
    section_header("Tank Status by Location",
                   "Fill levels from the 🛢️ Tank Levels tab · Blue = available · Amber = locked")

    _all_locations = sorted(df["location"].unique())
    _db_cols       = st.columns(min(len(_all_locations), 3))
    _cap           = st.session_state.get("tank_max_capacity", 1_000_000.0)

    for _ci, _loc in enumerate(_all_locations):
        _loc_products = sorted(df[df["location"] == _loc]["product"].unique())
        with _db_cols[_ci % 3]:
            _rows_html = ""
            for _prod in _loc_products:
                _vol    = _tank_levels.get((_loc, _prod), 0.0)
                _pct    = min(_vol / _cap, 1.0) * 100 if _cap > 0 else 0
                _lo_amt = sum(lo["amount"] for lo in _lockouts
                              if lo["location"] == _loc and lo["product"] == _prod)
                _lo_pct = min(_lo_amt / _cap, 1.0) * 100 if _cap > 0 else 0
                _avail_pct = max(_pct - _lo_pct, 0)
                _bar_c  = "#2580D4" if _pct > 60 else ("#F59E0B" if _pct > 30 else "#EF4444")
                _lo_tag = (f'<div style="font-size:10px;color:#F59E0B;margin-top:2px;">'
                           f'🔒 {_lo_amt:,.0f} locked</div>') if _lo_amt > 0 else ""
                _rows_html += (
                    f'<div style="margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
                    f'<span style="font-size:12px;color:#94A3B8;">{_prod}</span>'
                    f'<span style="font-size:12px;font-family:monospace;color:#E2E8F0;">{_pct:.0f}%</span>'
                    f'</div>'
                    f'<div style="background:#0A0F1E;border-radius:4px;height:8px;overflow:hidden;">'
                    f'<div style="display:flex;height:100%;">'
                    f'<div style="width:{_avail_pct:.1f}%;background:{_bar_c};border-radius:4px 0 0 4px;"></div>'
                    f'<div style="width:{_lo_pct:.1f}%;background:#F59E0B;"></div>'
                    f'</div></div>{_lo_tag}</div>'
                )
            st.markdown(
                f'<div style="background:#111827;border:1px solid #1E2D45;'
                f'border-radius:10px;padding:16px 18px;margin-bottom:12px;">'
                f'<div style="font-size:13px;font-weight:600;color:#E2E8F0;'
                f'margin-bottom:12px;">📍 {_loc}</div>'
                f'{_rows_html}</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Inactive allocations ───────────────────────────────────────────────────
    if _n_inactive > 0:
        section_header("Inactive Allocations",
                       "Customers with no available inventory right now")
        _ia_rows = [
            {"Location": loc, "Product": prod,
             "Customer": cust, "Reason": info.get("reason") or "Fully locked"}
            for (loc, prod, cust), info in _all_statuses.items()
            if info["status"] == "inactive"
        ]
        st.dataframe(pd.DataFrame(_ia_rows), use_container_width=True, hide_index=True)
    else:
        st.success("✅ All allocations are currently active across all locations.")

    # ── Active lockouts ────────────────────────────────────────────────────────
    if _lockouts:
        st.markdown("---")
        section_header("Active Lockouts", "All inventory reservations in effect")
        _lo_disp = pd.DataFrame(_lockouts).copy()
        _lo_disp.columns = ["Location", "Product", "Customer", "Locked Amount"]
        _lo_disp["Locked Amount"] = _lo_disp["Locked Amount"].map("{:,.0f}".format)
        st.dataframe(_lo_disp, use_container_width=True, hide_index=True)

# ==========================================================
# ======================= FORECAST TAB =====================
# ==========================================================
with forecast_tab:

    section_header("Forecast Viewer", "Monthly liftings by customer and product")

    month_options = sorted(df["year_month"].dropna().unique())

    selected_month = st.selectbox("Select Month", month_options, key="forecast_month")

    selected_customer = st.multiselect(
        "Select Customer", sorted(df["customer"].unique()),
        default=sorted(df["customer"].unique()), key="forecast_customer"
    )

    selected_product = st.multiselect(
        "Select Product", sorted(df["product"].unique()),
        default=sorted(df["product"].unique()), key="forecast_product"
    )

    scale_percent = st.number_input(
        "Scale Forecast (%)", min_value=-100, max_value=500,
        value=0, step=5, key="forecast_scale"
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
        filtered_df["Scaled_Forecast"] = filtered_df["liftings"] * scale_factor

        locations     = sorted(filtered_df["location"].unique())
        location_tabs = st.tabs(locations)

        for i, location in enumerate(locations):
            with location_tabs[i]:
                st.markdown(f"### {location}")
                location_df = filtered_df[filtered_df["location"] == location]
                st.dataframe(location_df, use_container_width=True)

                _orig  = location_df["liftings"].sum()
                _scld  = location_df["Scaled_Forecast"].sum()
                _ddiff = _scld - _orig
                kpi_row([
                    {"label": "Original Total", "value": f"{_orig:,.0f}",
                     "icon": "📊", "accent": "#4A9EFF"},
                    {"label": "Scaled Total", "value": f"{_scld:,.0f}",
                     "icon": "📈", "delta": f"{_ddiff:+,.0f}",
                     "delta_positive": _ddiff >= 0,
                     "accent": "#10B981" if _ddiff >= 0 else "#EF4444"},
                ])

# ==========================================================
# ====================== ALLOCATIONS TAB ===================
# ==========================================================
with alloc_tab:

    section_header("Allocation Breakdown",
                   "Customer and product allocations with live inventory status")

    if _n_inactive > 0:
        _mode_label = "Hard Cut" if _hard_cutoff else "Standard"
        st.error(
            f"⚠️  **{_n_inactive} allocation(s) are currently INACTIVE** "
            f"[{_mode_label} mode] — "
            "Update tank levels or lockouts in the 🛢️ Tank Levels tab."
        )

    month_options    = sorted(df["year_month"].dropna().unique())
    selected_month   = st.selectbox("Select Month", month_options, key="alloc_month")
    month_df         = df[df["year_month"] == selected_month]
    selected_location = st.selectbox(
        "Select Location", sorted(month_df["location"].unique()), key="alloc_location"
    )
    location_df = month_df[month_df["location"] == selected_location]

    # ── Overview table ─────────────────────────────────────────────────────────
    st.markdown("### All Allocations — " + selected_location)
    st.caption(
        "Allocations marked INACTIVE have no available inventory. "
        "Cutoff policy is set in the 🛢️ Tank Levels tab."
    )

    overview_rows = []
    for _, row in location_df.iterrows():
        s = get_status(_all_statuses, row["location"], row["product"], row["customer"])
        overview_rows.append({
            "Customer": row["customer"],
            "Product":  row["product"],
            "Liftings": f"{row['liftings']:,.0f}",
            "Status":   s["status"].upper(),
            "Reason":   s["reason"] or "—",
        })

    if overview_rows:
        ov_df = pd.DataFrame(overview_rows)

        def _style_status(val):
            if val == "INACTIVE":
                return "background-color:#3d0000;color:#ff4444;font-weight:bold;"
            return "color:#22c55e;font-weight:bold;"

        st.dataframe(
            ov_df.style.map(_style_status, subset=["Status"]),
            use_container_width=True, hide_index=True
        )

    st.markdown("---")
    st.markdown("### Drill-Down")

    selected_customer = st.selectbox(
        "Select Customer", sorted(location_df["customer"].unique()), key="alloc_customer"
    )
    customer_df  = location_df[location_df["customer"] == selected_customer]
    selected_product = st.selectbox(
        "Select Product", sorted(customer_df["product"].unique()), key="alloc_product"
    )
    allocation_row = customer_df[customer_df["product"] == selected_product]

    if allocation_row.empty:
        st.warning("No allocation found.")
    else:
        alloc_status = get_status(
            _all_statuses, selected_location, selected_product, selected_customer
        )

        if alloc_status["status"] == "inactive":
            st.markdown(
                f'<div style="display:inline-block;background:#3d0000;'
                f'border:1.5px solid #ff4444;border-radius:8px;'
                f'padding:10px 20px;margin-bottom:12px;">'
                f'<span style="color:#ff4444;font-size:18px;font-weight:bold;">🚫 INACTIVE</span><br/>'
                f'<span style="color:#ffaaaa;font-size:13px;">{alloc_status["reason"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="display:inline-block;background:#003d1a;'
                'border:1.5px solid #22c55e;border-radius:8px;'
                'padding:10px 20px;margin-bottom:12px;">'
                '<span style="color:#22c55e;font-size:18px;font-weight:bold;">✅ ACTIVE</span>'
                '</div>',
                unsafe_allow_html=True
            )

        total        = allocation_row["liftings"].sum()
        month_dt     = pd.to_datetime(selected_month)
        days_in_month = calendar.monthrange(month_dt.year, month_dt.month)[1]
        weekly       = total / 4
        daily        = total / days_in_month

        kpi_row([
            {"label": "Monthly Total", "value": f"{total:,.0f}",   "icon": "📅", "accent": "#4A9EFF"},
            {"label": "Weekly (÷4)",   "value": f"{weekly:,.0f}",  "icon": "📆", "accent": "#06B6D4"},
            {"label": "Daily Avg",     "value": f"{daily:,.0f}",   "icon": "📋", "accent": "#8B5CF6"},
        ])

        st.markdown("---")
        st.dataframe(allocation_row, use_container_width=True)

# ==========================================================
# ================= INVENTORY SIMULATION TAB ===============
# ==========================================================
with inventory_tab:

    st.subheader("Inventory Setup")

    selected_location = st.selectbox(
        "Select Location", sorted(df["location"].unique()), key="inv_location"
    )
    location_df = df[df["location"] == selected_location]
    products    = sorted(location_df["product"].unique())

    starting_inventory = {}
    safety_levels      = {}

    for product in products:
        col1, col2 = st.columns(2)
        with col1:
            starting_inventory[product] = st.number_input(
                f"{product} Starting Inventory",
                min_value=0.0, value=500000.0, step=10000.0,
                key=f"inv_start_{selected_location}_{product}"
            )
        with col2:
            safety_levels[product] = st.number_input(
                f"{product} Safety Level",
                min_value=0.0, value=100000.0, step=10000.0,
                key=f"inv_safety_{selected_location}_{product}"
            )

    if st.button("Run Inventory Simulation", key="inv_run"):
        sim_df = simulate_inventory_by_product(
            forecast_df=location_df,
            starting_inventory=starting_inventory,
            safety_levels=safety_levels,
        )
        st.subheader("Simulation Results")
        st.dataframe(sim_df, use_container_width=True)

# ==========================================================
# ====================== BATCH PLANNER TAB =================
# ==========================================================
with batch_tab:

    section_header("Batch Scheduling Planner",
                   "Determine optimal order dates and batch sizes")

    monthly_planner, daily_planner = st.tabs(["📅 Monthly Forecast", "📆 Daily Forecast"])

    with monthly_planner:

        selected_location = st.selectbox(
            "Select Location", sorted(df["location"].unique()), key="batch_monthly_location"
        )
        location_df  = df[df["location"] == selected_location]
        month_options = sorted(location_df["year_month"].unique())
        selected_month = st.selectbox("Select Month", month_options, key="batch_monthly_month")
        month_df = location_df[location_df["year_month"] == selected_month]

        selected_product = st.selectbox(
            "Select Product", sorted(month_df["product"].unique()), key="batch_monthly_product"
        )
        product_df      = month_df[month_df["product"] == selected_product]
        monthly_liftings = product_df["liftings"].sum()
        month_dt        = pd.to_datetime(selected_month)
        days_in_month   = calendar.monthrange(month_dt.year, month_dt.month)[1]
        daily_burn      = monthly_liftings / days_in_month

        st.markdown("### Inventory Inputs")
        col1, col2, col3 = st.columns(3)
        beginning_inventory = col1.number_input(
            "Beginning Inventory", 0.0, 999999999.0, 1000000.0, key="batch_monthly_begin"
        )
        safety_level = col2.number_input(
            "Safety Level", 0.0, 999999999.0, 200000.0, key="batch_monthly_safety"
        )
        max_capacity = col3.number_input(
            "Max Capacity", 0.0, 999999999.0, 1200000.0, key="batch_monthly_max"
        )
        lead_time_days = st.number_input("Lead Time (Days)", 0, 60, 5, key="batch_monthly_lead")

        if daily_burn > 0:
            usable_inventory  = beginning_inventory - safety_level
            days_until_safety = usable_inventory / daily_burn
            safety_hit_date   = month_dt + timedelta(days=days_until_safety)
            order_date        = safety_hit_date - timedelta(days=lead_time_days)
            batch_needed      = max_capacity - safety_level

            st.markdown("---")
            kpi_row([
                {"label": "Daily Burn",        "value": f"{daily_burn:,.0f}",
                 "icon": "🔥", "accent": "#F59E0B"},
                {"label": "Safety Hit Date",   "value": safety_hit_date.strftime("%Y-%m-%d"),
                 "icon": "⚠️", "accent": "#EF4444"},
                {"label": "Order By Date",     "value": order_date.strftime("%Y-%m-%d"),
                 "icon": "📦", "accent": "#4A9EFF"},
                {"label": "Recommended Batch", "value": f"{batch_needed:,.0f}",
                 "icon": "🚚", "accent": "#10B981"},
            ])

    with daily_planner:

        selected_location = st.selectbox(
            "Select Location", sorted(daily_df["location"].unique()), key="batch_daily_location"
        )
        location_df  = daily_df[daily_df["location"] == selected_location]
        month_options = sorted(location_df["year_month"].unique())
        selected_month = st.selectbox("Select Month", month_options, key="batch_daily_month")
        month_df = location_df[location_df["year_month"] == selected_month]

        selected_product = st.selectbox(
            "Select Product", sorted(month_df["product"].unique()), key="batch_daily_product"
        )
        product_df = month_df[month_df["product"] == selected_product].sort_values("date")

        if product_df.empty:
            st.warning("No daily data available.")
            st.stop()

        daily_burn_avg = product_df["liftings"].mean()

        st.markdown("### Inventory Inputs")
        col1, col2, col3 = st.columns(3)
        beginning_inventory = col1.number_input(
            "Beginning Inventory", 0.0, 999999999.0, 1000000.0, key="batch_daily_begin"
        )
        safety_level = col2.number_input(
            "Safety Level", 0.0, 999999999.0, 200000.0, key="batch_daily_safety"
        )
        max_capacity = col3.number_input(
            "Max Capacity", 0.0, 999999999.0, 1200000.0, key="batch_daily_max"
        )
        lead_time_days = st.number_input("Lead Time (Days)", 0, 60, 5, key="batch_daily_lead")

        inventory = beginning_inventory
        hit_date  = None
        for _, row in product_df.iterrows():
            inventory -= row["liftings"]
            if inventory <= safety_level:
                hit_date = row["date"]
                break

        if hit_date:
            order_date   = hit_date - timedelta(days=lead_time_days)
            batch_needed = max_capacity - inventory

            st.markdown("---")
            kpi_row([
                {"label": "Avg Daily Burn",    "value": f"{daily_burn_avg:,.0f}",
                 "icon": "🔥", "accent": "#F59E0B"},
                {"label": "Safety Hit Date",   "value": hit_date.strftime("%Y-%m-%d"),
                 "icon": "⚠️", "accent": "#EF4444"},
                {"label": "Order By Date",     "value": order_date.strftime("%Y-%m-%d"),
                 "icon": "📦", "accent": "#4A9EFF"},
                {"label": "Recommended Batch", "value": f"{batch_needed:,.0f}",
                 "icon": "🚚", "accent": "#10B981"},
            ])
        else:
            st.success("Inventory does not hit safety level this month.")

# ==========================================================
# ================ PRICE SENSITIVITY SIM TAB ===============
# ==========================================================
with price_sim_tab:

    section_header("Price Sensitivity Simulation",
                   "Model demand response to price changes using elasticity")

    st.markdown(
        """
        Simulate how forecast demand reacts to price changes using **price elasticity of demand**.
        Base prices are pulled from live market data (EIA weekly retail) and used as your
        starting point. Adjust elasticity per product and explore how volume and revenue
        change across a range of scenarios.

        > **Elasticity formula:** `% Δ Demand = Elasticity × % Δ Price`
        > - **-1.0** → unit elastic (1% price rise = 1% demand drop)
        > - **closer to 0** → inelastic (demand barely reacts)
        > - **below -1** → elastic (demand is very price-sensitive)
        """
    )

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────────────
    col_loc, col_month = st.columns(2)
    with col_loc:
        ps_location = st.selectbox(
            "Select Location", sorted(df["location"].unique()), key="ps_location"
        )
    with col_month:
        ps_month_options = sorted(
            df[df["location"] == ps_location]["year_month"].unique()
        )
        ps_month = st.selectbox("Select Month", ps_month_options, key="ps_month")

    ps_df = df[
        (df["location"] == ps_location) &
        (df["year_month"] == ps_month)
    ].copy()

    if ps_df.empty:
        st.warning("No data for the selected location and month.")
        st.stop()

    products = sorted(ps_df["product"].unique())

    # ── Live price fetch ──────────────────────────────────────────────────────
    section_header("Today's Market Prices", "Pulled from EIA weekly retail data · Used as baseline")

    with st.spinner("Fetching current fuel prices…"):
        live_prices = get_live_prices(tuple(products))

    # Show a compact price strip
    _price_cols = st.columns(min(len(products), 5))
    for _pi, _prod in enumerate(products):
        _pr = live_prices.get(_prod)
        if _pr:
            with _price_cols[_pi % 5]:
                st.markdown(
                    f'<div style="background:#111827;border:1px solid #1E2D45;'
                    f'border-radius:8px;padding:12px 14px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-size:11px;font-weight:600;color:#94A3B8;'
                    f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">'
                    f'{_prod}</div>'
                    f'<div style="font-size:22px;font-weight:700;color:#E2E8F0;'
                    f'font-family:monospace;">${_pr.price:.3f}</div>'
                    f'<div style="font-size:10px;color:#475569;margin-top:4px;">'
                    f'{_pr.unit}</div>'
                    f'{_pr.badge_html()}'
                    f'<div style="font-size:10px;color:#334155;margin-top:6px;">'
                    f'{"As of " + _pr.as_of if _pr.as_of else ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # Source attribution line
    _sample_pr = next(iter(live_prices.values()), None)
    if _sample_pr:
        if _sample_pr.is_live:
            st.caption(
                f"📡 Prices from: {_sample_pr.source}. "
                "To use OPIS rack prices, add your API key to secrets.toml under [opis]. "
                "To use EIA with higher rate limits, add a free key under [eia]."
            )
        else:
            st.caption(
                f"⚠️ Using static fallback prices ({_sample_pr.source}). "
                "Add a free EIA API key (eia.gov/opendata) under [eia] in secrets.toml "
                "for live weekly data, or add OPIS credentials under [opis] for real-time rack prices."
            )

    st.markdown("---")

    # ── Per-product parameter inputs ──────────────────────────────────────────
    st.markdown("### Price & Elasticity Inputs")
    st.caption(
        "Base price is pre-filled from today's market data. "
        "Adjust elasticity and the simulated price to model demand response."
    )

    product_params = {}

    for product in products:
        baseline_liftings = ps_df[ps_df["product"] == product]["liftings"].sum()
        live_pr           = live_prices.get(product)
        live_price_val    = live_pr.price if live_pr else 3.00

        with st.expander(
            f"⚙️ {product}  —  Baseline Liftings: {baseline_liftings:,.0f}"
            f"  —  Market Price: ${live_price_val:.3f}",
            expanded=True
        ):
            col1, col2, col3 = st.columns(3)

            base_price = col1.number_input(
                "Base Price ($/unit)",
                min_value=0.01,
                value=float(round(live_price_val, 2)),
                step=0.05,
                format="%.2f",
                key=f"ps_base_price_{product}",
                help="Pre-filled from EIA/OPIS live data. Adjust if needed."
            )

            elasticity = col2.number_input(
                "Price Elasticity",
                min_value=-10.0, max_value=0.0,
                value=-0.8, step=0.1, format="%.2f",
                key=f"ps_elasticity_{product}",
                help="Typical fuel: -0.3 (inelastic) to -1.5 (elastic). Must be ≤ 0."
            )

            sim_price = col3.number_input(
                "Simulated Price ($/unit)",
                min_value=0.01,
                value=round(base_price * 1.10, 2),
                step=0.05, format="%.2f",
                key=f"ps_sim_price_{product}"
            )

            # Show source note under the base price input
            if live_pr:
                st.caption(price_source_note(live_pr))

            product_params[product] = {
                "baseline_liftings": baseline_liftings,
                "base_price":        base_price,
                "elasticity":        elasticity,
                "sim_price":         sim_price,
            }

    st.markdown("---")

    # ── Run simulation ─────────────────────────────────────────────────────────
    if st.button("▶ Run Price Sensitivity Simulation", key="ps_run", type="primary"):

        st.markdown("### Simulation Results")
        results = []

        for product, params in product_params.items():
            pct_price_change  = (params["sim_price"] - params["base_price"]) / params["base_price"]
            pct_demand_change = params["elasticity"] * pct_price_change
            sim_liftings      = params["baseline_liftings"] * (1 + pct_demand_change)
            delta_liftings    = sim_liftings - params["baseline_liftings"]
            baseline_revenue  = params["baseline_liftings"] * params["base_price"]
            sim_revenue       = sim_liftings * params["sim_price"]
            delta_revenue     = sim_revenue - baseline_revenue

            results.append({
                "Product":           product,
                "Base Price":        params["base_price"],
                "Sim Price":         params["sim_price"],
                "Price Δ%":          f"{pct_price_change * 100:+.1f}%",
                "Elasticity":        params["elasticity"],
                "Demand Δ%":         f"{pct_demand_change * 100:+.1f}%",
                "Baseline Liftings": params["baseline_liftings"],
                "Simulated Liftings":sim_liftings,
                "Δ Liftings":        delta_liftings,
                "Baseline Revenue":  baseline_revenue,
                "Simulated Revenue": sim_revenue,
                "Δ Revenue":         delta_revenue,
            })

        results_df             = pd.DataFrame(results)
        total_baseline_liftings = results_df["Baseline Liftings"].sum()
        total_sim_liftings      = results_df["Simulated Liftings"].sum()
        total_baseline_rev      = results_df["Baseline Revenue"].sum()
        total_sim_rev           = results_df["Simulated Revenue"].sum()
        _lift_delta             = total_sim_liftings - total_baseline_liftings
        _rev_delta              = total_sim_rev - total_baseline_rev

        kpi_row([
            {"label": "Baseline Liftings",  "value": f"{total_baseline_liftings:,.0f}",
             "icon": "📊", "accent": "#4A9EFF"},
            {"label": "Simulated Liftings", "value": f"{total_sim_liftings:,.0f}",
             "delta": f"{_lift_delta:+,.0f}", "delta_positive": _lift_delta >= 0,
             "icon": "📈", "accent": "#10B981" if _lift_delta >= 0 else "#EF4444"},
            {"label": "Baseline Revenue",   "value": f"${total_baseline_rev:,.0f}",
             "icon": "💰", "accent": "#8B5CF6"},
            {"label": "Simulated Revenue",  "value": f"${total_sim_rev:,.0f}",
             "delta": f"${_rev_delta:+,.0f}", "delta_positive": _rev_delta >= 0,
             "icon": "💹", "accent": "#10B981" if _rev_delta >= 0 else "#EF4444"},
        ])

        st.markdown("#### Product-Level Breakdown")
        display_df = results_df[[
            "Product", "Base Price", "Sim Price", "Price Δ%", "Elasticity",
            "Demand Δ%", "Baseline Liftings", "Simulated Liftings", "Δ Liftings",
            "Baseline Revenue", "Simulated Revenue", "Δ Revenue"
        ]].copy()

        display_df["Baseline Liftings"]  = display_df["Baseline Liftings"].map("{:,.0f}".format)
        display_df["Simulated Liftings"] = display_df["Simulated Liftings"].map("{:,.0f}".format)
        display_df["Δ Liftings"]         = display_df["Δ Liftings"].map("{:+,.0f}".format)
        display_df["Baseline Revenue"]   = display_df["Baseline Revenue"].map("${:,.0f}".format)
        display_df["Simulated Revenue"]  = display_df["Simulated Revenue"].map("${:,.0f}".format)
        display_df["Δ Revenue"]          = display_df["Δ Revenue"].map("${:+,.0f}".format)
        display_df["Base Price"]         = display_df["Base Price"].map("${:.2f}".format)
        display_df["Sim Price"]          = display_df["Sim Price"].map("${:.2f}".format)
        st.dataframe(display_df, use_container_width=True)

        # ── Price sweep charts ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### Demand Curve — Price Sweep")
        st.caption("Shows how liftings and revenue change across a ±50% price range.")

        sweep_pct_range = np.linspace(-0.50, 0.50, 101)

        for product, params in product_params.items():
            sweep_prices   = params["base_price"] * (1 + sweep_pct_range)
            sweep_liftings = params["baseline_liftings"] * (
                1 + params["elasticity"] * sweep_pct_range
            )
            sweep_revenue  = sweep_liftings * sweep_prices

            sweep_df = pd.DataFrame({
                "Price ($/unit)":       sweep_prices,
                "Simulated Liftings":   sweep_liftings,
                "Simulated Revenue ($)":sweep_revenue,
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

            max_rev_idx   = sweep_df["Simulated Revenue ($)"].idxmax()
            max_rev_price = sweep_df.loc[max_rev_idx, "Price ($/unit)"]
            max_rev_lift  = sweep_df.loc[max_rev_idx, "Simulated Liftings"]
            max_rev_val   = sweep_df.loc[max_rev_idx, "Simulated Revenue ($)"]
            st.info(
                f"💡 **Revenue-maximizing price for {product}:** "
                f"${max_rev_price:.2f}/unit → "
                f"{max_rev_lift:,.0f} liftings → "
                f"${max_rev_val:,.0f} revenue"
            )
            st.markdown("")

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

    section_header("Tank Inventory Levels",
                   "Live fill visualization with customer lockouts")
    st.caption("Enter current inventory for each product at the selected location. "
               "Lockouts reserve volume for a specific customer.")

    # ── Cutoff policy control ──────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#111827;border:1px solid #1E2D45;border-radius:10px;'
        'padding:16px 20px;margin-bottom:16px;">'
        '<div style="font-size:13px;font-weight:600;color:#E2E8F0;margin-bottom:4px;">'
        '⚙️ Allocation Cutoff Policy</div>'
        '<div style="font-size:12px;color:#94A3B8;">'
        'Controls what happens when a product\'s available inventory reaches zero.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    _co_left, _co_right = st.columns([1, 2])
    with _co_left:
        auto_cutoff = st.checkbox(
            "Auto-cut ALL allocations when inventory hits zero",
            value=st.session_state["auto_cutoff_enabled"],
            key="auto_cutoff_checkbox",
            help=(
                "ON  — Hard Cut: every customer for that product goes INACTIVE when "
                "inventory = 0, including those with lockouts. Full supply stop.\n\n"
                "OFF — Standard: only customers without a lockout go INACTIVE. "
                "Customers who hold a lockout stay ACTIVE."
            ),
        )
        st.session_state["auto_cutoff_enabled"] = auto_cutoff

    with _co_right:
        if auto_cutoff:
            st.markdown(
                '<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);'
                'border-radius:8px;padding:12px 16px;margin-top:4px;">'
                '<span style="color:#EF4444;font-weight:600;font-size:13px;">🔴 HARD CUT MODE</span><br/>'
                '<span style="color:#94A3B8;font-size:12px;">All allocations go INACTIVE when '
                'inventory = 0, regardless of lockouts. Use for a full supply stop.</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);'
                'border-radius:8px;padding:12px 16px;margin-top:4px;">'
                '<span style="color:#10B981;font-weight:600;font-size:13px;">🟢 STANDARD MODE</span><br/>'
                '<span style="color:#94A3B8;font-size:12px;">Only unprotected allocations go INACTIVE. '
                'Customers with a lockout remain ACTIVE.</span></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Location selector ──────────────────────────────────────────────────────
    tank_location = st.selectbox(
        "Select Location", sorted(df["location"].unique()), key="tank_location"
    )
    tank_products  = sorted(df[df["location"] == tank_location]["product"].unique())
    tank_customers = sorted(df[df["location"] == tank_location]["customer"].unique())

    # ── Max capacity ───────────────────────────────────────────────────────────
    tank_max_capacity = st.number_input(
        "Max Tank Capacity (per product)",
        min_value=1000.0, max_value=999_999_999.0,
        value=1_000_000.0, step=50_000.0,
        key="tank_max_capacity",
        help="Maximum volume each tank can hold. Used to calculate fill percentage."
    )

    st.markdown("---")
    st.markdown("### Enter Current Inventory Levels")

    col_inputs = st.columns(min(len(tank_products), 4))
    for i, product in enumerate(tank_products):
        key = (tank_location, product)
        current_val = st.session_state["tank_levels"].get(key, 0.0)
        with col_inputs[i % 4]:
            new_val = st.number_input(
                f"{product}",
                min_value=0.0, max_value=float(tank_max_capacity),
                value=current_val, step=10_000.0,
                key=f"tank_input_{tank_location}_{product}"
            )
            st.session_state["tank_levels"][key] = new_val

    st.markdown("---")

    # ── Lockout dialog trigger ─────────────────────────────────────────────────
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔒 Lock Out Inventory", type="primary", key="open_lockout_btn"):
            st.session_state["show_lockout_dialog"] = True

    if st.session_state["show_lockout_dialog"]:
        with st.container():
            st.markdown(
                '<div style="background:#1e2a3a;border:1px solid #3a5068;'
                'border-radius:10px;padding:24px 28px;margin:16px 0;">'
                '<h4 style="color:#e8f4fd;margin-bottom:4px;">🔒 Lock Out Inventory</h4>'
                '<p style="color:#7fa8c9;font-size:13px;margin-bottom:16px;">'
                'Reserve a volume of product at this location for a specific customer. '
                'Locked-out inventory will appear separately on the tank visual.</p></div>',
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
                lockout_customers = sorted(
                    df[df["location"] == lockout_location]["customer"].unique()
                )
                lockout_customer = st.selectbox(
                    "Customer", lockout_customers, key="lockout_customer"
                )
                lockout_amount = st.number_input(
                    "Amount to Lock Out",
                    min_value=1.0, max_value=float(tank_max_capacity),
                    value=50_000.0, step=5_000.0, key="lockout_amount"
                )

            btn_col1, btn_col2, _ = st.columns([1, 1, 4])
            with btn_col1:
                if st.button("✅ Submit", type="primary", key="lockout_submit"):
                    st.session_state["lockouts"].append({
                        "location": lockout_location,
                        "product":  lockout_product,
                        "customer": lockout_customer,
                        "amount":   lockout_amount,
                    })
                    st.session_state["show_lockout_dialog"] = False
                    st.success(
                        f"Locked out {lockout_amount:,.0f} of {lockout_product} "
                        f"for {lockout_customer} at {lockout_location}."
                    )
                    st.rerun()
            with btn_col2:
                if st.button("Cancel", key="lockout_cancel"):
                    st.session_state["show_lockout_dialog"] = False
                    st.rerun()

    # ── Tank visualization ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Tank Visualization")

    location_lockouts = [
        lo for lo in st.session_state["lockouts"]
        if lo["location"] == tank_location
    ]

    tank_cols = st.columns(min(len(tank_products), 5))
    for i, product in enumerate(tank_products):
        key           = (tank_location, product)
        current_vol   = st.session_state["tank_levels"].get(key, 0.0)
        prod_lockouts = [lo for lo in location_lockouts if lo["product"] == product]

        with tank_cols[i % 5]:
            svg = build_tank_svg(product, current_vol, tank_max_capacity, prod_lockouts)
            st.markdown(
                f'<div style="display:flex;justify-content:center;">{svg}</div>',
                unsafe_allow_html=True
            )
            if prod_lockouts:
                for lo in prod_lockouts:
                    st.markdown(
                        f'<div style="background:rgba(245,158,11,0.08);'
                        f'border:1px solid rgba(245,158,11,0.3);border-radius:6px;'
                        f'padding:8px 12px;margin:4px 0;font-size:12px;">'
                        f'<span style="color:#F59E0B;font-weight:600;">🔒 {lo["customer"]}</span><br/>'
                        f'<span style="color:#94A3B8;font-family:\'JetBrains Mono\',monospace;'
                        f'font-size:11px;">{lo["amount"]:,.0f} units locked</span></div>',
                        unsafe_allow_html=True
                    )

    # ── Active lockouts summary table ──────────────────────────────────────────
    if location_lockouts:
        st.markdown("---")
        st.markdown("### 🔒 Active Lockouts — " + tank_location)
        lockout_df          = pd.DataFrame(location_lockouts)
        lockout_df.columns  = ["Location", "Product", "Customer", "Locked Amount"]
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
section_header("Grand Totals", "Across all locations for selected filters")

grand_original = filtered_df["liftings"].sum()
grand_scaled   = filtered_df["Scaled_Forecast"].sum()
grand_delta    = grand_scaled - grand_original

kpi_row([
    {"label": "Total Original", "value": f"{grand_original:,.0f}",
     "icon": "📊", "accent": "#4A9EFF"},
    {"label": "Total Scaled",   "value": f"{grand_scaled:,.0f}",
     "delta": f"{grand_delta:+,.0f}", "delta_positive": grand_delta >= 0,
     "icon": "📈", "accent": "#10B981" if grand_delta >= 0 else "#EF4444"},
])

# ==========================================================
# EXPORT
# ==========================================================
st.markdown("---")
section_header("Export", "Download filtered forecast data")

csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇ Download Filtered Forecast CSV",
    data=csv,
    file_name=f"forecast_{selected_month}.csv",
    mime="text/csv"
)
