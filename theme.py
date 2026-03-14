"""
theme.py
--------
Enterprise dark navy/slate UI system for the Liftings Forecast Dashboard.
Import and call inject_theme() once at the top of app.py, right after auth.

Also exports:
  - render_header(username)     — fixed top nav bar
  - kpi_card(label, value, delta, delta_positive)  — styled metric card
  - kpi_row(cards)              — render a list of kpi_card dicts in columns
  - section_header(title, subtitle)  — styled section divider
  - status_badge(status, reason)     — ACTIVE / INACTIVE badge HTML
  - styled_table_css()          — extra CSS for st.dataframe polish
"""

import streamlit as st


# ── Colour palette ─────────────────────────────────────────────────────────────
C = {
    "bg_base":       "#0A0F1E",   # deepest background
    "bg_surface":    "#111827",   # card / panel surface
    "bg_elevated":   "#1A2235",   # slightly raised elements
    "bg_border":     "#1E2D45",   # subtle borders
    "accent_blue":   "#4A9EFF",   # primary CTA / highlights
    "accent_cyan":   "#06B6D4",   # secondary accent
    "accent_green":  "#10B981",   # positive / active
    "accent_amber":  "#F59E0B",   # warning / lockout
    "accent_red":    "#EF4444",   # danger / inactive
    "text_primary":  "#E2E8F0",   # main text
    "text_secondary":"#94A3B8",   # muted labels
    "text_tertiary": "#475569",   # very muted
    "tank_fill":     "#1D6FA4",   # tank available fill
    "tank_fill2":    "#2596D4",   # tank fill highlight
    "tank_lock":     "#B45309",   # lockout fill
    "tank_lock2":    "#F59E0B",   # lockout highlight
    "tank_empty":    "#0D1626",   # empty tank
    "tank_border":   "#1E3A5F",   # tank shell
}


def inject_theme() -> None:
    """Inject full CSS override. Call once after st.set_page_config."""
    st.markdown(f"""
    <style>
    /* ── Google Fonts ──────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Root resets ────────────────────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {C["bg_base"]} !important;
        font-family: 'DM Sans', sans-serif !important;
        color: {C["text_primary"]} !important;
    }}

    /* ── Remove Streamlit default padding ──────────────────────────── */
    .block-container {{
        padding-top: 72px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1600px !important;
    }}

    /* ── Hide hamburger + footer ────────────────────────────────────── */
    #MainMenu, footer, header {{
        visibility: hidden !important;
    }}

    /* ── Fixed top nav bar ──────────────────────────────────────────── */
    .nav-bar {{
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 56px;
        background: {C["bg_surface"]};
        border-bottom: 1px solid {C["bg_border"]};
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
        z-index: 9999;
        backdrop-filter: blur(8px);
    }}
    .nav-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .nav-logo {{
        width: 28px; height: 28px;
        background: linear-gradient(135deg, {C["accent_blue"]}, {C["accent_cyan"]});
        border-radius: 6px;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; font-weight: 700; color: white;
    }}
    .nav-title {{
        font-size: 15px;
        font-weight: 600;
        color: {C["text_primary"]};
        letter-spacing: -0.01em;
    }}
    .nav-subtitle {{
        font-size: 11px;
        color: {C["text_secondary"]};
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }}
    .nav-right {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .nav-user {{
        display: flex;
        align-items: center;
        gap: 8px;
        background: {C["bg_elevated"]};
        border: 1px solid {C["bg_border"]};
        border-radius: 20px;
        padding: 5px 14px 5px 10px;
        font-size: 13px;
        color: {C["text_secondary"]};
    }}
    .nav-user-dot {{
        width: 8px; height: 8px;
        background: {C["accent_green"]};
        border-radius: 50%;
    }}
    .nav-env-badge {{
        font-size: 10px;
        font-weight: 600;
        color: {C["accent_blue"]};
        background: rgba(74,158,255,0.12);
        border: 1px solid rgba(74,158,255,0.25);
        border-radius: 4px;
        padding: 2px 8px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}

    /* ── Tabs ────────────────────────────────────────────────────────── */
    [data-testid="stTabs"] [role="tablist"] {{
        background: {C["bg_surface"]};
        border-radius: 8px;
        padding: 4px;
        gap: 2px;
        border: 1px solid {C["bg_border"]};
    }}
    [data-testid="stTabs"] button[role="tab"] {{
        background: transparent !important;
        color: {C["text_secondary"]} !important;
        border-radius: 6px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 7px 16px !important;
        transition: all 0.15s ease !important;
        border: none !important;
    }}
    [data-testid="stTabs"] button[role="tab"]:hover {{
        color: {C["text_primary"]} !important;
        background: {C["bg_elevated"]} !important;
    }}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: {C["accent_blue"]} !important;
        color: white !important;
        font-weight: 600 !important;
    }}

    /* ── Selectbox / inputs ──────────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stNumberInput"] > div > div > input,
    [data-testid="stTextInput"] > div > div > input {{
        background: {C["bg_elevated"]} !important;
        border: 1px solid {C["bg_border"]} !important;
        border-radius: 6px !important;
        color: {C["text_primary"]} !important;
        font-size: 13px !important;
        font-family: 'DM Sans', sans-serif !important;
    }}
    [data-testid="stSelectbox"] > div > div:focus-within,
    [data-testid="stNumberInput"] > div > div > input:focus,
    [data-testid="stTextInput"] > div > div > input:focus {{
        border-color: {C["accent_blue"]} !important;
        box-shadow: 0 0 0 2px rgba(74,158,255,0.15) !important;
    }}

    /* ── Buttons ─────────────────────────────────────────────────────── */
    [data-testid="stButton"] > button {{
        background: {C["bg_elevated"]} !important;
        border: 1px solid {C["bg_border"]} !important;
        color: {C["text_primary"]} !important;
        border-radius: 6px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        font-family: 'DM Sans', sans-serif !important;
        transition: all 0.15s ease !important;
        padding: 6px 16px !important;
    }}
    [data-testid="stButton"] > button:hover {{
        border-color: {C["accent_blue"]} !important;
        color: {C["accent_blue"]} !important;
        background: rgba(74,158,255,0.08) !important;
    }}
    [data-testid="stButton"] > button[kind="primary"] {{
        background: {C["accent_blue"]} !important;
        border-color: {C["accent_blue"]} !important;
        color: white !important;
    }}
    [data-testid="stButton"] > button[kind="primary"]:hover {{
        background: #3a8ef0 !important;
        border-color: #3a8ef0 !important;
        color: white !important;
    }}

    /* ── Dataframes ──────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {C["bg_border"]} !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }}
    [data-testid="stDataFrame"] iframe {{
        border-radius: 8px !important;
    }}

    /* ── Metrics (default st.metric) ─────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: {C["bg_surface"]} !important;
        border: 1px solid {C["bg_border"]} !important;
        border-radius: 8px !important;
        padding: 16px 20px !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
        color: {C["text_secondary"]} !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 26px !important;
        font-weight: 700 !important;
        color: {C["text_primary"]} !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}
    [data-testid="stMetricDelta"] {{
        font-size: 12px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}

    /* ── Expanders ───────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: {C["bg_surface"]} !important;
        border: 1px solid {C["bg_border"]} !important;
        border-radius: 8px !important;
    }}

    /* ── Alerts / info boxes ─────────────────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 8px !important;
        font-size: 13px !important;
    }}

    /* ── Download button ─────────────────────────────────────────────── */
    [data-testid="stDownloadButton"] > button {{
        background: transparent !important;
        border: 1px solid {C["accent_blue"]} !important;
        color: {C["accent_blue"]} !important;
        border-radius: 6px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }}
    [data-testid="stDownloadButton"] > button:hover {{
        background: rgba(74,158,255,0.1) !important;
    }}

    /* ── Dividers ────────────────────────────────────────────────────── */
    hr {{
        border-color: {C["bg_border"]} !important;
        margin: 1.5rem 0 !important;
    }}

    /* ── Subheaders / markdown headers ───────────────────────────────── */
    h1, h2, h3, h4 {{
        font-family: 'DM Sans', sans-serif !important;
        color: {C["text_primary"]} !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }}
    h3 {{ font-size: 16px !important; }}
    h4 {{ font-size: 14px !important; }}

    /* ── Caption / small text ────────────────────────────────────────── */
    [data-testid="stCaptionContainer"] p {{
        color: {C["text_tertiary"]} !important;
        font-size: 12px !important;
    }}

    /* ── Multiselect tags ────────────────────────────────────────────── */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
        background: rgba(74,158,255,0.15) !important;
        color: {C["accent_blue"]} !important;
        border: 1px solid rgba(74,158,255,0.3) !important;
        border-radius: 4px !important;
        font-size: 12px !important;
    }}

    /* ── Scrollbar ───────────────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {C["bg_base"]}; }}
    ::-webkit-scrollbar-thumb {{
        background: {C["bg_border"]};
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: {C["text_tertiary"]}; }}

    /* ── Number input spinners colour fix ────────────────────────────── */
    [data-testid="stNumberInput"] button {{
        background: {C["bg_border"]} !important;
        border: none !important;
        color: {C["text_secondary"]} !important;
    }}

    </style>
    """, unsafe_allow_html=True)


# ── Component helpers ──────────────────────────────────────────────────────────

def render_header(username: str) -> None:
    """Render fixed top navigation bar with brand, env badge, and user pill."""
    st.markdown(f"""
    <div class="nav-bar">
        <div class="nav-brand">
            <div class="nav-logo">LF</div>
            <div>
                <div class="nav-title">Liftings Forecast</div>
                <div class="nav-subtitle">Operations Dashboard</div>
            </div>
        </div>
        <div class="nav-right">
            <span class="nav-env-badge">Live</span>
            <div class="nav-user">
                <div class="nav-user-dot"></div>
                {username}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_positive: bool | None = None,
    icon: str = "",
    accent: str | None = None,
) -> str:
    """Return HTML string for a single KPI card. Use inside kpi_row()."""
    accent_color = accent or C["accent_blue"]
    delta_html = ""
    if delta:
        if delta_positive is True:
            delta_html = f'<div class="kpi-delta kpi-delta-pos">▲ {delta}</div>'
        elif delta_positive is False:
            delta_html = f'<div class="kpi-delta kpi-delta-neg">▼ {delta}</div>'
        else:
            delta_html = f'<div class="kpi-delta kpi-delta-neu">{delta}</div>'

    return f"""
    <div class="kpi-card" style="border-top: 3px solid {accent_color};">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def kpi_row(cards: list[dict]) -> None:
    """
    Render a row of KPI cards.
    Each dict: {label, value, delta?, delta_positive?, icon?, accent?}
    """
    css = f"""
    <style>
    .kpi-row {{
        display: flex;
        gap: 16px;
        margin: 16px 0;
        flex-wrap: wrap;
    }}
    .kpi-card {{
        flex: 1;
        min-width: 160px;
        background: {C["bg_surface"]};
        border: 1px solid {C["bg_border"]};
        border-radius: 10px;
        padding: 18px 20px 14px;
        transition: box-shadow 0.2s;
    }}
    .kpi-card:hover {{
        box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    }}
    .kpi-icon {{
        font-size: 18px;
        margin-bottom: 8px;
        opacity: 0.8;
    }}
    .kpi-label {{
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {C["text_secondary"]};
        margin-bottom: 6px;
    }}
    .kpi-value {{
        font-size: 24px;
        font-weight: 700;
        color: {C["text_primary"]};
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }}
    .kpi-delta {{
        font-size: 11px;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 6px;
        font-weight: 500;
    }}
    .kpi-delta-pos {{ color: {C["accent_green"]}; }}
    .kpi-delta-neg {{ color: {C["accent_red"]}; }}
    .kpi-delta-neu {{ color: {C["text_tertiary"]}; }}
    </style>
    """
    html = css + '<div class="kpi-row">'
    for c in cards:
        html += kpi_card(
            label=c["label"],
            value=c["value"],
            delta=c.get("delta"),
            delta_positive=c.get("delta_positive"),
            icon=c.get("icon", ""),
            accent=c.get("accent"),
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    """Render a visually separated section header."""
    sub_html = f'<div class="sh-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="section-header">
        <div class="sh-title">{title}</div>
        {sub_html}
    </div>
    <style>
    .section-header {{
        margin: 24px 0 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid {C["bg_border"]};
    }}
    .sh-title {{
        font-size: 14px;
        font-weight: 600;
        color: {C["text_primary"]};
        letter-spacing: -0.01em;
    }}
    .sh-sub {{
        font-size: 12px;
        color: {C["text_tertiary"]};
        margin-top: 2px;
    }}
    </style>
    """, unsafe_allow_html=True)


def status_badge(status: str, reason: str | None = None) -> str:
    """Return HTML for an ACTIVE or INACTIVE status badge."""
    if status == "inactive":
        reason_html = f'<div class="badge-reason">{reason}</div>' if reason else ""
        return f"""
        <div class="status-badge status-inactive">
            <span class="badge-dot"></span>
            INACTIVE
            {reason_html}
        </div>
        <style>
        .status-badge {{
            display: inline-flex;
            flex-direction: column;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 14px;
            gap: 4px;
        }}
        .status-inactive {{
            background: rgba(239,68,68,0.1);
            border: 1.5px solid rgba(239,68,68,0.4);
            color: {C["accent_red"]};
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}
        .badge-dot {{
            display: inline-block;
            width: 7px; height: 7px;
            border-radius: 50%;
            background: {C["accent_red"]};
            margin-right: 8px;
        }}
        .badge-reason {{
            font-size: 12px;
            font-weight: 400;
            color: rgba(239,68,68,0.75);
            letter-spacing: 0;
            padding-left: 15px;
        }}
        </style>
        """
    return f"""
    <div class="status-badge status-active">
        <span class="badge-dot-g"></span>
        ACTIVE
    </div>
    <style>
    .status-active {{
        display: inline-flex;
        align-items: center;
        background: rgba(16,185,129,0.1);
        border: 1.5px solid rgba(16,185,129,0.35);
        color: {C["accent_green"]};
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.05em;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 14px;
        gap: 8px;
    }}
    .badge-dot-g {{
        display: inline-block;
        width: 7px; height: 7px;
        border-radius: 50%;
        background: {C["accent_green"]};
    }}
    </style>
    """


def build_tank_svg(
    product: str,
    current_volume: float,
    max_capacity: float,
    lockouts_for_product: list[dict],
) -> str:
    """
    Upgraded enterprise-grade SVG cylindrical tank.
    Replaces the version defined inline in app.py.
    """
    W, H = 180, 340
    tx, ty = 34, 24        # tank rect origin
    tw, th = 112, 272      # tank dimensions
    ell_ry = 16

    total_lock   = sum(lo["amount"] for lo in lockouts_for_product)
    available    = max(0.0, current_volume - total_lock)
    pct_avail    = min(available / max_capacity,   1.0) if max_capacity > 0 else 0.0
    pct_lock     = min(total_lock / max_capacity,  1.0) if max_capacity > 0 else 0.0
    pct_total    = min(pct_avail + pct_lock,        1.0)

    fill_avail   = pct_avail * th
    fill_lock    = pct_lock  * th
    bot_y        = ty + th
    avail_top    = bot_y - fill_avail
    lock_top     = avail_top - fill_lock
    pct_disp     = int(pct_total * 100)

    # Colour ramps by fill level
    if pct_total > 0.5:
        fc1, fc2 = "#1558A0", "#2580D4"
    else:
        fc1, fc2 = "#8B1A1A", "#C93333"

    lc1, lc2 = "#92400E", "#F59E0B"

    pid = product.replace(" ", "_").replace("/", "_")

    parts = [f'<svg width="{W}" height="{H + 70}" xmlns="http://www.w3.org/2000/svg">']

    # ── Defs ──────────────────────────────────────────────────────────────────
    parts.append(f"""
  <defs>
    <linearGradient id="ga_{pid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="{fc1}" stop-opacity="0.9"/>
      <stop offset="45%"  stop-color="{fc2}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{fc1}" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="gl_{pid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="{lc1}" stop-opacity="0.9"/>
      <stop offset="50%"  stop-color="{lc2}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{lc1}" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="gbody_{pid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="#090E1C"/>
      <stop offset="50%"  stop-color="#0F1929"/>
      <stop offset="100%" stop-color="#090E1C"/>
    </linearGradient>
    <linearGradient id="gsheen_{pid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="white" stop-opacity="0"/>
      <stop offset="30%"  stop-color="white" stop-opacity="0.04"/>
      <stop offset="100%" stop-color="white" stop-opacity="0"/>
    </linearGradient>
    <filter id="blur_{pid}">
      <feGaussianBlur stdDeviation="1.5"/>
    </filter>
    <clipPath id="clip_{pid}">
      <rect x="{tx}" y="{ty}" width="{tw}" height="{th}"/>
    </clipPath>
  </defs>""")

    # ── Tank shell ─────────────────────────────────────────────────────────────
    parts.append(f"""
  <rect x="{tx}" y="{ty}" width="{tw}" height="{th}"
        fill="url(#gbody_{pid})"/>""")

    # ── Fluid fills ────────────────────────────────────────────────────────────
    if fill_avail > 0:
        parts.append(f"""
  <rect x="{tx}" y="{avail_top:.1f}" width="{tw}" height="{fill_avail:.1f}"
        fill="url(#ga_{pid})" clip-path="url(#clip_{pid})"/>""")

    if fill_lock > 0:
        parts.append(f"""
  <rect x="{tx}" y="{lock_top:.1f}" width="{tw}" height="{fill_lock:.1f}"
        fill="url(#gl_{pid})" clip-path="url(#clip_{pid})"/>""")

    # ── Surface glows ──────────────────────────────────────────────────────────
    if fill_avail > 3:
        parts.append(f"""
  <ellipse cx="{tx + tw//2}" cy="{avail_top:.1f}" rx="{tw//2 - 4}" ry="{ell_ry//2}"
           fill="{fc2}" opacity="0.35" filter="url(#blur_{pid})"/>""")

    if fill_lock > 3:
        parts.append(f"""
  <ellipse cx="{tx + tw//2}" cy="{lock_top:.1f}" rx="{tw//2 - 4}" ry="{ell_ry//2}"
           fill="{lc2}" opacity="0.45" filter="url(#blur_{pid})"/>""")

    # ── Sheen overlay ──────────────────────────────────────────────────────────
    parts.append(f"""
  <rect x="{tx}" y="{ty}" width="{tw//3}" height="{th}"
        fill="url(#gsheen_{pid})" clip-path="url(#clip_{pid})"/>""")

    # ── Tick marks + scale labels ──────────────────────────────────────────────
    for pct_t in [0.25, 0.5, 0.75]:
        tick_y = bot_y - pct_t * th
        major = pct_t == 0.5
        parts.append(f"""
  <line x1="{tx + tw - (12 if major else 7)}" y1="{tick_y:.1f}"
        x2="{tx + tw}" y2="{tick_y:.1f}"
        stroke="#1E3A5F" stroke-width="{"1.5" if major else "1"}"/>
  <text x="{tx + tw + 5}" y="{tick_y + 4:.1f}"
        font-size="8" font-family="'JetBrains Mono', monospace"
        fill="#334E68" font-weight="{"600" if major else "400"}"
        >{int(pct_t*100)}%</text>""")

    # ── Border shell ───────────────────────────────────────────────────────────
    parts.append(f"""
  <rect x="{tx}" y="{ty}" width="{tw}" height="{th}"
        fill="none" stroke="#1E3A5F" stroke-width="1.5"/>""")

    # ── Top / bottom caps ──────────────────────────────────────────────────────
    parts.append(f"""
  <ellipse cx="{tx + tw//2}" cy="{ty}" rx="{tw//2}" ry="{ell_ry}"
           fill="#090E1C" stroke="#1E3A5F" stroke-width="1.5"/>
  <ellipse cx="{tx + tw//2}" cy="{ty + th}" rx="{tw//2}" ry="{ell_ry}"
           fill="#060C18" stroke="#1E3A5F" stroke-width="1.5"/>""")

    # ── Percentage label ───────────────────────────────────────────────────────
    text_y = ty + th // 2 + 8
    parts.append(f"""
  <text x="{tx + tw//2}" y="{text_y}"
        text-anchor="middle" font-size="26" font-weight="700"
        font-family="'JetBrains Mono', monospace"
        fill="white" opacity="0.9">{pct_disp}%</text>""")

    # ── Product name ───────────────────────────────────────────────────────────
    label_y = H + 26
    parts.append(f"""
  <text x="{tx + tw//2}" y="{label_y}"
        text-anchor="middle" font-size="13" font-weight="600"
        font-family="'DM Sans', sans-serif"
        fill="#CBD5E1">{product}</text>""")

    # ── Volume sub-label ───────────────────────────────────────────────────────
    parts.append(f"""
  <text x="{tx + tw//2}" y="{label_y + 17}"
        text-anchor="middle" font-size="10"
        font-family="'JetBrains Mono', monospace"
        fill="#475569">{current_volume:,.0f} / {max_capacity:,.0f}</text>""")

    # ── Legend: available vs locked ────────────────────────────────────────────
    if total_lock > 0:
        parts.append(f"""
  <rect x="{tx}" y="{label_y + 30}" width="10" height="10" rx="2" fill="{fc2}"/>
  <text x="{tx + 14}" y="{label_y + 39}"
        font-size="9" font-family="'DM Sans', sans-serif" fill="#64748B"
        >Available</text>
  <rect x="{tx + 70}" y="{label_y + 30}" width="10" height="10" rx="2" fill="{lc2}"/>
  <text x="{tx + 84}" y="{label_y + 39}"
        font-size="9" font-family="'DM Sans', sans-serif" fill="#64748B"
        >Locked</text>""")

    parts.append("</svg>")
    return "".join(parts)
