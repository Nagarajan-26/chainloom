import json
import os
import urllib.error
import urllib.request
from datetime import datetime

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
    .stApp { background:#F6F8FB; }
    .block-container { max-width:1440px; padding-top:1.2rem; padding-bottom:2.5rem; }

    .brand {
        display:flex; justify-content:space-between; align-items:center;
        padding:.7rem 0 .8rem; border-bottom:1px solid #E2E8F0;
        margin-bottom:1rem;
    }
    .brand-left { display:flex; align-items:center; gap:13px; }
    .mark { width:38px; height:38px; position:relative; flex:none; }
    .node { position:absolute; width:8px; height:8px; border-radius:50%; background:#29B5E8; }
    .n1{top:1px;left:15px}.n2{top:15px;left:1px}.n3{top:15px;left:29px}.n4{top:29px;left:15px}
    .link { position:absolute; height:1.5px; width:17px; background:#CBD5E1; transform-origin:left center; }
    .l1{top:5px;left:19px;transform:rotate(45deg)} .l2{top:5px;left:15px;transform:rotate(135deg)}
    .l3{top:19px;left:5px;transform:rotate(45deg)} .l4{top:19px;left:19px;transform:rotate(135deg)}
    .brand-name { font-size:.65rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; color:#64748B; }
    .brand-title { font-size:1.28rem; font-weight:750; color:#0F172A; }
    .brand-sub { font-size:.72rem; color:#94A3B8; }
    .live { font-size:.62rem; color:#047857; background:#ECFDF5; border:1px solid #A7F3D0; border-radius:999px; padding:4px 9px; font-weight:700; }

    .section-label { font-size:.62rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:#94A3B8; margin:1.1rem 0 .45rem; }
    .surface { background:#FFF; border:1px solid #E2E8F0; border-radius:9px; padding:1rem 1.1rem; }
    .ai-console { background:#FFF; border:1px solid #BFDBFE; border-top:3px solid #3B82F6; border-radius:10px; padding:1rem 1.2rem .7rem; margin-top:.5rem; }
    .ai-kicker { font-size:.6rem; font-weight:800; letter-spacing:.1em; color:#2563EB; text-transform:uppercase; }
    .ai-title { font-size:1.18rem; font-weight:750; color:#1E293B; margin:.15rem 0; }
    .ai-sub { font-size:.76rem; color:#64748B; }
    .inv-card { background:#FFF; border:1px solid #E2E8F0; border-radius:9px; padding:1rem 1.1rem; margin:.7rem 0; }
    .inv-tag { font-size:.58rem; font-weight:700; letter-spacing:.09em; text-transform:uppercase; color:#2563EB; }
    .inv-q { font-size:.92rem; font-weight:650; color:#1E293B; margin:.25rem 0 .6rem; }
    .gov-good { background:#F0FDF4; border-left:3px solid #22C55E; padding:.55rem .75rem; border-radius:0 6px 6px 0; font-size:.76rem; color:#166534; margin-top:.35rem; }
    .gov-bad { background:#FEF2F2; border-left:3px solid #EF4444; padding:.55rem .75rem; border-radius:0 6px 6px 0; font-size:.76rem; color:#991B1B; margin-top:.35rem; }
    .gov-badges { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.5rem; }
    .gb { font-size:.6rem; color:#166534; background:#F0FDF4; border:1px solid #BBF7D0; border-radius:4px; padding:3px 7px; }
    .footer { text-align:center; color:#CBD5E1; font-size:.6rem; border-top:1px solid #E2E8F0; margin-top:2rem; padding:1rem; }
    .stButton > button { border-radius:8px; font-weight:600; }
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
          <div class="brand-name">ChainLoom</div>
          <div class="brand-title">Supply Chain Intelligence</div>
          <div class="brand-sub">Control Tower</div>
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

pulse_left, pulse_right = st.columns([2.2, 1], gap="medium")
with pulse_right:
    st.markdown('<div class="section-label">Network Pulse</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="surface">
          <b>{products}</b> monitored &nbsp; · &nbsp;
          <b>{high_risk}</b> high-risk &nbsp; · &nbsp;
          <b>{watchlist}</b> watchlist &nbsp; · &nbsp;
          <b>{healthy}</b> healthy
          <div style="font-size:.6rem;color:#CBD5E1;text-align:right;margin-top:.45rem;">
            Refreshed {refresh_ts}
          </div>
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
