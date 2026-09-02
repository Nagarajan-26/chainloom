import html

import pandas as pd
import streamlit as st


def _format_percentage(value):
    if pd.isna(value):
        return "—"
    return f"{float(value) * 100:.1f}%"


def render_priority_attention(df):
    """Render the highest-priority governed product risk signal."""

    risky = df[df["RISK_SIGNAL_COUNT"].fillna(0) >= 2].copy()

    if risky.empty:
        st.success("No products currently have multiple active risk signals.")
        return

    risky = risky.sort_values(
        by=["RISK_SIGNAL_COUNT", "FULFILLMENT_RATE", "ON_TIME_DELIVERY_RATE"],
        ascending=[False, True, True],
    )

    row = risky.iloc[0]

    signals = []
    if bool(row["FULFILLMENT_RISK_FLAG"]):
        signals.append("Fulfillment")
    if bool(row["DELIVERY_RISK_FLAG"]):
        signals.append("Delivery")
    if bool(row["PRODUCTION_RISK_FLAG"]):
        signals.append("Production")

    signal_text = " · ".join(signals)

    st.markdown(
        """
        <div class="cl-section">
          <div class="cl-section-kicker">PRIORITY ATTENTION</div>
          <div class="cl-section-title">Where should attention start?</div>
          <div class="cl-section-sub">Highest-priority product based on independently observed risk signals</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        left, right = st.columns([2.2, 1])

        with left:
            st.caption(f"{row['PRODUCT_ID']} · HIGH ATTENTION")
            st.markdown(f"### {html.escape(str(row['PRODUCT_NAME']))}")
            st.write(
                f"**{int(row['RISK_SIGNAL_COUNT'])} independent risk signals** · {signal_text}"
            )

        with right:
            st.metric("Fulfillment", _format_percentage(row["FULFILLMENT_RATE"]))
            st.metric("On-Time Delivery", _format_percentage(row["ON_TIME_DELIVERY_RATE"]))

        st.caption(
            "Signals are independently observed. Their co-occurrence does not establish causality."
        )


def render_product_risk_panel(df):
    """Render the governed product-level risk overview."""

    st.markdown(
        """
        <div class="cl-section">
          <div class="cl-section-kicker">PRODUCT RISK OVERVIEW</div>
          <div class="cl-section-title">Independent risk signals by product</div>
          <div class="cl-section-sub">Fulfillment, delivery and production indicators remain analytically distinct.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No product risk signals are available.")
        return

    display_df = pd.DataFrame(
        {
            "Product": df["PRODUCT_NAME"],
            "Fulfillment": df["FULFILLMENT_RATE"].apply(
                lambda x: None if pd.isna(x) else float(x) * 100
            ),
            "On-Time Delivery": df["ON_TIME_DELIVERY_RATE"].apply(
                lambda x: None if pd.isna(x) else float(x) * 100
            ),
            "Production": df["PRODUCTION_ATTAINMENT"].apply(
                lambda x: None if pd.isna(x) else float(x) * 100
            ),
            "Risk Signals": df["RISK_SIGNAL_COUNT"].fillna(0).astype(int),
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Product": st.column_config.TextColumn(
                "Product",
                width="large",
            ),
            "Fulfillment": st.column_config.ProgressColumn(
                "Fulfillment",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "On-Time Delivery": st.column_config.ProgressColumn(
                "On-Time Delivery",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "Production": st.column_config.ProgressColumn(
                "Production",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "Risk Signals": st.column_config.NumberColumn(
                "Risk Signals",
                min_value=0,
                max_value=3,
                step=1,
            ),
        },
    )

    st.caption(
        "Independent observed indicators · missing metrics remain unavailable and are not interpreted as zero."
    )
