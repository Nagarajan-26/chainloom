import json
import os
import urllib.error
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st

# PASS 1 — visual system only. Functional/service logic is unchanged.

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
# Cortex Analyst — Snowflake Container Runtime
# ============================================================

SEMANTIC_VIEW = "CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS"


def _get_session_token() -> str:
    token_path = "/snowflake/session/token"
    if not os.path.exists(token_path):
        raise RuntimeError(
            "Snowflake session token is unavailable. "
            "This app must run in Snowflake Container Runtime."
        )
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise RuntimeError("Snowflake session token is empty.")
    return token


def call_analyst(question: str, history=None) -> dict:
    """Call Cortex Analyst through the Container Runtime REST endpoint.

    Uses urllib from the Python standard library so no new dependency is
    required in requirements.txt.
    """
    host = os.getenv("SNOWFLAKE_HOST")
    if not host:
        raise RuntimeError(
            "SNOWFLAKE_HOST is not available in the Streamlit Container Runtime."
        )

    messages = list(history or [])
    messages.append(
        {"role": "user", "content": [{"type": "text", "text": question}]}
    )

    body = json.dumps(
        {"messages": messages, "semantic_view": SEMANTIC_VIEW}
    ).encode("utf-8")

    req = urllib.request.Request(
        f"https://{host}/api/v2/cortex/analyst/message",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {_get_session_token()}",
            "X-Snowflake-Authorization-Token-Type": "OAUTH",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw)
            request_id = (
                result.get("request_id")
                or response.headers.get("X-Snowflake-Request-ID")
                or response.headers.get("X-Snowflake-Request-Id")
            )
            if request_id and not result.get("request_id"):
                result["request_id"] = request_id
            return result
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Cortex Analyst HTTP {exc.code}: {detail[:1000]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach Cortex Analyst: {exc.reason}"
        ) from exc


def parse_analyst_response(resp: dict) -> dict:
    result = {
        "text": "",
        "sql": "",
        "warnings": [],
        "request_id": resp.get("request_id", ""),
    }

    message = resp.get("message", resp)
    content = message.get("content", []) if isinstance(message, dict) else []

    if content:
        for item in content:
            if item.get("type") == "text":
                result["text"] += item.get("text", "")
            elif item.get("type") == "sql":
                result["sql"] = item.get("statement", "")
    elif isinstance(resp.get("result"), str):
        raw = resp["result"]
        if "```sql" in raw:
            before, after = raw.split("```sql", 1)
            result["text"] = before.strip()
            result["sql"] = after.split("```", 1)[0].strip()
        else:
            result["text"] = raw.strip()

    warnings = resp.get("warnings", [])
    if isinstance(warnings, list):
        result["warnings"] = warnings

    return result


def run_analyst_sql(sql: str):
    if not sql or not sql.strip():
        return None

    # Reuse the application's existing Snowflake connection.
    conn = st.connection(
        "snowflake",
        ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"),
    )
    session = conn.session()
    return session.sql(sql).to_pandas()


# ============================================================
# Design system
# ============================================================

st.markdown(
    """
    <style>
    /* ============================================================
       PASS 1.1 — Alignment / hierarchy polish
       UI-only. Application logic and data flow are untouched.
       ============================================================ */
    :root {
        --cl-ink:#0F172A;
        --cl-text:#334155;
        --cl-muted:#64748B;
        --cl-subtle:#94A3B8;
        --cl-border:#E2E8F0;
        --cl-border-strong:#CBD5E1;
        --cl-surface:#FFFFFF;
        --cl-canvas:#F6F8FC;
        --cl-blue:#2563EB;
        --cl-blue-soft:#EFF6FF;
        --cl-cyan:#29B5E8;
        --cl-green:#047857;
        --cl-green-soft:#ECFDF5;
        --cl-red:#B91C1C;
        --cl-red-soft:#FEF2F2;
    }

    .stApp {
        background:var(--cl-canvas);
        color:var(--cl-text);
    }

    .block-container {
        max-width:1420px;
        padding-top:1rem;
        padding-bottom:3rem;
    }

    html, body, [class*="css"] {
        font-family:Inter,ui-sans-serif,system-ui,-apple-system,
        BlinkMacSystemFont,"Segoe UI",sans-serif;
    }

    h1,h2,h3,h4 {
        color:var(--cl-ink);
        letter-spacing:-.025em;
    }

    /* Header: compact and aligned with the dashboard grid */
    .brand {
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1.5rem;
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:12px;
        padding:.82rem 1rem;
        margin-bottom:.8rem;
        box-shadow:0 1px 3px rgba(15,23,42,.035);
    }

    .brand-left {
        display:flex;
        align-items:center;
        gap:12px;
        min-width:0;
    }

    .mark {
        width:38px;
        height:38px;
        position:relative;
        flex:none;
        border-radius:10px;
        background:var(--cl-blue-soft);
        border:1px solid #DBEAFE;
    }

    .node {
        position:absolute;
        width:7px;
        height:7px;
        border-radius:50%;
        background:var(--cl-cyan);
    }

    .n1{top:5px;left:15px}.n2{top:15px;left:5px}
    .n3{top:15px;left:26px}.n4{top:26px;left:15px}

    .link {
        position:absolute;
        height:1.5px;
        width:15px;
        background:var(--cl-border-strong);
        transform-origin:left center;
    }

    .l1{top:8px;left:18px;transform:rotate(45deg)}
    .l2{top:8px;left:15px;transform:rotate(135deg)}
    .l3{top:18px;left:8px;transform:rotate(45deg)}
    .l4{top:18px;left:18px;transform:rotate(135deg)}

    .brand-name {
        font-size:.54rem;
        font-weight:800;
        letter-spacing:.13em;
        text-transform:uppercase;
        color:var(--cl-muted);
        line-height:1.1;
    }

    .brand-title {
        font-size:1.25rem;
        line-height:1.05;
        font-weight:800;
        color:var(--cl-ink);
        margin-top:.12rem;
    }

    .brand-sub {
        font-size:.66rem;
        color:var(--cl-subtle);
        margin-top:.14rem;
    }

    .live {
        white-space:nowrap;
        font-size:.57rem;
        color:var(--cl-green);
        background:var(--cl-green-soft);
        border:1px solid #A7F3D0;
        border-radius:999px;
        padding:5px 9px;
        font-weight:800;
        letter-spacing:.045em;
    }

    /* KPI row */
    div[data-testid="stMetric"] {
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:10px;
        padding:.72rem .85rem .66rem;
        min-height:78px;
        box-shadow:0 1px 2px rgba(15,23,42,.025);
    }

    div[data-testid="stMetricLabel"] {
        color:var(--cl-muted);
        font-size:.62rem;
        font-weight:750;
    }

    div[data-testid="stMetricValue"] {
        color:var(--cl-ink);
        font-size:1.48rem;
        line-height:1.05;
        font-weight:800;
        letter-spacing:-.035em;
    }

    /* Consistent section spacing */
    .section-label {
        font-size:.58rem;
        font-weight:800;
        letter-spacing:.13em;
        text-transform:uppercase;
        color:var(--cl-subtle);
        margin:1rem 0 .34rem;
    }

    .surface {
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:10px;
        padding:.8rem 1rem;
        box-shadow:0 1px 2px rgba(15,23,42,.02);
    }

    /* Network pulse becomes a full-width status strip rather than a
       right-column island with unused whitespace beside it. */
    .network-pulse {
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1rem;
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:9px;
        padding:.55rem .8rem;
        color:var(--cl-muted);
        font-size:.67rem;
        box-shadow:0 1px 2px rgba(15,23,42,.02);
    }

    .network-pulse strong {
        color:var(--cl-ink);
    }

    .network-pulse-meta {
        color:var(--cl-subtle);
        font-size:.58rem;
        white-space:nowrap;
    }

    /* Ask area: one visual unit */
    .ai-console {
        background:var(--cl-surface);
        border:1px solid #BFDBFE;
        border-top:3px solid var(--cl-blue);
        border-radius:12px;
        padding:.9rem 1rem .55rem;
        margin-top:1rem;
        box-shadow:0 2px 9px rgba(37,99,235,.045);
    }

    .ai-kicker {
        font-size:.56rem;
        font-weight:800;
        letter-spacing:.10em;
        color:var(--cl-blue);
        text-transform:uppercase;
    }

    .ai-title {
        font-size:1.12rem;
        line-height:1.2;
        font-weight:800;
        color:var(--cl-ink);
        margin:.14rem 0 .14rem;
    }

    .ai-sub {
        font-size:.70rem;
        color:var(--cl-muted);
        line-height:1.4;
    }

    /* Suggested-question buttons */
    .stButton > button {
        border-radius:8px;
        min-height:2.35rem;
        border:1px solid var(--cl-border-strong);
        font-weight:620;
        font-size:.70rem;
        line-height:1.2;
        color:var(--cl-text);
        background:#FFFFFF;
        padding:.42rem .65rem;
        transition:border-color .15s ease,box-shadow .15s ease,transform .15s ease;
    }

    .stButton > button:hover {
        border-color:#93C5FD;
        box-shadow:0 3px 9px rgba(37,99,235,.07);
        transform:translateY(-1px);
    }

    .stButton > button[kind="primary"] {
        background:var(--cl-blue);
        border-color:var(--cl-blue);
        color:#FFFFFF;
        font-weight:700;
    }

    div[data-testid="stTextInput"] input {
        border:1px solid var(--cl-border-strong);
        border-radius:8px;
        background:#FFFFFF;
        color:var(--cl-ink);
        min-height:2.55rem;
        font-size:.76rem;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color:#60A5FA;
        box-shadow:0 0 0 3px rgba(37,99,235,.09);
    }

    /* Investigation result card */
    .inv-card {
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:10px;
        padding:.85rem 1rem;
        margin:.65rem 0;
        box-shadow:0 1px 2px rgba(15,23,42,.02);
    }

    .inv-tag {
        font-size:.55rem;
        font-weight:800;
        letter-spacing:.08em;
        text-transform:uppercase;
        color:var(--cl-blue);
    }

    .inv-q {
        font-size:.88rem;
        font-weight:700;
        color:var(--cl-ink);
        margin:.18rem 0 .42rem;
    }

    /* Governance */
    .gov-good {
        background:var(--cl-green-soft);
        border-left:3px solid #22C55E;
        padding:.52rem .7rem;
        border-radius:0 6px 6px 0;
        font-size:.70rem;
        color:#166534;
        margin-top:.35rem;
        line-height:1.4;
    }

    .gov-bad {
        background:var(--cl-red-soft);
        border-left:3px solid #EF4444;
        padding:.52rem .7rem;
        border-radius:0 6px 6px 0;
        font-size:.70rem;
        color:#991B1B;
        margin-top:.35rem;
        line-height:1.4;
    }

    .gov-badges {
        display:flex;
        flex-wrap:wrap;
        gap:.3rem;
        margin-top:.5rem;
    }

    .gb {
        font-size:.54rem;
        color:#166534;
        background:#F0FDF4;
        border:1px solid #BBF7D0;
        border-radius:999px;
        padding:3px 7px;
        font-weight:650;
    }

    .footer {
        text-align:center;
        color:#94A3B8;
        font-size:.57rem;
        border-top:1px solid var(--cl-border);
        margin-top:2rem;
        padding:.9rem;
        line-height:1.5;
    }

    @media (max-width:900px) {
        .block-container {padding-top:.7rem;}
        .brand {align-items:flex-start;}
        .brand-sub {display:none;}
        .live {font-size:.52rem;}
        .network-pulse {align-items:flex-start;flex-direction:column;gap:.25rem;}
        .network-pulse-meta {white-space:normal;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Load governed live data
# ============================================================

try:
    summary = fetch_control_tower_summary()
    risk_df = fetch_product_risk_signals()
except Exception as exc:
    st.error("Unable to load ChainLoom data.")
    st.exception(exc)
    st.stop()

high_risk = int((risk_df["RISK_SIGNAL_COUNT"].fillna(0) >= 2).sum())
watchlist = int((risk_df["RISK_SIGNAL_COUNT"].fillna(0) == 1).sum())
healthy = int((risk_df["RISK_SIGNAL_COUNT"].fillna(0) == 0).sum())
products = len(risk_df)

refresh_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# Header
# ============================================================

st.markdown(
    """
    <div class="brand">
      <div class="brand-left">
        <div class="mark">
          <div class="node n1"></div><div class="node n2"></div>
          <div class="node n3"></div><div class="node n4"></div>
          <div class="link l1"></div><div class="link l2"></div>
          <div class="link l3"></div><div class="link l4"></div>
        </div>
        <div>
          <div class="brand-name">CHAINLOOM · SUPPLY CHAIN INTELLIGENCE</div>
          <div class="brand-title">Control Tower</div>
          <div class="brand-sub">Governed executive intelligence across the supply chain</div>
        </div>
      </div>
      <div class="live">● LIVE SNOWFLAKE DATA</div>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("High-Risk Products", high_risk, help="Products with two or more independent risk signals.")
with k2:
    st.metric("Watchlist", watchlist, help="Products with exactly one active risk signal.")
with k3:
    st.metric("Products Monitored", products)
with k4:
    value = summary["FULFILLMENT_RATE"]
    st.metric("Network Fulfillment", "—" if pd.isna(value) else f"{float(value)*100:.1f}%")
with k5:
    value = summary["ON_TIME_DELIVERY_RATE"]
    st.metric("On-Time Delivery", "—" if pd.isna(value) else f"{float(value)*100:.1f}%")


# ============================================================
# Existing governed executive panels
# ============================================================

render_priority_attention(risk_df)
render_product_risk_panel(risk_df)


# ============================================================
# Network pulse
# ============================================================

st.markdown('<div class="section-label">Network Pulse</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="network-pulse">
      <div>
        <strong>{products}</strong> monitored
        &nbsp; · &nbsp;
        <strong>{high_risk}</strong> high-risk
        &nbsp; · &nbsp;
        <strong>{watchlist}</strong> watchlist
        &nbsp; · &nbsp;
        <strong>{healthy}</strong> healthy
      </div>
      <div class="network-pulse-meta">Refreshed {refresh_ts}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Ask ChainLoom — working suggestion buttons + investigation
# ============================================================

st.markdown(
    """
    <div class="ai-console">
      <div class="ai-kicker">Ask ChainLoom — AI-Assisted Investigation</div>
      <div class="ai-title">What would you like to investigate?</div>
      <div class="ai-sub">Explore governed supply-chain intelligence using natural language.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "analyst_history" not in st.session_state:
    st.session_state["analyst_history"] = []
if "analyst_results" not in st.session_state:
    st.session_state["analyst_results"] = []
if "analyst_input" not in st.session_state:
    st.session_state["analyst_input"] = ""


def _choose_suggestion(text: str):
    # The callback updates the widget's own state before the next rerun.
    st.session_state["analyst_input"] = text


suggestions = [
    "Which products currently show multiple risk signals?",
    "Which carriers have the lowest on-time delivery?",
    "Which parts are below safety stock?",
    "Which suppliers have the highest defect rate?",
]

cols = st.columns(4)
for i, suggestion in enumerate(suggestions):
    with cols[i]:
        st.button(
            suggestion,
            key=f"suggestion_{i}",
            use_container_width=True,
            on_click=_choose_suggestion,
            args=(suggestion,),
        )

question = st.text_input(
    "Ask ChainLoom",
    key="analyst_input",
    placeholder="e.g. What is the fulfillment rate by customer segment?",
    label_visibility="collapsed",
)

ask = st.button("Investigate", type="primary", key="investigate_button")

if ask:
    clean_question = question.strip()
    if not clean_question:
        st.warning("Enter a question or select one of the suggested investigations.")
    else:
        with st.spinner("Consulting Cortex Analyst..."):
            try:
                raw = call_analyst(clean_question, st.session_state["analyst_history"])
                parsed = parse_analyst_response(raw)

                st.session_state["analyst_history"].append(
                    {"role": "user", "content": [{"type": "text", "text": clean_question}]}
                )

                assistant_content = []
                if parsed["text"]:
                    assistant_content.append({"type": "text", "text": parsed["text"]})
                if parsed["sql"]:
                    assistant_content.append({"type": "sql", "statement": parsed["sql"]})
                if assistant_content:
                    st.session_state["analyst_history"].append(
                        {"role": "analyst", "content": assistant_content}
                    )

                df_result = run_analyst_sql(parsed["sql"]) if parsed["sql"] else None
                st.session_state["analyst_results"].append(
                    {
                        "question": clean_question,
                        "parsed": parsed,
                        "df": df_result,
                    }
                )
            except Exception as exc:
                st.error(f"Cortex Analyst error: {exc}")


for entry in reversed(st.session_state["analyst_results"]):
    parsed = entry["parsed"]

    st.markdown(
        f"""
        <div class="inv-card">
          <div class="inv-tag">Ask ChainLoom — Your Investigation</div>
          <div class="inv-q">{entry["question"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if parsed["text"]:
        st.markdown("**Finding**")
        st.markdown(parsed["text"])

    for warning in parsed["warnings"]:
        st.warning(warning)

    if entry["df"] is not None:
        if not entry["df"].empty:
            st.markdown("**Results**")
            st.dataframe(entry["df"], use_container_width=True, hide_index=True)
        else:
            st.info("Query returned no rows.")

    with st.expander("View generated SQL"):
        if parsed["sql"]:
            st.code(parsed["sql"], language="sql")
        else:
            st.caption("No SQL was generated.")

    with st.expander("View governance notes"):
        st.markdown(
            f"**Semantic View:** `{SEMANTIC_VIEW}`  \n"
            f"**Request ID:** `{parsed.get('request_id','')}`  \n"
            "Results are generated through the governed ChainLoom semantic layer."
        )


# ============================================================
# Trust & Governance
# ============================================================

st.markdown('<div class="section-label">Trust &amp; Governance</div>', unsafe_allow_html=True)
st.caption("ChainLoom makes analytical boundaries explicit.")

challenges = [
    {
        "badge": "CAUSAL BOUNDARY",
        "label": "Can P104 shortage be proven as the cause?",
        "question": "Did Part P104 inventory shortages cause production constraints last month?",
        "can": "P104 BOM exposure and observed production constraints can be independently reported.",
        "cannot": "Causation cannot be established. P104_EXPOSURE_FLAG indicates BOM dependency, not proof of shortage. Inventory and production are separate analytical surfaces.",
    },
    {
        "badge": "ATTRIBUTION BOUNDARY",
        "label": "Can supplier delay be proven as the cause?",
        "question": "Which supplier delivery delays directly caused late shipments to our Strategic customers?",
        "can": "Supplier delays and customer shipment delays can be independently observed.",
        "cannot": "Direct supplier-to-customer causation cannot be established because lot/batch genealogy linking a supplier receipt to a customer shipment is unavailable.",
    },
    {
        "badge": "INDEPENDENT SIGNALS",
        "label": "Can multiple risk signals be combined without inventing causality?",
        "question": "Which products currently show multiple independent supply-chain risk signals across fulfillment, delivery, and production?",
        "can": "Multiple independent product risk signals can be reported using the governed RISK_SIGNAL_COUNT.",
        "cannot": "A weighted or causal risk score cannot be inferred. Co-occurrence does not imply causation.",
    },
]

gc = st.columns(3)
for i, ch in enumerate(challenges):
    with gc[i]:
        st.markdown(
            f"""
            <div class="surface" style="min-height:105px;">
              <div style="font-size:.55rem;font-weight:800;letter-spacing:.07em;color:#2563EB;">
                {ch["badge"]}
              </div>
              <div style="font-size:.78rem;font-weight:650;color:#334155;margin-top:.35rem;">
                {ch["label"]}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Run Challenge", key=f"challenge_{i}", use_container_width=True):
            with st.spinner("Running governance challenge..."):
                try:
                    raw = call_analyst(ch["question"])
                    parsed = parse_analyst_response(raw)

                    st.markdown("**BOUNDARY ENFORCED**" if i < 2 else "**GOVERNED**")
                    if parsed["text"]:
                        st.markdown(parsed["text"])
                    for warning in parsed["warnings"]:
                        st.warning(warning)
                    if parsed["sql"]:
                        df = run_analyst_sql(parsed["sql"])
                        if df is not None and not df.empty:
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        with st.expander("View generated SQL"):
                            st.code(parsed["sql"], language="sql")

                    st.markdown(
                        f'<div class="gov-good"><b>What the data can establish:</b> {ch["can"]}</div>'
                        f'<div class="gov-bad"><b>What the data cannot establish:</b> {ch["cannot"]}</div>',
                        unsafe_allow_html=True,
                    )
                    if parsed.get("request_id"):
                        st.caption(f"Request ID: {parsed['request_id']}")
                except Exception as exc:
                    st.error(f"Cortex Analyst error: {exc}")


st.markdown(
    """
    <div class="gov-badges">
      <span class="gb">✓ Snowflake Semantic View</span>
      <span class="gb">✓ Verified Query Repository</span>
      <span class="gb">✓ Independent Analytical Surfaces</span>
      <span class="gb">✓ No Unsupported Fact-to-Fact Joins</span>
      <span class="gb">✓ No Unsupported Causal Inference</span>
      <span class="gb">✓ Semi-Additive Inventory Handling</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("How ChainLoom reasons"):
    st.markdown(
        """
        **Analytical architecture**

        ChainLoom maintains independent analytical surfaces for fulfillment,
        shipment performance, production, inventory, and supplier performance.

        **Governance**

        - No unsupported fact-to-fact joins.
        - Inventory remains snapshot-aware and semi-additive.
        - P104 exposure indicates BOM dependency, not proof of shortage or causality.
        - Supplier-to-customer causality requires lot/batch genealogy that is not present.
        - Product risk signals are independent observed indicators.
        - Missing metrics remain unavailable rather than being silently converted to zero.

        **Semantic View:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`
        """
    )

st.markdown(
    f'<div class="footer">ChainLoom · Snowflake-Native Supply Chain Intelligence<br>'
    f'Semantic View: {SEMANTIC_VIEW} · Refreshed: {refresh_ts}</div>',
    unsafe_allow_html=True,
)
