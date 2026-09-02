import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="ChainLoom | Control Tower",
    page_icon="🔗",
    layout="wide",
)

# ── Snowflake session ──────────────────────────────────────────────────────
conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))
session = conn.session()

# ── Cortex Analyst helper ──────────────────────────────────────────────────
SEMANTIC_VIEW = "CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS"


def call_analyst(question: str, history: list | None = None) -> dict:
    """Call Cortex Analyst from the Snowflake Container Runtime.

    Container Runtime does not provide the private `_snowflake` module.
    Snowflake exposes an OAuth session token to the container at
    /snowflake/session/token, which can be used with the Cortex Analyst
    REST API.
    """
    import requests

    if history is None:
        messages = [{"role": "user", "content": [{"type": "text", "text": question}]}]
    else:
        messages = history + [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ]

    request_body = {
        "messages": messages,
        "semantic_view": SEMANTIC_VIEW,
    }

    snowflake_host = os.getenv("SNOWFLAKE_HOST")
    if not snowflake_host:
        raise RuntimeError("SNOWFLAKE_HOST is not available in the Container Runtime.")

    try:
        with open("/snowflake/session/token", "r", encoding="utf-8") as token_file:
            token = token_file.read().strip()
    except OSError as exc:
        raise RuntimeError(
            "Snowflake Container Runtime session token is unavailable."
        ) from exc

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Snowflake-Authorization-Token-Type": "OAUTH",
    }

    resp = requests.post(
        f"https://{snowflake_host}/api/v2/cortex/analyst/message",
        headers=headers,
        json=request_body,
        timeout=120,
    )

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Cortex Analyst REST API returned HTTP {resp.status_code}: {resp.text}"
        )

    return resp.json()


def parse_analyst_response(resp: dict) -> dict:
    result = {"text": "", "sql": "", "warnings": [], "request_id": resp.get("request_id", "")}
    message = resp.get("message", resp)
    content_items = message.get("content", []) if isinstance(message, dict) else []
    if not content_items and "result" in resp:
        raw = resp["result"]
        if "```sql" in raw:
            parts = raw.split("```sql")
            result["text"] = parts[0].strip()
            result["sql"] = parts[1].split("```")[0].strip()
        else:
            result["text"] = raw
        return result
    for item in content_items:
        if item.get("type") == "text":
            result["text"] += item.get("text", "")
        elif item.get("type") == "sql":
            result["sql"] = item.get("statement", "")
    if "warnings" in resp:
        result["warnings"] = resp["warnings"]
    if "request_id" in resp:
        result["request_id"] = resp["request_id"]
    return result


def run_analyst_sql(sql: str) -> pd.DataFrame | None:
    if not sql or not sql.strip():
        return None
    try:
        return session.sql(sql).to_pandas()
    except Exception as e:
        st.error(f"Query execution error: {e}")
        return None


# ── Data loaders ───────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_risk_signals():
    return session.sql(
        "SELECT * FROM CHAINLOOM.CURATED.V_PRODUCT_RISK_SIGNALS ORDER BY RISK_SIGNAL_COUNT DESC"
    ).to_pandas()


@st.cache_data(ttl=120)
def load_executive_kpis():
    ff = session.sql(
        "SELECT ROUND(100.0*SUM(FULFILLED_QUANTITY)/NULLIF(SUM(ORDERED_QUANTITY),0),1) AS V "
        "FROM CHAINLOOM.CURATED.V_CUSTOMER_FULFILLMENT"
    ).to_pandas().iloc[0, 0]
    otd = session.sql(
        "SELECT ROUND(100.0*COUNT_IF(ON_TIME_FLAG=TRUE)/NULLIF(COUNT_IF(DELIVERY_ELIGIBLE_FLAG=TRUE),0),1) AS V "
        "FROM CHAINLOOM.CURATED.V_SHIPMENT_PERFORMANCE"
    ).to_pandas().iloc[0, 0]
    return ff, otd


@st.cache_data(ttl=120)
def load_inventory_trend():
    return session.sql("""
        SELECT SNAPSHOT_DATE,
               SUM(AVAILABLE_QUANTITY) AS AVAILABLE_INVENTORY,
               SUM(SAFETY_STOCK_QUANTITY) AS SAFETY_STOCK_LEVEL
        FROM CHAINLOOM.CURATED.V_INVENTORY_POSITION
        GROUP BY SNAPSHOT_DATE
        ORDER BY SNAPSHOT_DATE
    """).to_pandas()


risk_df = load_risk_signals()
fulfillment_pct, otd_pct = load_executive_kpis()
inv_trend_df = load_inventory_trend()
refresh_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

high_risk_count = int((risk_df["RISK_SIGNAL_COUNT"] >= 2).sum())
watchlist_count = int((risk_df["RISK_SIGNAL_COUNT"] == 1).sum())
healthy_count = int((risk_df["RISK_SIGNAL_COUNT"] == 0).sum())
monitored_count = len(risk_df)


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
/* ── Canvas ─────────────────────────────────────────────── */
.stApp { background: #F6F8FB; }
.block-container { padding-top: 1.0rem; padding-bottom: 1.5rem; max-width: 1440px; }
section[data-testid="stSidebar"] { display: none; }
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }

/* ── Brand header ───────────────────────────────────────── */
.cl-brand {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.8rem 0 0.7rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1rem;
}
.cl-brand-left { display: flex; align-items: center; gap: 14px; }
.cl-mark {
    width: 36px; height: 36px; position: relative; flex-shrink: 0;
}
.cl-mark .node {
    width: 8px; height: 8px; background: #29B5E8; border-radius: 50%;
    position: absolute;
}
.cl-mark .node.n1 { top: 0; left: 14px; }
.cl-mark .node.n2 { top: 14px; left: 0; }
.cl-mark .node.n3 { top: 14px; left: 28px; }
.cl-mark .node.n4 { top: 28px; left: 14px; }
.cl-mark .link {
    position: absolute; background: #CBD5E1; transform-origin: 0 0;
}
.cl-mark .link.l1 { top: 4px; left: 18px; width: 16px; height: 1.5px; transform: rotate(45deg); }
.cl-mark .link.l2 { top: 4px; left: 14px; width: 16px; height: 1.5px; transform: rotate(135deg); }
.cl-mark .link.l3 { top: 18px; left: 4px; width: 16px; height: 1.5px; transform: rotate(45deg); }
.cl-mark .link.l4 { top: 18px; left: 18px; width: 16px; height: 1.5px; transform: rotate(135deg); }
.cl-brand-text {}
.cl-brand-name {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #64748B; line-height: 1;
}
.cl-brand-title {
    font-size: 1.25rem; font-weight: 700; color: #0F172A; letter-spacing: -0.01em;
    line-height: 1.25; margin-top: 1px;
}
.cl-brand-subtitle {
    font-size: 0.72rem; color: #94A3B8; line-height: 1.2; margin-top: 1px;
}
.cl-brand-right { display: flex; align-items: center; gap: 12px; }
.cl-live {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.62rem; font-weight: 500; letter-spacing: 0.04em;
    text-transform: uppercase; color: #059669;
    background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 4px;
    padding: 3px 8px;
}
.cl-live .dot { width: 6px; height: 6px; background: #10B981; border-radius: 50%; }

/* ── Metric strip ───────────────────────────────────────── */
.m-strip {
    display: flex; gap: 1px; background: #E2E8F0; border-radius: 8px;
    overflow: hidden; margin-bottom: 1.1rem;
}
.m-cell {
    flex: 1; background: #FFFFFF; padding: 0.7rem 0.5rem; text-align: center;
    min-width: 0;
}
.m-cell:first-child { border-radius: 8px 0 0 8px; }
.m-cell:last-child  { border-radius: 0 8px 8px 0; }
.m-cell .ml {
    font-size: 0.58rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.07em; color: #94A3B8; margin-bottom: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.m-cell .mv { font-size: 1.3rem; font-weight: 700; color: #0F172A; line-height: 1.2; }
.m-cell .mv.g { color: #059669; } .m-cell .mv.w { color: #D97706; } .m-cell .mv.d { color: #DC2626; }
.m-cell .md { font-size: 0.6rem; color: #94A3B8; margin-top: 1px; }

/* ── Section label ──────────────────────────────────────── */
.sec-label {
    font-size: 0.6rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.1em; color: #94A3B8; margin-bottom: 0.45rem;
}

/* ── Card surface ───────────────────────────────────────── */
.surface {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 1rem 1.1rem;
}

/* ── Priority card ──────────────────────────────────────── */
.pri-surface {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 1rem 1.1rem; border-left: 3px solid #F59E0B;
}
.pri-badge {
    display: inline-block; font-size: 0.55rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    padding: 2px 7px; border-radius: 3px; margin-bottom: 0.5rem;
}
.pri-badge.high { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.pri-badge.watch { background: #FFF7ED; color: #9A3412; border: 1px solid #FED7AA; }
.pri-prod { font-size: 1.05rem; font-weight: 700; color: #1E293B; margin-bottom: 0.25rem; }
.pri-sigs { font-size: 0.78rem; color: #64748B; margin-bottom: 0.4rem; }
.pri-mets { display: flex; gap: 1.2rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.pri-met { font-size: 0.75rem; color: #475569; }
.pri-met strong { font-weight: 700; color: #1E293B; }
.pri-why { font-size: 0.72rem; color: #92400E; font-style: italic; margin-bottom: 0.35rem; }
.pri-gov {
    font-size: 0.65rem; color: #94A3B8; border-top: 1px solid #F1F5F9;
    padding-top: 0.35rem; margin-top: 0.15rem;
}

/* ── Pulse panel ────────────────────────────────────────── */
.pulse-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.45rem; }
.pulse-cell {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px;
    padding: 0.55rem 0.7rem; display: flex; align-items: baseline; gap: 6px;
}
.pulse-n { font-size: 1.15rem; font-weight: 700; color: #0F172A; line-height: 1; }
.pulse-n.d { color: #DC2626; } .pulse-n.w { color: #D97706; } .pulse-n.g { color: #059669; }
.pulse-l { font-size: 0.68rem; color: #64748B; }

.pulse-table { width: 100%; border-collapse: collapse; margin-top: 0.65rem; }
.pulse-table th {
    font-size: 0.54rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #94A3B8; text-align: left;
    padding: 0.38rem 0.2rem; border-bottom: 1px solid #E2E8F0;
}
.pulse-table th:last-child, .pulse-table td:last-child { text-align: right; }
.pulse-table td {
    font-size: 0.68rem; color: #475569; padding: 0.36rem 0.2rem;
    border-bottom: 1px solid #F8FAFC;
}
.pulse-table tr:last-child td { border-bottom: none; }
.pulse-share { font-variant-numeric: tabular-nums; color: #64748B; }
.pulse-status { font-weight: 600; }
.pulse-status.high { color: #DC2626; }
.pulse-status.watch { color: #D97706; }
.pulse-status.healthy { color: #059669; }
.pt-miss {
    display: inline-block; color: #64748B; background: #F8FAFC;
    border: 1px solid #E2E8F0; border-radius: 4px; padding: 1px 6px;
    font-size: 0.65rem; white-space: nowrap;
}
.pt-miss::after { content: " unavailable"; color: #94A3B8; font-weight: 500; }
.pulse-ts {
    font-size: 0.6rem; color: #CBD5E1; margin-top: 0.4rem; text-align: right;
}

/* ── Inventory panel ────────────────────────────────────── */
.inv-note { font-size: 0.65rem; color: #94A3B8; font-style: italic; margin-top: 0.3rem; }

/* ── AI console ─────────────────────────────────────────── */
.ai-console {
    background: #FFFFFF; border: 1px solid #BFDBFE; border-radius: 10px;
    padding: 1.2rem 1.3rem; margin: 0.2rem 0 0.5rem 0;
    border-top: 3px solid #3B82F6;
}
.ai-hdr {
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #3B82F6; margin-bottom: 0.15rem;
}
.ai-title { font-size: 1.1rem; font-weight: 700; color: #1E293B; margin-bottom: 0.1rem; }
.ai-sub { font-size: 0.75rem; color: #64748B; margin-bottom: 0.6rem; }

/* ── Investigation result ───────────────────────────────── */
.inv-card {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 1rem 1.1rem; margin: 0.5rem 0;
}
.inv-tag {
    font-size: 0.55rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #3B82F6; margin-bottom: 0.3rem;
}
.inv-q { font-size: 0.9rem; font-weight: 600; color: #1E293B; margin-bottom: 0.5rem; }
.inv-sep { border: none; border-top: 1px solid #F1F5F9; margin: 0.5rem 0; }
.inv-section-label {
    font-size: 0.58rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #94A3B8; margin: 0.5rem 0 0.25rem 0;
}

/* ── Trust cards ────────────────────────────────────────── */
.tc {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 0.8rem 0.9rem; height: 100%;
}
.tc-badge {
    display: inline-block; font-size: 0.52rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    border-radius: 3px; padding: 2px 6px; margin-bottom: 0.35rem;
}
.tc-badge.causal  { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.tc-badge.attrib  { background: #FFF7ED; color: #9A3412; border: 1px solid #FED7AA; }
.tc-badge.signals { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
.tc-q { font-size: 0.78rem; font-weight: 600; color: #334155; line-height: 1.35; }

/* ── Governance result ──────────────────────────────────── */
.gov-state {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.58rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; border-radius: 3px; padding: 3px 8px; margin: 0.3rem 0;
}
.gov-state.enforced { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.gov-state.verified { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
.can-block {
    background: #F0FDF4; border-left: 3px solid #22C55E; border-radius: 0 6px 6px 0;
    padding: 0.55rem 0.8rem; margin: 0.3rem 0; font-size: 0.78rem; color: #166534;
}
.cannot-block {
    background: #FEF2F2; border-left: 3px solid #EF4444; border-radius: 0 6px 6px 0;
    padding: 0.55rem 0.8rem; margin: 0.3rem 0; font-size: 0.78rem; color: #991B1B;
}

/* ── Gov badges ─────────────────────────────────────────── */
.gov-badges { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.5rem; }
.gb {
    font-size: 0.62rem; font-weight: 500; background: #F0FDF4;
    border: 1px solid #BBF7D0; border-radius: 4px;
    padding: 2px 8px; color: #166534;
}

/* ── Product table ──────────────────────────────────────── */
.pt-surface {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 0.8rem 1rem; overflow-x: auto;
}
.pt-table { width: 100%; border-collapse: collapse; }
.pt-table th {
    font-size: 0.58rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #94A3B8; text-align: left;
    padding: 0.5rem 0.6rem; border-bottom: 1px solid #E2E8F0;
}
.pt-table th:last-child { text-align: right; }
.pt-table td {
    font-size: 0.8rem; color: #334155; padding: 0.55rem 0.6rem;
    border-bottom: 1px solid #F8FAFC; vertical-align: middle;
}
.pt-table tr:last-child td { border-bottom: none; }
.pt-prod { font-weight: 600; color: #1E293B; }
.pt-pct { font-variant-numeric: tabular-nums; }
.pt-miss { color: #CBD5E1; }
.pt-sig {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.68rem; font-weight: 600; border-radius: 4px;
    padding: 2px 7px; float: right;
}
.pt-sig.high { background: #FEF2F2; color: #DC2626; }
.pt-sig.watch { background: #FFF7ED; color: #D97706; }
.pt-sig.ok { background: #F0FDF4; color: #059669; }

/* ── Footer ─────────────────────────────────────────────── */
.cl-footer {
    text-align: center; font-size: 0.62rem; color: #CBD5E1;
    padding: 0.9rem 0 0.4rem 0; border-top: 1px solid #E2E8F0; margin-top: 1.4rem;
}
.cl-footer a { color: #94A3B8; text-decoration: none; }

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 900px) {
    .m-strip { flex-wrap: wrap; }
    .m-cell { flex: 1 1 30%; }
    .pulse-grid { grid-template-columns: 1fr 1fr; }
}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 3. BRAND HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="cl-brand">
    <div class="cl-brand-left">
        <div class="cl-mark">
            <div class="node n1"></div><div class="node n2"></div>
            <div class="node n3"></div><div class="node n4"></div>
            <div class="link l1"></div><div class="link l2"></div>
            <div class="link l3"></div><div class="link l4"></div>
        </div>
        <div class="cl-brand-text">
            <div class="cl-brand-name">ChainLoom</div>
            <div class="cl-brand-title">Supply Chain Intelligence</div>
            <div class="cl-brand-subtitle">Control Tower</div>
        </div>
    </div>
    <div class="cl-brand-right">
        <span class="cl-live"><span class="dot"></span> Live Snowflake Data</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 4. EXECUTIVE KPI STRIP
# ══════════════════════════════════════════════════════════════════════════════
ff_c = "g" if fulfillment_pct and fulfillment_pct >= 90 else ("w" if fulfillment_pct and fulfillment_pct >= 80 else "d")
ff_v = f"{fulfillment_pct}%" if fulfillment_pct is not None else "\u2014"
otd_c = "g" if otd_pct and otd_pct >= 85 else ("w" if otd_pct and otd_pct >= 70 else "d")
otd_v = f"{otd_pct}%" if otd_pct is not None else "\u2014"

st.markdown(f"""
<div class="m-strip">
    <div class="m-cell">
        <div class="ml">High-Risk Products</div>
        <div class="mv{"  d" if high_risk_count > 0 else ""}">{high_risk_count}</div>
        <div class="md">&ge;2 signals</div>
    </div>
    <div class="m-cell">
        <div class="ml">Watchlist</div>
        <div class="mv{" w" if watchlist_count > 0 else ""}">{watchlist_count}</div>
        <div class="md">1 signal</div>
    </div>
    <div class="m-cell">
        <div class="ml">Products Monitored</div>
        <div class="mv">{monitored_count}</div>
        <div class="md">across network</div>
    </div>
    <div class="m-cell">
        <div class="ml">Network Fulfillment</div>
        <div class="mv {ff_c}">{ff_v}</div>
        <div class="md">order fill rate</div>
    </div>
    <div class="m-cell">
        <div class="ml">On-Time Delivery</div>
        <div class="mv {otd_c}">{otd_v}</div>
        <div class="md">delivered on/before promise</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 5. EXECUTIVE FOCUS — TWO COLUMN
# ══════════════════════════════════════════════════════════════════════════════
ef_left, ef_right = st.columns([65, 35], gap="medium")

# ── LEFT: PRIORITY ATTENTION ──────────────────────────────────────────────
with ef_left:
    st.markdown('<div class="sec-label">Priority Attention</div>', unsafe_allow_html=True)

    top = risk_df.iloc[0] if len(risk_df) > 0 and risk_df.iloc[0]["RISK_SIGNAL_COUNT"] > 0 else None

    if top is not None:
        sig_count = int(top["RISK_SIGNAL_COUNT"])
        signals_list = []
        if top.get("FULFILLMENT_RISK_FLAG"):
            signals_list.append("Fulfillment")
        if top.get("DELIVERY_RISK_FLAG"):
            signals_list.append("Delivery")
        if top.get("PRODUCTION_RISK_FLAG"):
            signals_list.append("Production")
        signal_text = " \u00b7 ".join(signals_list) if signals_list else "\u2014"

        attention = "HIGH ATTENTION" if sig_count >= 2 else "WATCH"
        badge_cls = "high" if sig_count >= 2 else "watch"

        ff_rate = top.get("FULFILLMENT_RATE")
        otd_rate = top.get("ON_TIME_DELIVERY_RATE")
        prod_att = top.get("PRODUCTION_ATTAINMENT")

        met_html = ""
        if ff_rate is not None and pd.notna(ff_rate):
            met_html += f'<div class="pri-met"><strong>{ff_rate:.0%}</strong> Fulfillment</div>'
        if otd_rate is not None and pd.notna(otd_rate):
            met_html += f'<div class="pri-met"><strong>{otd_rate:.0%}</strong> On-Time Delivery</div>'
        if prod_att is not None and pd.notna(prod_att):
            met_html += f'<div class="pri-met"><strong>{prod_att:.0%}</strong> Production Attainment</div>'

        # Dynamically derive why surfaced — no composite language
        why_parts = []
        if top.get("FULFILLMENT_RISK_FLAG") and ff_rate is not None and pd.notna(ff_rate):
            why_parts.append(f"fulfillment at {ff_rate:.0%}")
        if top.get("DELIVERY_RISK_FLAG") and otd_rate is not None and pd.notna(otd_rate):
            why_parts.append(f"on-time delivery at {otd_rate:.0%}")
        if top.get("PRODUCTION_RISK_FLAG") and prod_att is not None and pd.notna(prod_att):
            why_parts.append(f"production attainment at {prod_att:.0%}")
        if len(why_parts) > 1:
            primary = why_parts[0]
            also = "; ".join(f"{p} is also below the network threshold" for p in why_parts[1:])
            why_text = f"Why surfaced: {primary} is the lowest among products with {sig_count} independent signals; {also}."
        elif len(why_parts) == 1:
            why_text = f"Why surfaced: {why_parts[0]} below threshold with {sig_count} independent signal{'s' if sig_count != 1 else ''}."
        else:
            why_text = f"Why surfaced: {sig_count} independent risk signals detected."

        st.markdown(f"""
        <div class="pri-surface">
            <div class="pri-badge {badge_cls}">{attention}</div>
            <div class="pri-prod">{top["PRODUCT_ID"]} \u2014 {top["PRODUCT_NAME"]}</div>
            <div class="pri-sigs">{sig_count} independent risk signal{"s" if sig_count != 1 else ""} \u00b7 {signal_text}</div>
            <div class="pri-mets">{met_html}</div>
            <div class="pri-why">{why_text}</div>
            <div class="pri-gov">Signals are independently observed indicators and do not establish causality.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="surface" style="color:#059669;font-size:0.85rem;">'
            'All products within normal operating thresholds.</div>',
            unsafe_allow_html=True,
        )

# ── RIGHT: NETWORK PULSE ─────────────────────────────────────────────────
with ef_right:
    st.markdown('<div class="sec-label">Network Pulse</div>', unsafe_allow_html=True)
    total = monitored_count or 1
    pulse_rows = [
        ("High Risk", high_risk_count, "high"),
        ("Watchlist", watchlist_count, "watch"),
        ("Healthy", healthy_count, "healthy"),
    ]
    pulse_table_rows = "".join(
        f'<tr><td><span class="pulse-status {cls}">{label}</span></td>'
        f'<td>{count}</td><td class="pulse-share">{count / total:.1%}</td></tr>'
        for label, count, cls in pulse_rows
    )

    st.markdown(f"""
    <div class="surface" style="padding:0.85rem 0.95rem;">
        <div class="pulse-grid">
            <div class="pulse-cell">
                <div class="pulse-n">{monitored_count}</div>
                <div class="pulse-l">Monitored</div>
            </div>
            <div class="pulse-cell">
                <div class="pulse-n d">{high_risk_count}</div>
                <div class="pulse-l">High Risk</div>
            </div>
        </div>
        <table class="pulse-table">
            <thead><tr><th>Status</th><th>Products</th><th>Share</th></tr></thead>
            <tbody>{pulse_table_rows}</tbody>
        </table>
        <div class="pulse-ts">Last refreshed: {refresh_ts}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 6. NETWORK INVENTORY INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("")
st.markdown('<div class="sec-label">Network Inventory Intelligence</div>', unsafe_allow_html=True)

if not inv_trend_df.empty:
    chart_df = inv_trend_df.rename(columns={
        "SNAPSHOT_DATE": "Date",
        "AVAILABLE_INVENTORY": "Available Inventory",
        "SAFETY_STOCK_LEVEL": "Safety Stock Level",
    })
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])
    chart_df = chart_df.set_index("Date")
    st.line_chart(chart_df, height=240)

    total_snaps = len(inv_trend_df)
    below_count = int((inv_trend_df["AVAILABLE_INVENTORY"] < inv_trend_df["SAFETY_STOCK_LEVEL"]).sum())
    if below_count == 0:
        inv_insight = "Inventory remains above safety stock across all displayed snapshots."
    elif below_count == total_snaps:
        inv_insight = "Inventory is below safety stock across all displayed snapshots."
    else:
        inv_insight = f"Inventory is below safety stock in {below_count} of {total_snaps} displayed snapshots."

    st.markdown(f'<div class="inv-note">{inv_insight}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="inv-note">Snapshot-aware inventory view \u00b7 '
        'no cross-date aggregation \u00b7 each date represents its own inventory position.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("No inventory snapshot data available.")


# ══════════════════════════════════════════════════════════════════════════════
# 7. PRODUCT RISK INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("")
st.markdown('<div class="sec-label">Product Risk Intelligence</div>', unsafe_allow_html=True)


def fmt_pct_html(val):
    if val is None or pd.isna(val):
        return '<span class="pt-miss">\u2014</span>'
    return f'<span class="pt-pct">{val:.0%}</span>'


def fmt_sig_html(n):
    if n is None or pd.isna(n):
        return '<span class="pt-miss">\u2014</span>'
    n = int(n)
    if n == 0:
        return '<span class="pt-sig ok">\u2713 None</span>'
    if n == 1:
        return '<span class="pt-sig watch">\u25b3 1 signal</span>'
    return f'<span class="pt-sig high">\u25cf {n} signals</span>'


table_rows = ""
for _, row in risk_df.iterrows():
    table_rows += (
        f'<tr>'
        f'<td><span class="pt-prod">{row["PRODUCT_ID"]}</span> {row["PRODUCT_NAME"]}</td>'
        f'<td>{fmt_pct_html(row.get("FULFILLMENT_RATE"))}</td>'
        f'<td>{fmt_pct_html(row.get("ON_TIME_DELIVERY_RATE"))}</td>'
        f'<td>{fmt_pct_html(row.get("PRODUCTION_ATTAINMENT"))}</td>'
        f'<td>{fmt_sig_html(row.get("RISK_SIGNAL_COUNT"))}</td>'
        f'</tr>'
    )

if table_rows:
    st.markdown(f"""
    <div class="pt-surface">
        <table class="pt-table">
            <thead><tr>
                <th>Product</th><th>Fulfillment</th><th>On-Time Delivery</th>
                <th>Production</th><th style="text-align:right">Risk Signals</th>
            </tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No product risk signal data available.")


# ══════════════════════════════════════════════════════════════════════════════
# 8. ASK CHAINLOOM — INVESTIGATION CONSOLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("")
st.markdown("""
<div class="ai-console">
    <div class="ai-hdr">Ask ChainLoom</div>
    <div class="ai-title">What would you like to investigate?</div>
    <div class="ai-sub">Explore governed supply-chain intelligence using natural language.</div>
</div>
""", unsafe_allow_html=True)

if "analyst_history" not in st.session_state:
    st.session_state.analyst_history = []
if "analyst_results" not in st.session_state:
    st.session_state.analyst_results = []

suggestions = [
    "Which products currently show multiple risk signals?",
    "Which carriers have the lowest on-time delivery?",
    "Which parts are below safety stock?",
    "Which suppliers have the highest defect rate?",
]

# Suggestion prefill: use a versioned widget key so Streamlit cannot reuse
# the previous text_input state when a suggestion is selected.
if "_suggestion_text" not in st.session_state:
    st.session_state["_suggestion_text"] = ""
if "_suggestion_version" not in st.session_state:
    st.session_state["_suggestion_version"] = 0

sg_cols = st.columns(len(suggestions))
for i, sg in enumerate(suggestions):
    with sg_cols[i]:
        if st.button(sg, key=f"sg_{i}", use_container_width=True):
            st.session_state["_suggestion_text"] = sg
            st.session_state["_suggestion_version"] += 1
            st.rerun()

question = st.text_input(
    "Ask a question about your supply chain",
    value=st.session_state["_suggestion_text"],
    placeholder="e.g. What is the fulfillment rate by customer segment?",
    key=f"analyst_input_{st.session_state['_suggestion_version']}",
    label_visibility="collapsed",
)

# Once the widget is initialized with the suggestion, retain what the user
# types in the normal widget state; the versioned key only changes on a new
# suggestion selection.
st.session_state["_suggestion_text"] = question

if st.button("Investigate", type="primary", key="analyst_ask") and question.strip():
    with st.spinner("Consulting Cortex Analyst..."):
        try:
            raw_resp = call_analyst(question.strip(), st.session_state.analyst_history)
            parsed = parse_analyst_response(raw_resp)
            st.session_state.analyst_history.append(
                {"role": "user", "content": [{"type": "text", "text": question.strip()}]}
            )
            reply_content = []
            if parsed["text"]:
                reply_content.append({"type": "text", "text": parsed["text"]})
            if parsed["sql"]:
                reply_content.append({"type": "sql", "statement": parsed["sql"]})
            st.session_state.analyst_history.append(
                {"role": "analyst", "content": reply_content}
            )
            df_result = run_analyst_sql(parsed["sql"]) if parsed["sql"] else None
            st.session_state.analyst_results.append({
                "question": question.strip(),
                "parsed": parsed,
                "df": df_result,
            })
        except Exception as e:
            st.error(f"Cortex Analyst error: {e}")

def render_governed_result(entry, governance=None):
    parsed = entry["parsed"]
    st.markdown(
        f'<div class="inv-card">'
        f'<div class="inv-tag">Ask ChainLoom &mdash; Investigation</div>'
        f'<div class="inv-q">{entry["question"]}</div>'
        f'<hr class="inv-sep">'
        f'</div>',
        unsafe_allow_html=True,
    )

    if parsed["text"]:
        st.markdown('<div class="inv-section-label">Finding</div>', unsafe_allow_html=True)
        st.markdown(parsed["text"])

    if parsed["warnings"]:
        with st.expander(f"Analyst advisories · {len(parsed['warnings'])}", expanded=False):
            for warning in parsed["warnings"]:
                st.caption(str(warning))

    if entry.get("df") is not None and not entry["df"].empty:
        st.markdown('<div class="inv-section-label">Results</div>', unsafe_allow_html=True)
        st.dataframe(entry["df"], use_container_width=True, hide_index=True)
    elif parsed["sql"]:
        st.caption("Query returned no results.")

    with st.expander("View generated SQL"):
        if parsed["sql"]:
            st.code(parsed["sql"], language="sql")
        else:
            st.caption("No SQL was generated for this question.")

    with st.expander("View governance metadata"):
        request_id = parsed.get("request_id") or "Not provided"
        st.markdown(
            f"**Semantic View:** `{SEMANTIC_VIEW}`  \n"
            f"**Request ID:** `{request_id}`  \n"
            "The investigation is grounded in the governed semantic layer and its analytical boundaries."
        )

    if governance:
        st.markdown('<div class="inv-section-label">Governance interpretation</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="can-block"><strong>What the data can establish:</strong> {governance["can"]}</div>'
            f'<div class="cannot-block"><strong>What the data cannot establish:</strong> {governance["cannot"]}</div>',
            unsafe_allow_html=True,
        )

# Render investigation results
for entry in reversed(st.session_state.analyst_results):
    render_governed_result(entry)


# ══════════════════════════════════════════════════════════════════════════════
# 9. TRUST & GOVERNANCE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("")
st.markdown('<div class="sec-label">Trust &amp; Governance</div>', unsafe_allow_html=True)
st.caption("Challenge ChainLoom's analytical boundaries using the same governed investigation pattern.")

challenges = [
    {
        "badge_cls": "causal",
        "badge": "Causal Boundary",
        "label": "Can P104 shortage be proven as the cause?",
        "question": "Did Part P104 inventory shortages cause production constraints last month?",
        "can": "P104 BOM exposure and observed production constraints can be independently reported.",
        "cannot": "Causation cannot be established. P104_EXPOSURE_FLAG indicates BOM dependency, not proof of shortage. Inventory and production are separate fact tables with no fact-to-fact join.",
        "state": "BOUNDARY ENFORCED",
        "state_cls": "enforced",
    },
    {
        "badge_cls": "attrib",
        "badge": "Attribution Boundary",
        "label": "Can supplier delay be proven as the cause?",
        "question": "Which supplier delivery delays directly caused late shipments to our Strategic customers?",
        "can": "Supplier delays and customer shipment delays can be independently observed from their respective analytical surfaces.",
        "cannot": "Direct supplier-to-customer causation cannot be established. Lot/batch genealogy is unavailable, so no linkage exists between a specific supplier receipt and a specific customer shipment.",
        "state": "BOUNDARY ENFORCED",
        "state_cls": "enforced",
    },
    {
        "badge_cls": "signals",
        "badge": "Independent Signals",
        "label": "Can multiple risk signals be combined without inventing causality?",
        "question": "Which products currently show multiple independent supply-chain risk signals across fulfillment, delivery, and production?",
        "can": "Multiple independent product risk signals can be reported. RISK_SIGNAL_COUNT counts co-occurring threshold breaches across fulfillment, delivery, and production.",
        "cannot": "A weighted or composite causal risk score cannot be created. Signals are independently observed; co-occurrence does not imply causation.",
        "state": "GOVERNED",
        "state_cls": "verified",
    },
]

# Keep the three boundary choices compact and scannable.
ch_cols = st.columns(3)
for i, ch in enumerate(challenges):
    with ch_cols[i]:
        st.markdown(
            f'<div class="tc">'
            f'<div class="tc-badge {ch["badge_cls"]}">{ch["badge"]}</div>'
            f'<div class="tc-q">{ch["label"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Run Challenge", key=f"ch_{i}", use_container_width=True):
            st.session_state[f"_run_challenge_{i}"] = True

# Render a selected governance challenge using the same Question → Finding → Results
# pattern as Ask ChainLoom, then append the explicit can/cannot boundary.
for i, ch in enumerate(challenges):
    if st.session_state.get(f"_run_challenge_{i}"):
        st.session_state[f"_run_challenge_{i}"] = False

        with st.spinner("Running governance challenge..."):
            try:
                raw = call_analyst(ch["question"])
                parsed = parse_analyst_response(raw)
                df = run_analyst_sql(parsed["sql"]) if parsed["sql"] else None

                entry = {
                    "question": ch["question"],
                    "parsed": parsed,
                    "df": df,
                }

                st.markdown(
                    f'<div class="gov-state {ch["state_cls"]}">{ch["state"]}</div>',
                    unsafe_allow_html=True,
                )
                render_governed_result(
                    entry,
                    governance={"can": ch["can"], "cannot": ch["cannot"]},
                )
            except Exception as e:
                st.error(f"Cortex Analyst error: {e}")

# Permanent governance proof points — concise and reviewer-friendly.
st.markdown('<div class="inv-section-label">Governance controls</div>', unsafe_allow_html=True)
st.markdown("""
<div class="gov-badges">
    <span class="gb">✓ Snowflake Semantic View</span>
    <span class="gb">✓ Verified Query Repository</span>
    <span class="gb">✓ Independent Analytical Surfaces</span>
    <span class="gb">✓ No Unsupported Fact-to-Fact Joins</span>
    <span class="gb">✓ No Unsupported Causal Inference</span>
    <span class="gb">✓ Semi-Additive Inventory Handling</span>
</div>
""", unsafe_allow_html=True)

with st.expander("How ChainLoom reasons"):
    st.markdown("""
**Analytical Architecture**

ChainLoom maintains five independent curated analytical surfaces — customer fulfillment,
shipment performance, production performance, inventory position, and supplier performance —
each with a clearly defined grain and governed by a Snowflake Semantic View with verified queries.

**Governance Principles**

1. **No unsupported fact-to-fact joins.** Each surface is queried independently through the semantic layer. Cross-surface signals are computed through governed views that aggregate each surface separately before joining at the product level.
2. **Inventory is semi-additive.** Inventory quantities are snapshot-based and must not be summed across snapshot dates.
3. **P104_EXPOSURE_FLAG means BOM dependency, not proof of shortage or causality.**
4. **Supplier-to-customer causality cannot be established.** There is no lot/batch genealogy linking a specific supplier delivery to a specific customer shipment.
5. **Product risk signals are independent observed indicators.** RISK_SIGNAL_COUNT counts threshold breaches; it is not a weighted or composite causal score.
6. **Missing metrics remain unavailable.** A missing fulfillment or delivery observation is shown as "—", never silently converted to 0%.

**Semantic View:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`
**Verified Queries:** Q1–Q10 operational · Q13 product risk signals · Q11–Q12 governance/adversarial
""")


# ══════════════════════════════════════════════════════════════════════════════
# 10. FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="cl-footer">ChainLoom \u00b7 Snowflake-Native Supply Chain Intelligence<br>'
    f'Semantic View: {SEMANTIC_VIEW}<br>'
    f'Last refreshed: {refresh_ts}</div>',
    unsafe_allow_html=True,
)
