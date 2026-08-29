import pandas as pd
import streamlit as st

from components.risk import (
    render_priority_attention,
    render_product_risk_panel,
)
from services.analytics import fetch_control_tower_summary
from services.snowflake import fetch_product_risk_signals


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="ChainLoom | Control Tower",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Design system
# ============================================================

st.markdown(
    """
    <style>

    /* ======================================================
       Global
       ====================================================== */

    .block-container {
        max-width: 1380px;
        padding-top: 3.5rem;
        padding-bottom: 4rem;
    }

    /* ======================================================
       Brand
       ====================================================== */

    .brand-kicker {
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        color: #64748b;
        margin-bottom: 0.35rem;
    }

    .brand-title {
        font-size: 2.8rem;
        line-height: 1.02;
        font-weight: 850;
        letter-spacing: -0.05em;
        color: #0f172a;
    }

    .brand-subtitle {
        margin-top: 0.55rem;
        max-width: 780px;
        color: #64748b;
        font-size: 0.96rem;
        line-height: 1.55;
    }

    .live-pill {
        display: inline-block;
        margin-top: 0.9rem;
        padding: 0.34rem 0.72rem;
        border-radius: 999px;
        background: #ecfdf5;
        color: #047857;
        font-size: 0.67rem;
        font-weight: 800;
        letter-spacing: 0.07em;
    }

    /* ======================================================
       Section headers
       ====================================================== */

    .section-header {
        margin-top: 2.6rem;
        margin-bottom: 1rem;
    }

    .section-kicker,
    .attention-kicker {
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        color: #64748b;
    }

    .section-title,
    .attention-title {
        margin-top: 0.2rem;
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0f172a;
    }

    .section-subtitle {
        margin-top: 0.2rem;
        color: #64748b;
        font-size: 0.84rem;
    }

    /* ======================================================
       KPI area
       ====================================================== */

    div[data-testid="stMetric"] {
        padding: 0.2rem 0;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.72rem;
        color: #64748b;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 750;
        color: #0f172a;
    }

    /* ======================================================
       Buttons
       ====================================================== */

    .stButton > button {
        border-radius: 9px;
        font-weight: 600;
    }

    /* ======================================================
       Attention
       ====================================================== */

    .attention-kicker {
        margin-top: 2.7rem;
    }

    .attention-title {
        margin-bottom: 0.9rem;
    }

    /* ======================================================
       Footer
       ====================================================== */

    .data-note {
        margin-top: 1.8rem;
        color: #94a3b8;
        font-size: 0.7rem;
        line-height: 1.5;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Header
# ============================================================

header_left, header_right = st.columns([6, 1])

with header_left:

    st.markdown(
        """
        <div class="brand-kicker">
            CHAINLOOM · SUPPLY CHAIN INTELLIGENCE
        </div>

        <div class="brand-title">
            Control Tower
        </div>

        <div class="brand-subtitle">
            A governed executive view across fulfillment, delivery,
            production, inventory, and supplier risk.
        </div>

        <div class="live-pill">
            ● LIVE SNOWFLAKE DATA
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_right:

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(
        "↻ Refresh",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# Load data
# ============================================================

try:

    summary = fetch_control_tower_summary()

    risk_df = fetch_product_risk_signals()

except Exception as exc:

    st.error("Unable to load ChainLoom data.")
    st.exception(exc)
    st.stop()


# ============================================================
# Executive signals
# ============================================================

st.markdown(
    """
    <div class="section-header">
        <div class="section-kicker">EXECUTIVE SIGNALS</div>
        <div class="section-title">What needs attention?</div>
        <div class="section-subtitle">
            Current network-level indicators from governed ChainLoom data
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


high_risk = int(
    (risk_df["RISK_SIGNAL_COUNT"].fillna(0) >= 2).sum()
)

watchlist = int(
    (risk_df["RISK_SIGNAL_COUNT"].fillna(0) == 1).sum()
)

products = len(risk_df)


k1, k2, k3, k4, k5 = st.columns(5)


with k1:
    st.metric(
        "High-Risk Products",
        high_risk,
        help="Products with two or more independent risk signals.",
    )


with k2:
    st.metric(
        "Watchlist",
        watchlist,
        help="Products with exactly one active risk signal.",
    )


with k3:
    st.metric(
        "Products Monitored",
        products,
    )


with k4:

    value = summary["FULFILLMENT_RATE"]

    st.metric(
        "Network Fulfillment",
        "—" if pd.isna(value) else f"{float(value) * 100:.1f}%",
        help="Total fulfilled quantity divided by total ordered quantity.",
    )


with k5:

    value = summary["ON_TIME_DELIVERY_RATE"]

    st.metric(
        "On-Time Delivery",
        "—" if pd.isna(value) else f"{float(value) * 100:.1f}%",
        help="On-time eligible shipments divided by delivery-eligible shipments.",
    )


# ============================================================
# Priority attention
# ============================================================

render_priority_attention(risk_df)


# ============================================================
# Product risk overview
# ============================================================

render_product_risk_panel(risk_df)


# ============================================================
# Ask ChainLoom
# ============================================================

st.markdown(
    """
    <div class="section-header">
        <div class="section-kicker">
            AI-ASSISTED INVESTIGATION
        </div>
        <div class="section-title">
            Ask ChainLoom
        </div>
        <div class="section-subtitle">
            Explore governed supply-chain intelligence using natural language.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):

    st.markdown("### What would you like to investigate?")

    st.write(
        "Ask about fulfillment, delivery, production, inventory, "
        "supplier performance, or product risk."
    )

    question = st.text_input(
        "Ask ChainLoom",
        placeholder="e.g. Which products currently need attention?",
        label_visibility="collapsed",
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("Suggested")

        st.button(
            "Products with multiple risk signals",
            disabled=True,
            use_container_width=True,
        )

    with c2:
        st.caption("Suggested")

        st.button(
            "Carriers with lowest OTD",
            disabled=True,
            use_container_width=True,
        )

    with c3:
        st.caption("Suggested")

        st.button(
            "Parts below safety stock",
            disabled=True,
            use_container_width=True,
        )

# ============================================================
# Governance
# ============================================================

st.markdown(
    """
    <div class="data-note">
        ChainLoom keeps analytical surfaces independent to prevent
        fact-to-fact fan-out and avoids unsupported causal inference.
        AI responses are grounded in the governed semantic model.
    </div>
    """,
    unsafe_allow_html=True,
)