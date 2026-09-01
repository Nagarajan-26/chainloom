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
# ChainLoom — Enterprise Control Tower UI
# Visual layer only. Functional/service logic above is unchanged.
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --cl-ink:#0B1220;
        --cl-text:#334155;
        --cl-muted:#64748B;
        --cl-subtle:#94A3B8;
        --cl-border:#E2E8F0;
        --cl-border-strong:#CBD5E1;
        --cl-surface:#FFFFFF;
        --cl-canvas:#F7F9FC;
        --cl-blue:#2563EB;
        --cl-blue-soft:#EFF6FF;
        --cl-cyan:#29B5E8;
        --cl-green:#047857;
        --cl-green-soft:#ECFDF5;
        --cl-red:#B91C1C;
        --cl-red-soft:#FEF2F2;
        --cl-amber:#B45309;
        --cl-amber-soft:#FFFBEB;
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(37,99,235,.045), transparent 30rem),
            var(--cl-canvas);
        color:var(--cl-text);
    }

    .block-container {
        max-width:1480px;
        padding-top:1.15rem;
        padding-bottom:3rem;
    }

    html, body, [class*="css"] {
        font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    }

    h1,h2,h3,h4 { color:var(--cl-ink); letter-spacing:-.025em; }

    /* ---------- Header ---------- */
    .cl-header {
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1.5rem;
        background:rgba(255,255,255,.97);
        border:1px solid var(--cl-border);
        border-radius:14px;
        padding:.95rem 1.1rem;
        margin-bottom:1rem;
        box-shadow:0 1px 3px rgba(15,23,42,.035);
    }

    .cl-brand {
        display:flex;
        align-items:center;
        gap:13px;
        min-width:0;
    }

    .cl-mark {
        width:42px;
        height:42px;
        position:relative;
        flex:none;
        border-radius:11px;
        background:var(--cl-blue-soft);
        border:1px solid #DBEAFE;
    }

    .cl-node {
        position:absolute;
        width:8px;
        height:8px;
        border-radius:50%;
        background:var(--cl-cyan);
        box-shadow:0 0 0 3px rgba(41,181,232,.10);
    }

    .cl-n1{top:5px;left:17px}.cl-n2{top:17px;left:5px}
    .cl-n3{top:17px;left:29px}.cl-n4{top:29px;left:17px}

    .cl-link {
        position:absolute;
        height:1.5px;
        width:17px;
        background:#CBD5E1;
        transform-origin:left center;
    }

    .cl-l1{top:9px;left:21px;transform:rotate(45deg)}
    .cl-l2{top:9px;left:17px;transform:rotate(135deg)}
    .cl-l3{top:21px;left:9px;transform:rotate(45deg)}
    .cl-l4{top:21px;left:21px;transform:rotate(135deg)}

    .cl-eyebrow {
        font-size:.60rem;
        font-weight:800;
        letter-spacing:.16em;
        text-transform:uppercase;
        color:var(--cl-muted);
    }

    .cl-title {
        font-size:1.42rem;
        line-height:1.05;
        font-weight:800;
        color:var(--cl-ink);
        margin-top:.06rem;
    }

    .cl-subtitle {
        font-size:.70rem;
        color:var(--cl-subtle);
        margin-top:.18rem;
    }

    .cl-live {
        white-space:nowrap;
        font-size:.60rem;
        color:var(--cl-green);
        background:var(--cl-green-soft);
        border:1px solid #A7F3D0;
        border-radius:999px;
        padding:6px 10px;
        font-weight:800;
        letter-spacing:.055em;
    }

    /* ---------- Section hierarchy ---------- */
    .cl-section {
        margin:1.15rem 0 .55rem;
    }

    .cl-section-kicker {
        font-size:.59rem;
        font-weight:800;
        letter-spacing:.14em;
        text-transform:uppercase;
        color:var(--cl-blue);
    }

    .cl-section-title {
        font-size:1.05rem;
        line-height:1.2;
        font-weight:800;
        color:var(--cl-ink);
        margin-top:.16rem;
    }

    .cl-section-sub {
        font-size:.72rem;
        color:var(--cl-muted);
        margin-top:.12rem;
    }

    /* ---------- KPI cards ---------- */
    div[data-testid="stMetric"] {
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:11px;
        padding:.82rem .95rem .72rem;
        min-height:88px;
        box-shadow:0 1px 2px rgba(15,23,42,.025);
    }

    div[data-testid="stMetricLabel"] {
        color:var(--cl-muted);
        font-size:.66rem;
        font-weight:700;
    }

    div[data-testid="stMetricValue"] {
        color:var(--cl-ink);
        font-size:1.62rem;
        line-height:1.05;
        font-weight:800;
        letter-spacing:-.035em;
    }

    /* ---------- Surfaces ---------- */
    .cl-surface {
        background:var(--cl-surface);
        border:1px solid var(--cl-border);
        border-radius:12px;
        padding:1rem 1.1rem;
        box-shadow:0 1px 2px rgba(15,23,42,.025);
    }

    .cl-pulse {
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1rem;
        flex-wrap:wrap;
    }

    .cl-pulse-main {
        font-size:.84rem;
        color:var(--cl-text);
    }

    .cl-pulse-main b { color:var(--cl-ink); }

    .cl-refresh {
        font-size:.61rem;
        color:var(--cl-subtle);
    }

    /* ---------- AI console ---------- */
    .cl-ai {
        background:var(--cl-surface);
        border:1px solid #BFDBFE;
        border-top:3px solid var(--cl-blue);
        border-radius:13px;
        padding:1rem 1.15rem .85rem;
        margin-top:.75rem;
        box-shadow:0 3px 12px rgba(37,99,235,.045);
    }

    .cl-ai-kicker {
        font-size:.59rem;
        font-weight:800;
        letter-spacing:.11em;
        color:var(--cl-blue);
        text-transform:uppercase;
    }

    .cl-ai-title {
        font-size:1.18rem;
        line-height:1.2;
        font-weight:800;
        color:var(--cl-ink);
        margin:.18rem 0 .20rem;
    }

    .cl-ai-sub {
        font-size:.74rem;
        color:var(--cl-muted);
        line-height:1.45;
    }

    .stButton > button {
        border-radius:9px;
        min-height:2.35rem;
        border:1px solid var(--cl-border-strong);
        font-weight:650;
        color:var(--cl-text);
        background:#FFFFFF;
        transition:border-color .15s ease,box-shadow .15s ease,transform .15s ease;
    }

    .stButton > button:hover {
        border-color:#93C5FD;
        box-shadow:0 3px 10px rgba(37,99,235,.08);
        transform:translateY(-1px);
    }

    .stButton > button[kind="primary"] {
        background:var(--cl-blue);
        border-color:var(--cl-blue);
        color:#FFFFFF;
    }

    div[data-testid="stTextInput"] input {
        border:1px solid var(--cl-border-strong);
        border-radius:10px;
        background:#FFFFFF;
        color:var(--cl-ink);
        min-height:2.65rem;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color:#60A5FA;
        box-shadow:0 0 0 3px rgba(37,99,235,.10);
    }

    /* ---------- Investigation ---------- */
    .cl-investigation {
        background:#FFFFFF;
        border:1px solid var(--cl-border);
        border-radius:12px;
        padding:.95rem 1.05rem;
        margin:.85rem 0;
        box-shadow:0 1px 2px rgba(15,23,42,.02);
    }

    .cl-investigation-tag {
        font-size:.57rem;
        font-weight:800;
        letter-spacing:.10em;
        text-transform:uppercase;
        color:var(--cl-blue);
    }

    .cl-investigation-question {
        font-size:.91rem;
        font-weight:700;
        line-height:1.4;
        color:var(--cl-ink);
        margin-top:.24rem;
    }

    .cl-finding {
        border-left:3px solid #93C5FD;
        background:#F8FAFC;
        border-radius:0 8px 8px 0;
        padding:.75rem .85rem;
        margin:.65rem 0;
        font-size:.80rem;
        line-height:1.55;
    }

    /* ---------- Governance ---------- */
    .cl-gov-good {
        background:var(--cl-green-soft);
        border-left:3px solid #22C55E;
        padding:.58rem .78rem;
        border-radius:0 7px 7px 0;
        font-size:.74rem;
        color:#166534;
        margin-top:.4rem;
        line-height:1.45;
    }

    .cl-gov-bad {
        background:var(--cl-red-soft);
        border-left:3px solid #EF4444;
        padding:.58rem .78rem;
        border-radius:0 7px 7px 0;
        font-size:.74rem;
        color:#991B1B;
        margin-top:.4rem;
        line-height:1.45;
    }

    .cl-gov-badge {
        display:inline-block;
        font-size:.57rem;
        color:#166534;
        background:#F0FDF4;
        border:1px solid #BBF7D0;
        border-radius:999px;
        padding:4px 8px;
        margin:.2rem .25rem .2rem 0;
        font-weight:650;
    }

    .cl-footer {
        text-align:center;
        color:#94A3B8;
        font-size:.60rem;
        border-top:1px solid var(--cl-border);
        margin-top:2.2rem;
        padding:1rem;
        line-height:1.6;
    }

    @media (max-width:900px) {
        .block-container { padding-top:.75rem; }
        .cl-header { align-items:flex-start; }
        .cl-live { font-size:.54rem; }
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
    <div class="cl-header">
      <div class="cl-brand">
        <div class="cl-mark">
          <div class="cl-node cl-n1"></div><div class="cl-node cl-n2"></div>
          <div class="cl-node cl-n3"></div><div class="cl-node cl-n4"></div>
          <div class="cl-link cl-l1"></div><div class="cl-link cl-l2"></div>
          <div class="cl-link cl-l3"></div><div class="cl-link cl-l4"></div>
        </div>
        <div>
          <div class="cl-eyebrow">CHAINLOOM · SUPPLY CHAIN INTELLIGENCE</div>
          <div class="cl-title">Control Tower</div>
          <div class="cl-subtitle">Governed executive intelligence across the supply chain</div>
        </div>
      </div>
      <div class="cl-live">● LIVE SNOWFLAKE DATA</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Executive signals
# ============================================================

st.markdown(
    """
    <div class="cl-section">
      <div class="cl-section-kicker">EXECUTIVE SIGNALS</div>
      <div class="cl-section-title">Network health at a glance</div>
      <div class="cl-section-sub">Current indicators from governed ChainLoom data</div>
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
# Priority attention + product risk
# ============================================================

render_priority_attention(risk_df)
render_product_risk_panel(risk_df)


# ============================================================
# Network pulse
# ============================================================

st.markdown(
    """
    <div class="cl-section">
      <div class="cl-section-kicker">NETWORK PULSE</div>
      <div class="cl-section-title">Current network posture</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="cl-surface cl-pulse">
      <div class="cl-pulse-main">
        <b>{products}</b> monitored &nbsp;·&nbsp;
        <b>{high_risk}</b> high-risk &nbsp;·&nbsp;
        <b>{watchlist}</b> watchlist &nbsp;·&nbsp;
        <b>{healthy}</b> healthy
      </div>
      <div class="cl-refresh">Refreshed {refresh_ts}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Ask ChainLoom
# ============================================================

st.markdown(
    """
    <div class="cl-ai">
      <div class="cl-ai-kicker">AI-ASSISTED INVESTIGATION</div>
      <div class="cl-ai-title">Ask ChainLoom</div>
      <div class="cl-ai-sub">Explore governed supply-chain intelligence using natural language.</div>
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
    st.session_state["analyst_input"] = text


suggestions = [
    "Which products currently show multiple risk signals?",
    "Which carriers have the lowest on-time delivery?",
    "Which parts are below safety stock?",
    "Which suppliers have the highest defect rate?",
]

st.caption("Suggested investigations")

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

ask_col, clear_col = st.columns([1, 5])
with ask_col:
    ask = st.button("Investigate", type="primary", key="investigate_button", use_container_width=True)
with clear_col:
    st.caption("Responses are grounded in the ChainLoom semantic view and governed analytical surfaces.")

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
                    {"question": clean_question, "parsed": parsed, "df": df_result}
                )
            except Exception as exc:
                st.error(f"Cortex Analyst error: {exc}")


# ============================================================
# Investigation results
# ============================================================

if st.session_state["analyst_results"]:
    st.markdown(
        """
        <div class="cl-section">
          <div class="cl-section-kicker">INVESTIGATION</div>
          <div class="cl-section-title">Your governed investigation</div>
          <div class="cl-section-sub">Questions, findings and generated SQL from Cortex Analyst</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for entry in reversed(st.session_state["analyst_results"]):
    parsed = entry["parsed"]

    st.markdown(
        f"""
        <div class="cl-investigation">
          <div class="cl-investigation-tag">ASK CHAINLOOM · INVESTIGATION</div>
          <div class="cl-investigation-question">{entry["question"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if parsed["text"]:
        st.markdown(
            f'<div class="cl-finding"><b>Finding</b><br>{parsed["text"]}</div>',
            unsafe_allow_html=True,
        )

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

    with st.expander("View governance metadata"):
        st.markdown(
            f"**Semantic View:** `{SEMANTIC_VIEW}`  \n"
            f"**Request ID:** `{parsed.get('request_id','')}`  \n"
            "Results are generated through the governed ChainLoom semantic layer."
        )


# ============================================================
# Trust & governance
# ============================================================

st.markdown(
    """
    <div class="cl-section">
      <div class="cl-section-kicker">TRUST &amp; GOVERNANCE</div>
      <div class="cl-section-title">Make the analytical boundary visible</div>
      <div class="cl-section-sub">ChainLoom distinguishes what the data can establish from what it cannot.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
        "label": "Can multiple risk signals be combined safely?",
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
            <div class="cl-surface" style="min-height:112px;">
              <div style="font-size:.55rem;font-weight:800;letter-spacing:.08em;color:#2563EB;">
                {ch["badge"]}
              </div>
              <div style="font-size:.78rem;font-weight:700;color:#334155;margin-top:.38rem;line-height:1.35;">
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
                        f'<div class="cl-gov-good"><b>What the data can establish:</b> {ch["can"]}</div>'
                        f'<div class="cl-gov-bad"><b>What the data cannot establish:</b> {ch["cannot"]}</div>',
                        unsafe_allow_html=True,
                    )

                    if parsed.get("request_id"):
                        st.caption(f"Request ID: {parsed['request_id']}")
                except Exception as exc:
                    st.error(f"Cortex Analyst error: {exc}")


st.markdown(
    """
    <div style="margin-top:.75rem;">
      <span class="cl-gov-badge">✓ Snowflake Semantic View</span>
      <span class="cl-gov-badge">✓ Verified Query Repository</span>
      <span class="cl-gov-badge">✓ Independent Analytical Surfaces</span>
      <span class="cl-gov-badge">✓ No Unsupported Fact-to-Fact Joins</span>
      <span class="cl-gov-badge">✓ No Unsupported Causal Inference</span>
      <span class="cl-gov-badge">✓ Semi-Additive Inventory Handling</span>
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
    f"""
    <div class="cl-footer">
      ChainLoom · Snowflake-Native Supply Chain Intelligence<br>
      Semantic View: {SEMANTIC_VIEW} · Refreshed: {refresh_ts}
    </div>
    """,
    unsafe_allow_html=True,
)
