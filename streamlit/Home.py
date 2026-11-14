import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

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


def run_analyst_sql(sql: str) -> tuple[str, pd.DataFrame | None, str]:
    """Execute Analyst SQL and preserve the difference between failure and zero rows."""
    if not sql or not sql.strip():
        return "NO_SQL", None, "Cortex Analyst did not generate SQL for this question."
    try:
        df = session.sql(sql).to_pandas()
        return ("NO_ROWS", df, "Query executed successfully but returned no matching rows.") if df.empty else ("SUCCESS", df, "")
    except Exception as exc:
        return "EXECUTION_FAILED", None, str(exc)


# ── Data loaders ───────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_risk_signals():
    return session.sql(
        "SELECT * FROM CHAINLOOM.CURATED.V_PRODUCT_RISK_SIGNALS ORDER BY RISK_SIGNAL_COUNT DESC"
    ).to_pandas()


@st.cache_data(ttl=30)
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


@st.cache_data(ttl=120)
def load_latest_inventory_exceptions():
    return session.sql("""
        SELECT SNAPSHOT_DATE,
               COUNT(DISTINCT PART_ID) AS PARTS_BELOW_SAFETY_STOCK
        FROM CHAINLOOM.CURATED.V_INVENTORY_POSITION
        WHERE SNAPSHOT_DATE = (
            SELECT MAX(SNAPSHOT_DATE)
            FROM CHAINLOOM.CURATED.V_INVENTORY_POSITION
        )
        AND AVAILABLE_QUANTITY < SAFETY_STOCK_QUANTITY
        GROUP BY SNAPSHOT_DATE
    """).to_pandas()


risk_df = load_risk_signals()
fulfillment_pct, otd_pct = load_executive_kpis()
inv_trend_df = load_inventory_trend()
inv_exception_df = load_latest_inventory_exceptions()
refresh_ts = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M:%S %p IST")

high_risk_count = int((risk_df["RISK_SIGNAL_COUNT"] >= 2).sum())
watchlist_count = int((risk_df["RISK_SIGNAL_COUNT"] == 1).sum())
healthy_count = int((risk_df["RISK_SIGNAL_COUNT"] == 0).sum())
attention_count = high_risk_count + watchlist_count
monitored_count = int(risk_df["PRODUCT_ID"].nunique()) if "PRODUCT_ID" in risk_df.columns else len(risk_df)

# Deterministic display priority only: signal count, then lowest fulfillment, then lowest OTD.
# This is a tie-breaker, not a composite risk score.
priority_df = risk_df.copy()
priority_df["_ff_sort"] = pd.to_numeric(priority_df["FULFILLMENT_RATE"], errors="coerce").fillna(999)
priority_df["_otd_sort"] = pd.to_numeric(priority_df["ON_TIME_DELIVERY_RATE"], errors="coerce").fillna(999)
priority_df = priority_df.sort_values(
    ["RISK_SIGNAL_COUNT", "_ff_sort", "_otd_sort", "PRODUCT_ID"],
    ascending=[False, True, True, True],
)


# Theme preference is kept in Streamlit session state across reruns.
if "chainloom_theme" not in st.session_state:
    st.session_state["chainloom_theme"] = "Light"

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
.posture-head { display: flex; align-items: baseline; gap: 6px; }
.posture-main { font-size: 1.35rem; font-weight: 700; color: #0F172A; line-height: 1.1; }
.posture-label { font-size: 0.72rem; color: #475569; }
.posture-share { font-size: 0.62rem; color: #94A3B8; margin-top: 0.15rem; }

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
.pt-miss::after { content: none; }
.pulse-ts {
    font-size: 0.6rem; color: #CBD5E1; margin-top: 0.4rem; text-align: right;
}

/* ── Inventory panel ────────────────────────────────────── */
.inv-note { font-size: 0.65rem; color: #64748B; margin-top: 0.3rem; line-height: 1.45; }
.inv-note strong { color: #334155; }
.inv-exception { font-size: 0.68rem; color: #92400E; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 5px; padding: 0.45rem 0.65rem; margin-top: 0.45rem; }
.finding-surface { background: #F8FAFC; border-left: 3px solid #3B82F6; border-radius: 0 6px 6px 0; padding: 0.65rem 0.8rem; margin-bottom: 0.55rem; }

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
.pt-table td {
    font-size: 0.8rem; color: #334155; padding: 0.55rem 0.6rem;
    border-bottom: 1px solid #F8FAFC; vertical-align: middle;
}
.pt-table tr:last-child td { border-bottom: none; }
.pt-prod { font-weight: 600; color: #1E293B; }
.pt-pct { font-variant-numeric: tabular-nums; }
.pt-miss { color: #94A3B8; } .pt-miss small { font-size: 0.56rem; color: #CBD5E1; }
.pt-sig {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 0.68rem; font-weight: 600; border-radius: 4px;
    padding: 2px 7px;
}
.pt-sig.high { background: #FEF2F2; color: #DC2626; }
.pt-sig.watch { background: #FFF7ED; color: #D97706; }
.pt-sig.ok { background: #F0FDF4; color: #059669; }
.pt-state { display: inline-block; font-size: 0.65rem; font-weight: 650; border-radius: 4px; padding: 2px 6px; white-space: nowrap; }
.pt-state.high { background: #FEF2F2; color: #DC2626; }
.pt-state.watch { background: #FFF7ED; color: #D97706; }
.pt-state.ok { background: #F0FDF4; color: #059669; }

/* ── Governance posture ────────────────────────────────── */
.gov-overview {
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.45rem;
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 0.65rem; margin-bottom: 0.7rem;
}
.gov-metric { padding: 0.45rem 0.55rem; border-right: 1px solid #F1F5F9; min-width: 0; }
.gov-metric:last-child { border-right: none; }
.gov-kicker { font-size: 0.52rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: #94A3B8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gov-value { font-size: 0.78rem; font-weight: 700; color: #334155; margin-top: 0.16rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gov-value.ok { color: #059669; }
.gov-value.lock { color: #2563EB; }
.boundary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem; }
.boundary-card {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 0.75rem 0.8rem; min-height: 118px;
}
.boundary-head { display: flex; align-items: center; justify-content: space-between; gap: 0.4rem; margin-bottom: 0.35rem; }
.boundary-type { font-size: 0.52rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748B; }
.boundary-state { font-size: 0.5rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; border-radius: 3px; padding: 2px 5px; background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
.boundary-q { font-size: 0.73rem; font-weight: 600; color: #334155; line-height: 1.35; margin-bottom: 0.5rem; }
.boundary-meta { font-size: 0.6rem; color: #94A3B8; line-height: 1.35; }
@media (max-width: 1100px) {
    .gov-overview { grid-template-columns: repeat(3, 1fr); }
    .gov-metric:nth-child(3) { border-right: none; }
}
@media (max-width: 800px) {
    .boundary-grid { grid-template-columns: 1fr; }
}

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
/* Suggested question buttons: wrap long labels instead of truncating. */
.st-key-suggestion_buttons [data-testid="stButton"] button {
    height: auto !important;
    min-height: 3.0rem;
    white-space: normal !important;
    overflow-wrap: anywhere;
    word-break: normal;
    line-height: 1.25;
    padding: 0.55rem 0.65rem;
}
.st-key-suggestion_buttons [data-testid="stButton"] button p {
    white-space: normal !important;
    overflow-wrap: anywhere;
    line-height: 1.25;
}
.boundary-state.ready { background: #F1F5F9; color: #475569; border-color: #CBD5E1; }
.boundary-state.success { background: #EFF6FF; color: #1D4ED8; border-color: #BFDBFE; }
.boundary-state.warning { background: #FFFBEB; color: #92400E; border-color: #FDE68A; }
.boundary-state.error { background: #FEF2F2; color: #B91C1C; border-color: #FECACA; }

/* ── ChainLoom premium theme system ───────────────────────────────────── */
:root {
  --cl-bg: #F3F6FB; --cl-panel: #FFFFFF; --cl-panel-soft: #F8FAFD;
  --cl-text: #142238; --cl-muted: #64748B; --cl-subtle: #8795A8;
  --cl-border: #DCE4EF; --cl-grid: #E9EEF5; --cl-blue: #2563EB;
  --cl-blue-soft: #EFF6FF; --cl-green: #087F5B; --cl-green-bg: #E8F7F0;
  --cl-amber: #A65B08; --cl-amber-bg: #FFF5E5; --cl-red: #B42332; --cl-red-bg: #FFF0F1;
  --cl-shadow: 0 8px 28px rgba(21, 40, 72, .07);
}
.stApp { background: var(--cl-bg) !important; color: var(--cl-text) !important; }
.block-container { max-width: 1500px; padding-top: 1.25rem; padding-bottom: 2rem; }
.cl-brand, .surface, .pri-surface, .pulse-cell, .ai-console, .inv-card, .tc,
.pt-surface, .gov-overview, .boundary-card, .m-cell {
  background: var(--cl-panel) !important; border-color: var(--cl-border) !important;
  box-shadow: var(--cl-shadow);
}
.cl-brand-title, .m-cell .mv, .pri-prod, .pulse-n, .posture-main, .ai-title,
.inv-q, .pt-prod, .gov-value, .boundary-q { color: var(--cl-text) !important; }
.cl-brand-name, .cl-brand-subtitle, .cl-live, .m-cell .ml, .m-cell .md, .sec-label,
.pri-sigs, .pri-met, .pulse-l, .posture-label, .posture-share, .pulse-table th,
.pulse-table td, .pulse-ts, .inv-note, .ai-sub, .inv-section-label, .tc-q,
.boundary-type, .boundary-meta, .cl-footer { color: var(--cl-muted) !important; }
.surface, .pri-surface, .pulse-cell, .ai-console, .inv-card, .tc, .pt-surface,
.gov-overview, .boundary-card { border-radius: 14px !important; }
.m-cell { padding: 1rem .85rem !important; }
.m-cell .ml { font-size: .76rem !important; letter-spacing: .055em; white-space: normal !important; }
.m-cell .mv { font-size: 1.85rem !important; font-weight: 750 !important; }
.m-cell .md { font-size: .76rem !important; }
.sec-label { font-size: .78rem !important; letter-spacing: .11em; font-weight: 750 !important; }
.cl-brand-title { font-size: 1.55rem !important; }
.cl-brand-name { font-size: .75rem !important; }
.cl-brand-subtitle { font-size: .85rem !important; }
.pri-prod { font-size: 1.2rem !important; }
.pri-sigs, .pri-met, .pri-why, .pri-gov, .pulse-l, .posture-label, .inv-note,
.inv-exception, .ai-sub, .tc-q, .boundary-q, .boundary-meta { font-size: .88rem !important; line-height: 1.5 !important; }
.pulse-n { font-size: 1.45rem !important; }
.posture-main { font-size: 1.65rem !important; }
.pt-table th, .pulse-table th, .gov-kicker { font-size: .72rem !important; }
.pt-table td, .pulse-table td, .gov-value { font-size: .88rem !important; }
.boundary-state, .gov-state, .pri-badge, .tc-badge { font-size: .68rem !important; padding: 4px 8px !important; }
.ai-hdr, .inv-tag, .inv-section-label { font-size: .75rem !important; }
.ai-title { font-size: 1.35rem !important; }
.stButton > button, .stFormSubmitButton > button { min-height: 2.8rem; border-radius: 10px; font-weight: 650; }
.stTextInput input { min-height: 2.8rem; border-radius: 10px; }
.stDataFrame, [data-testid="stDataFrame"] { border: 1px solid var(--cl-border); border-radius: 12px; }
.stExpander { border: 1px solid var(--cl-border); border-radius: 12px; }
.st-key-suggestion_buttons [data-testid="stButton"] button { min-height: 4rem; white-space: normal !important; overflow-wrap: anywhere; line-height: 1.35; }
.boundary-state.ready { background: var(--cl-panel-soft); color: var(--cl-muted); border-color: var(--cl-border); }
.boundary-state.success { background: var(--cl-green-bg); color: var(--cl-green); border-color: #9AD9BD; }
.boundary-state.warning { background: var(--cl-amber-bg); color: var(--cl-amber); border-color: #F2D39B; }
.boundary-state.error { background: var(--cl-red-bg); color: var(--cl-red); border-color: #F2B8BE; }
.gov-state.verified, .can-block, .gb { background: var(--cl-green-bg) !important; color: var(--cl-green) !important; border-color: #9AD9BD !important; }
.boundary-state.enforced { background: var(--cl-green-bg) !important; color: var(--cl-green) !important; border-color: #9AD9BD !important; }
.gov-state.enforced { background: var(--cl-green-bg) !important; color: var(--cl-green) !important; border-color: #9AD9BD !important; }
.cannot-block { background: var(--cl-red-bg) !important; color: var(--cl-red) !important; border-color: #F2B8BE !important; }

/* Dark palette: all custom surfaces, typography, controls and status chips move together. */
</style>""", unsafe_allow_html=True)

if st.session_state["chainloom_theme"] == "Dark":
    st.markdown("""<style>
      :root { --cl-bg:#0B1220; --cl-panel:#111C2E; --cl-panel-soft:#172438; --cl-text:#E8EEF7;
        --cl-muted:#A7B5C8; --cl-subtle:#8293AA; --cl-border:#26364D; --cl-grid:#26364D;
        --cl-blue:#7CB8FF; --cl-blue-soft:#152B46; --cl-green:#72D6A8; --cl-green-bg:#12372D;
        --cl-amber:#F6C66D; --cl-amber-bg:#3A2B16; --cl-red:#FF9AA4; --cl-red-bg:#3A2028;
        --cl-shadow:0 10px 30px rgba(0,0,0,.22); }
      .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background:var(--cl-bg) !important; color:var(--cl-text) !important; }
      .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp li, .stApp span { color:inherit; }
      .cl-brand, .surface, .pri-surface, .pulse-cell, .ai-console, .inv-card, .tc, .pt-surface, .gov-overview, .boundary-card, .m-cell { background:var(--cl-panel) !important; border-color:var(--cl-border) !important; }
      .cl-brand-title, .m-cell .mv, .pri-prod, .pulse-n, .posture-main, .ai-title, .inv-q, .pt-prod, .gov-value, .boundary-q { color:var(--cl-text) !important; }
      .cl-brand-name, .cl-brand-subtitle, .cl-live, .m-cell .ml, .m-cell .md, .sec-label, .pri-sigs, .pri-met, .pulse-l, .posture-label, .posture-share, .pulse-table th, .pulse-table td, .pulse-ts, .inv-note, .ai-sub, .inv-section-label, .tc-q, .boundary-type, .boundary-meta, .cl-footer { color:var(--cl-muted) !important; }
      .pulse-table td, .pt-table td { border-color:var(--cl-border) !important; }
      .pri-gov, .inv-sep { border-color:var(--cl-border) !important; color:var(--cl-muted) !important; }
      .finding-surface { background:#172B43 !important; color:#D8E8FA !important; border-color:#5797D4 !important; }
      .inv-exception { background:var(--cl-amber-bg) !important; color:var(--cl-amber) !important; border-color:#73582D !important; }
      .pri-badge.high, .pt-state.high, .pt-sig.high { background:#3A2028 !important; color:#FF9AA4 !important; border-color:#75404A !important; }
      .pri-badge.watch, .pt-state.watch, .pt-sig.watch { background:#3A2B16 !important; color:#F6C66D !important; border-color:#73582D !important; }
      .pt-state.ok, .pt-sig.ok { background:#12372D !important; color:#72D6A8 !important; }
      .gov-state.verified, .gov-state.enforced, .can-block, .gb { background:var(--cl-green-bg) !important; color:var(--cl-green) !important; border-color:#286B55 !important; }
      .cannot-block { background:var(--cl-red-bg) !important; color:var(--cl-red) !important; border-color:#75404A !important; }
      .boundary-state.ready { background:var(--cl-panel-soft) !important; color:var(--cl-muted) !important; border-color:var(--cl-border) !important; }
      .boundary-state.success { background:var(--cl-green-bg) !important; color:var(--cl-green) !important; border-color:#286B55 !important; }
      .boundary-state.warning { background:var(--cl-amber-bg) !important; color:var(--cl-amber) !important; border-color:#73582D !important; }
      .boundary-state.error { background:var(--cl-red-bg) !important; color:var(--cl-red) !important; border-color:#75404A !important; }
      .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div { background:#172438 !important; color:var(--cl-text) !important; border-color:var(--cl-border) !important; }
      .stButton > button, .stFormSubmitButton > button { background:#1B2B42; color:#E8EEF7; border-color:#344963; }
      .stButton > button:hover { border-color:#7CB8FF; color:#FFFFFF; }
      [data-testid="stExpander"] { background:var(--cl-panel) !important; border-color:var(--cl-border) !important; }
      [data-testid="stDataFrame"] { filter: brightness(.88) contrast(1.04); }
      [data-testid="stMetric"] { background:var(--cl-panel); border:1px solid var(--cl-border); border-radius:12px; padding:12px; }
      .stAlert { background:var(--cl-panel) !important; color:var(--cl-text) !important; }
    </style>""", unsafe_allow_html=True)




# Final visual polish: preserve the original risk colour language while elevating the KPI tiles.
st.markdown("""<style>
/* Five headline KPI tiles: distinct semantic colours, not generic white boxes. */
.m-strip { display:grid !important; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px !important; background:transparent !important; overflow:visible !important; margin:0 0 1.35rem !important; }
.m-cell { position:relative; overflow:hidden; min-height:122px; border:1px solid transparent !important; border-radius:18px !important; padding:1.05rem 1.05rem .95rem !important; text-align:left !important; box-shadow:0 10px 26px rgba(25,45,78,.10) !important; transition:transform .22s ease, box-shadow .22s ease; }
.m-cell:hover { transform:translateY(-4px); box-shadow:0 16px 32px rgba(25,45,78,.16) !important; }
.m-cell:before { content:""; position:absolute; left:0; top:0; bottom:0; width:5px; background:var(--tile-accent); }
.m-cell:after { content:""; position:absolute; width:112px; height:112px; border-radius:50%; right:-42px; top:-48px; background:var(--tile-glow); }
.m-cell:nth-child(1) { --tile-accent:#E5484D; --tile-glow:rgba(229,72,77,.12); background:linear-gradient(135deg,#FFF4F3,#FFFFFF) !important; border-color:#F7D2D0 !important; }
.m-cell:nth-child(2) { --tile-accent:#D99018; --tile-glow:rgba(217,144,24,.14); background:linear-gradient(135deg,#FFF8E9,#FFFFFF) !important; border-color:#F4E1B9 !important; }
.m-cell:nth-child(3) { --tile-accent:#7657D5; --tile-glow:rgba(118,87,213,.13); background:linear-gradient(135deg,#F5F1FF,#FFFFFF) !important; border-color:#DED5FA !important; }
.m-cell:nth-child(4) { --tile-accent:#078B73; --tile-glow:rgba(7,139,115,.13); background:linear-gradient(135deg,#EAF9F5,#FFFFFF) !important; border-color:#C7EDE3 !important; }
.m-cell:nth-child(5) { --tile-accent:#2878D0; --tile-glow:rgba(40,120,208,.13); background:linear-gradient(135deg,#EDF5FF,#FFFFFF) !important; border-color:#D0E3FA !important; }
.m-cell .ml,.m-cell .mv,.m-cell .md { position:relative; z-index:1; text-align:left !important; }
.m-cell .ml { color:#43536B !important; font-size:.78rem !important; font-weight:750 !important; letter-spacing:.025em !important; line-height:1.35; white-space:normal !important; }
.m-cell .mv { color:#17263D !important; font-size:2rem !important; font-weight:800 !important; letter-spacing:-.04em; margin:.35rem 0 .18rem; }
.m-cell:nth-child(1) .mv { color:#C7353B !important; }
.m-cell:nth-child(2) .mv { color:#A96808 !important; }
.m-cell:nth-child(3) .mv { color:#6244BE !important; }
.m-cell:nth-child(4) .mv { color:#087A65 !important; }
.m-cell:nth-child(5) .mv { color:#2168B7 !important; }
.m-cell .md { color:#66758B !important; font-size:.76rem !important; }
.cl-info { display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px; margin-left:3px; border-radius:50%; border:1px solid currentColor; font-size:10px; font-weight:800; line-height:1; opacity:.78; cursor:help; vertical-align:1px; }
/* Branded animated ChainLoom mark. Subtle motion only; no distracting page animation. */
.cl-mark { filter:drop-shadow(0 3px 7px rgba(41,181,232,.22)); animation:cl-mark-float 3.8s ease-in-out infinite; }
.cl-mark .node { box-shadow:0 0 0 3px rgba(41,181,232,.10); animation:cl-node-pulse 2.8s ease-in-out infinite; }
.cl-mark .node.n2 { animation-delay:.35s; } .cl-mark .node.n3 { animation-delay:.7s; } .cl-mark .node.n4 { animation-delay:1.05s; }
@keyframes cl-mark-float { 0%,100% { transform:translateY(0) rotate(0); } 50% { transform:translateY(-3px) rotate(4deg); } }
@keyframes cl-node-pulse { 0%,100% { box-shadow:0 0 0 2px rgba(41,181,232,.10); } 50% { box-shadow:0 0 0 6px rgba(41,181,232,.04),0 0 13px rgba(41,181,232,.45); } }
/* Rich, linked surfaces and clearer section hierarchy. */
.surface,.pri-surface,.ai-console,.inv-card,.tc,.pt-surface,.gov-overview,.boundary-card { border-radius:18px !important; box-shadow:0 8px 26px rgba(22,43,74,.07) !important; }
.sec-label { font-size:.82rem !important; font-weight:800 !important; letter-spacing:.10em !important; color:#53647D !important; }
.st-key-suggestion_buttons [data-testid="stButton"] button { min-height:4.1rem !important; border-radius:14px !important; border:1px solid #D7E1EF !important; background:linear-gradient(145deg,#FFFFFF,#F3F7FC) !important; color:#23344D !important; box-shadow:0 5px 16px rgba(29,54,89,.07); font-weight:650 !important; white-space:normal !important; }
.st-key-suggestion_buttons [data-testid="stButton"] button:hover { border-color:#65A8DC !important; background:#EDF6FF !important; transform:translateY(-2px); }
/* Dark theme: explicit foreground/background pairs for all custom content. */
</style>""", unsafe_allow_html=True)

if st.session_state["chainloom_theme"] == "Dark":
    st.markdown("""<style>
      .m-cell:nth-child(1) { background:linear-gradient(135deg,#3B2028,#251B28) !important; border-color:#70404A !important; }
      .m-cell:nth-child(2) { background:linear-gradient(135deg,#3A2E1D,#282318) !important; border-color:#71582F !important; }
      .m-cell:nth-child(3) { background:linear-gradient(135deg,#30264C,#211D37) !important; border-color:#57477F !important; }
      .m-cell:nth-child(4) { background:linear-gradient(135deg,#153A35,#142B2D) !important; border-color:#28685B !important; }
      .m-cell:nth-child(5) { background:linear-gradient(135deg,#193654,#17283E) !important; border-color:#315D87 !important; }
      .m-cell .ml { color:#D5DFEC !important; }
      .m-cell .md { color:#A9B8CB !important; }
      .m-cell:nth-child(1) .mv { color:#FF9DA5 !important; }
      .m-cell:nth-child(2) .mv { color:#F6CA78 !important; }
      .m-cell:nth-child(3) .mv { color:#C5B4FF !important; }
      .m-cell:nth-child(4) .mv { color:#83E0C4 !important; }
      .m-cell:nth-child(5) .mv { color:#91C8FF !important; }
      .cl-info { color:#C7D5E7 !important; }
      .sec-label { color:#B9C8DA !important; }
      .st-key-suggestion_buttons [data-testid="stButton"] button { background:linear-gradient(145deg,#1A2B42,#152338) !important; color:#E7EEF8 !important; border-color:#344B67 !important; }
      .st-key-suggestion_buttons [data-testid="stButton"] button:hover { background:#203B5A !important; border-color:#78B8F4 !important; }
      .surface,.pri-surface,.ai-console,.inv-card,.tc,.pt-surface,.gov-overview,.boundary-card { box-shadow:0 10px 28px rgba(0,0,0,.20) !important; }
      .cl-mark .node { box-shadow:0 0 0 3px rgba(41,181,232,.15); }
    </style>""", unsafe_allow_html=True)

# Theme switch sits in the application header and persists across Streamlit reruns.
_theme_spacer, _theme_control = st.columns([8, 2])
with _theme_control:
    st.radio(
        "Appearance", ["Light", "Dark"],
        horizontal=True, key="chainloom_theme",
        label_visibility="collapsed",
    )

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
fulfillment_pct = float(fulfillment_pct) if fulfillment_pct is not None and pd.notna(fulfillment_pct) else None
otd_pct = float(otd_pct) if otd_pct is not None and pd.notna(otd_pct) else None
ff_c = "g" if fulfillment_pct is not None and fulfillment_pct >= 90 else ("w" if fulfillment_pct is not None and fulfillment_pct >= 80 else "d")
ff_v = f"{fulfillment_pct:.1f}%" if fulfillment_pct is not None else "Unavailable"
otd_c = "g" if otd_pct is not None and otd_pct >= 85 else ("w" if otd_pct is not None and otd_pct >= 70 else "d")
otd_v = f"{otd_pct:.1f}%" if otd_pct is not None else "Unavailable"

st.markdown(f"""
<div class="m-strip">
    <div class="m-cell">
        <div class="ml" title="Products with two or more independently observed risk signals.">High-Risk Products <span class="cl-info">i</span></div>
        <div class="mv{"  d" if high_risk_count > 0 else ""}">{high_risk_count}</div>
        <div class="md">&ge;2 signals</div>
    </div>
    <div class="m-cell">
        <div class="ml" title="Products with one independently observed risk signal.">Watchlist <span class="cl-info">i</span></div>
        <div class="mv{" w" if watchlist_count > 0 else ""}">{watchlist_count}</div>
        <div class="md">1 signal</div>
    </div>
    <div class="m-cell">
        <div class="ml" title="High-risk products plus watchlist products. This is a prioritisation count, not a causal score.">Products Needing Attention <span class="cl-info">i</span></div>
        <div class="mv{" d" if attention_count > 0 else ""}">{attention_count}</div>
        <div class="md">of {monitored_count} products</div>
    </div>
    <div class="m-cell">
        <div class="ml" title="Fulfilled quantity divided by ordered quantity across the available customer fulfillment records.">Network Fulfillment <span class="cl-info">i</span></div>
        <div class="mv {ff_c}">{ff_v}</div>
        <div class="md">all available orders</div>
    </div>
    <div class="m-cell">
        <div class="ml" title="On-time eligible shipments divided by all eligible shipments.">On-Time Delivery <span class="cl-info">i</span></div>
        <div class="mv {otd_c}">{otd_v}</div>
        <div class="md">eligible shipments</div>
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

    top = priority_df.iloc[0] if len(priority_df) > 0 and priority_df.iloc[0]["RISK_SIGNAL_COUNT"] > 0 else None

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

        attention = "HIGH RISK" if sig_count >= 2 else "WATCHLIST"
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

        # Explain the selection using observable signals only — no composite score.
        why_parts = []
        if top.get("FULFILLMENT_RISK_FLAG") and ff_rate is not None and pd.notna(ff_rate):
            why_parts.append(f"fulfillment {ff_rate:.0%}")
        if top.get("DELIVERY_RISK_FLAG") and otd_rate is not None and pd.notna(otd_rate):
            why_parts.append(f"on-time delivery {otd_rate:.0%}")
        if top.get("PRODUCTION_RISK_FLAG") and prod_att is not None and pd.notna(prod_att):
            why_parts.append(f"production attainment {prod_att:.0%}")
        if why_parts:
            why_text = f"Why surfaced: {sig_count} independent risk signals — " + "; ".join(why_parts) + "."
        else:
            why_text = f"Why surfaced: {sig_count} independent risk signals detected."

        st.markdown(f"""
        <div class="pri-surface">
            <div class="pri-badge {badge_cls}">{attention}</div>
            <div class="pri-prod">{top["PRODUCT_ID"]} \u2014 {top["PRODUCT_NAME"]}</div>
            <div class="pri-sigs">{sig_count} independent risk signal{"s" if sig_count != 1 else ""} \u00b7 {signal_text}</div>
            <div class="pri-mets">{met_html}</div>
            <div class="pri-why">{why_text}</div>
            <div class="pri-gov">Priority order uses signal count first; supporting metrics only break ties. Signals are independently observed indicators and do not establish causality.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="surface" style="color:#059669;font-size:0.85rem;">'
            'All products within normal operating thresholds.</div>',
            unsafe_allow_html=True,
        )

# ── RIGHT: NETWORK POSTURE ────────────────────────────────────────────────
with ef_right:
    st.markdown('<div class="sec-label">Network Posture</div>', unsafe_allow_html=True)
    total = monitored_count or 1
    attention_share = attention_count / total
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
        <div class="posture-head">
            <div class="posture-main">{attention_count} of {monitored_count}</div>
            <div class="posture-label">products require attention</div>
        </div>
        <div class="posture-share">{attention_share:.1%} of network scope</div>
        <table class="pulse-table">
            <thead><tr><th>Attention state</th><th>Products</th><th>Share</th></tr></thead>
            <tbody>{pulse_table_rows}</tbody>
        </table>
        <div class="pulse-ts">Network scope: {monitored_count} products · Last refreshed: {refresh_ts}</div>
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
    }).copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])

    # Native Vega-Lite keeps the chart dependency-free while giving us
    # control over readable date ticks and the actual snapshot range.
    chart_long = chart_df.melt(
        id_vars=["Date"],
        value_vars=["Available Inventory", "Safety Stock Level"],
        var_name="Metric",
        value_name="Value",
    )
    chart_spec = {
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {
                "field": "Date",
                "type": "temporal",
                "title": None,
                "axis": {"format": "%b %d", "tickCount": 6, "labelAngle": 0},
            },
            "y": {
                "field": "Value",
                "type": "quantitative",
                "title": None,
            },
            "color": {
                "field": "Metric",
                "type": "nominal",
                "title": None,
            },
        },
        "width": "container",
        "height": 220,
        "config": {
            "view": {"stroke": None},
            "axis": {"grid": True},
        },
    }
    st.vega_lite_chart(chart_long, chart_spec, use_container_width=True)

    total_snaps = len(inv_trend_df)
    below_count = int((inv_trend_df["AVAILABLE_INVENTORY"] < inv_trend_df["SAFETY_STOCK_LEVEL"]).sum())
    if below_count == 0:
        inv_trend_insight = "Network available inventory stayed above aggregate safety stock in every displayed snapshot."
    elif below_count == total_snaps:
        inv_trend_insight = "Network available inventory was below aggregate safety stock in every displayed snapshot."
    else:
        inv_trend_insight = f"Network available inventory was below aggregate safety stock in {below_count} of {total_snaps} displayed snapshots."

    if not inv_exception_df.empty:
        latest_date = pd.to_datetime(inv_exception_df.iloc[0]["SNAPSHOT_DATE"]).strftime("%Y-%m-%d")
        parts_below = int(inv_exception_df.iloc[0]["PARTS_BELOW_SAFETY_STOCK"])
        inv_exception = f"Latest snapshot · {latest_date} · {parts_below} part{'s' if parts_below != 1 else ''} below safety stock."
    else:
        latest_date = pd.to_datetime(inv_trend_df["SNAPSHOT_DATE"]).max().strftime("%Y-%m-%d")
        inv_exception = f"Latest snapshot · {latest_date} · No parts below safety stock."

    st.markdown(f'<div class="inv-note"><strong>Network position:</strong> {inv_trend_insight}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="inv-exception"><strong>Exception check:</strong> {inv_exception}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="inv-note">Snapshot-aware inventory view · '
        'no cross-date aggregation · each date represents its own inventory position.</div>',
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
        return '<span class="pt-miss">— <small>unavailable</small></span>'
    return f'<span class="pt-pct">{val:.0%}</span>'


def fmt_sig_html(n):
    if n is None or pd.isna(n):
        return '<span class="pt-miss">—</span>'
    n = int(n)
    if n == 0:
        return '<span class="pt-sig ok">✓ None</span>'
    if n == 1:
        return '<span class="pt-sig watch">△ 1 signal</span>'
    return f'<span class="pt-sig high">● {n} signals</span>'


def fmt_attention_html(n):
    if n is None or pd.isna(n):
        return '<span class="pt-state">—</span>'
    n = int(n)
    if n >= 2:
        return '<span class="pt-state high">High Risk</span>'
    if n == 1:
        return '<span class="pt-state watch">Watchlist</span>'
    return '<span class="pt-state ok">Healthy</span>'


table_rows = ""
for _, row in priority_df.iterrows():
    table_rows += (
        f'<tr>'
        f'<td><span class="pt-prod">{row["PRODUCT_ID"]}</span> {row["PRODUCT_NAME"]}</td>'
        f'<td>{fmt_attention_html(row.get("RISK_SIGNAL_COUNT"))}</td>'
        f'<td>{fmt_sig_html(row.get("RISK_SIGNAL_COUNT"))}</td>'
        f'<td>{fmt_pct_html(row.get("FULFILLMENT_RATE"))}</td>'
        f'<td>{fmt_pct_html(row.get("ON_TIME_DELIVERY_RATE"))}</td>'
        f'<td>{fmt_pct_html(row.get("PRODUCTION_ATTAINMENT"))}</td>'
        f'</tr>'
    )

if table_rows:
    st.markdown(f"""
    <div class="pt-surface">
        <table class="pt-table">
            <thead><tr>
                <th>Product</th><th>Attention</th><th>Signal Evidence</th>
                <th>Fulfillment</th><th>On-Time Delivery</th><th>Production</th>
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

with st.container(key="suggestion_buttons"):
    sg_cols = st.columns(len(suggestions))
    for i, sg in enumerate(suggestions):
        with sg_cols[i]:
            if st.button(sg, key=f"sg_{i}", use_container_width=True):
                st.session_state["_suggestion_text"] = sg
                st.session_state["_suggestion_version"] += 1
                st.rerun()

# Use a form so pressing Enter in the question field submits the investigation.
with st.form(key="analyst_form", clear_on_submit=False):
    input_col, action_col = st.columns([5, 1])
    with input_col:
        question = st.text_input(
            "Ask a question about your supply chain",
            value=st.session_state["_suggestion_text"],
            placeholder="e.g. What is the fulfillment rate by customer segment?",
            key=f"analyst_input_{st.session_state['_suggestion_version']}",
            label_visibility="collapsed",
        )
    with action_col:
        submitted = st.form_submit_button(
            "Investigate",
            type="primary",
            use_container_width=True,
        )

# Once the widget is initialized with the suggestion, retain what the user
# types in the normal widget state; the versioned key only changes on a new
# suggestion selection.
st.session_state["_suggestion_text"] = question

# Reset only the investigation workspace; the dashboard/data remain unchanged.
reset_col = st.columns([5, 1])[1]
with reset_col:
    reset_investigation = st.button(
        "↻ Reset Investigation",
        key="reset_investigation",
        use_container_width=True,
    )

if reset_investigation:
    st.session_state.analyst_history = []
    st.session_state.analyst_results = []
    st.session_state["_suggestion_text"] = ""
    st.session_state["_suggestion_version"] += 1
    st.rerun()

if submitted and question.strip():
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
            execution_status, df_result, execution_message = run_analyst_sql(parsed["sql"])
            st.session_state.analyst_results.append({
                "question": question.strip(),
                "parsed": parsed,
                "df": df_result,
                "execution_status": execution_status,
                "execution_message": execution_message,
            })
        except Exception as e:
            st.error(f"Cortex Analyst error: {e}")

def build_business_finding(entry):
    """Create a concise business-first finding from governed query results.

    Prefer deterministic summaries from returned evidence. For questions that do
    not match a known pattern, fall back to a neutral result-count statement
    rather than inventing an interpretation.
    """
    df = entry.get("df")
    q = (entry.get("question") or "").lower()
    if df is None:
        return "The query could not be executed; no business finding is available."
    if df.empty:
        return "The query executed successfully but returned no matching records."

    n = len(df)
    cols = {str(c).upper(): c for c in df.columns}

    # Supplier defect-rate investigation
    if "supplier" in q and "defect" in q and "DEFECT_RATE" in cols:
        row = df.iloc[0]
        name_col = cols.get("SUPPLIER_NAME")
        rate_col = cols["DEFECT_RATE"]
        if name_col is not None and pd.notna(row[name_col]) and pd.notna(row[rate_col]):
            return f"{row[name_col]} has the highest observed defect rate at {float(row[rate_col]):.0%}."

    # Carrier OTD investigation
    if "carrier" in q and ("on-time" in q or "otd" in q or "delivery" in q):
        rate_col = next((cols[k] for k in ("ON_TIME_DELIVERY_RATE", "OTD_RATE") if k in cols), None)
        name_col = cols.get("CARRIER_NAME")
        if rate_col is not None and name_col is not None:
            row = df.iloc[0]
            if pd.notna(row[name_col]) and pd.notna(row[rate_col]):
                return f"{row[name_col]} has the lowest observed on-time delivery rate at {float(row[rate_col]):.0%}."

    # Parts below safety stock
    if "part" in q and "safety stock" in q:
        return f"{n} part{'s' if n != 1 else ''} matched the below-safety-stock condition in the governed result."

    # Multiple product risk signals
    if "product" in q and "risk signal" in q:
        return f"{n} product{'s' if n != 1 else ''} show multiple independently observed risk signals."

    return f"The governed query returned {n} matching result{'s' if n != 1 else ''}."


def clean_analyst_context(text):
    """Remove the Analyst's implementation-style preamble from the executive finding area."""
    if not text:
        return ""
    marker = "This is our interpretation of your question:"
    cleaned = text.strip()
    if cleaned.lower().startswith(marker.lower()):
        cleaned = cleaned[len(marker):].strip()
    return cleaned


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

    finding = build_business_finding(entry)
    st.markdown('<div class="inv-section-label">Finding</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="finding-surface">{finding}</div>', unsafe_allow_html=True)

    analyst_context = clean_analyst_context(parsed.get("text", ""))
    if analyst_context and analyst_context.lower() != finding.lower():
        with st.expander("Analyst interpretation", expanded=False):
            st.markdown(analyst_context)

    execution_status = entry.get("execution_status", "SUCCESS" if entry.get("df") is not None else "NO_SQL")
    execution_message = entry.get("execution_message", "")
    if execution_status == "EXECUTION_FAILED":
        st.error(f"Query execution failed: {execution_message}")
    elif execution_status == "NO_SQL":
        st.warning(execution_message or "No SQL was generated for this question.")
    elif execution_status == "NO_ROWS":
        st.info(execution_message or "Query executed successfully but returned no matching rows.")
    elif entry.get("df") is not None:
        st.markdown('<div class="inv-section-label">Results</div>', unsafe_allow_html=True)
        st.dataframe(entry["df"], use_container_width=True, hide_index=True)

    if parsed["warnings"]:
        with st.expander(f"Analyst diagnostics · {len(parsed['warnings'])}", expanded=False):
            st.caption("Technical advisories from Cortex Analyst are shown here separately from the business finding.")
            for warning in parsed["warnings"]:
                st.caption(str(warning))

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
st.caption("Configured governance policies are shown in green. Each test's execution outcome is displayed separately; successful SQL execution alone does not prove causation or policy compliance.")

# Enterprise posture: persistent, scannable controls rather than a static demo-style block.
gov_overview = [
    ("Semantic Layer", "CONNECTED", "ok"),
    ("Verified Queries", "11", "ok"),
    ("Fact-to-Fact Joins", "BLOCKED", "lock"),
    ("Causal Inference", "BLOCKED", "lock"),
    ("Inventory Grain", "SNAPSHOT", "ok"),
    ("Missing Values", "PRESERVED", "ok"),
]
gov_cells = "".join(
    f'<div class="gov-metric"><div class="gov-kicker">{label}</div>'
    f'<div class="gov-value {cls}">{value}</div></div>'
    for label, value, cls in gov_overview
)
st.markdown(f'<div class="gov-overview">{gov_cells}</div>', unsafe_allow_html=True)

challenges = [
    {
        "badge_cls": "causal",
        "badge": "Causal Boundary",
        "label": "Can P104 shortage be proven as the cause?",
        "question": "For August 2026, which products with Part P104 BOM exposure also had constrained production days, and what can the data establish about causation?",
        "can": "BOM exposure and production constraints can be independently reported.",
        "cannot": "Causation cannot be established without a valid linkage between the inventory and production surfaces.",
        "state": "BOUNDARY ENFORCED",
        "state_cls": "enforced",
    },
    {
        "badge_cls": "attrib",
        "badge": "Attribution Boundary",
        "label": "Can supplier delay be proven as the cause?",
        "question": "Which supplier delivery delays directly caused late shipments to our Strategic customers?",
        "can": "Supplier and shipment delays can be independently observed.",
        "cannot": "Direct supplier-to-customer causation cannot be established because lot/batch genealogy is unavailable.",
        "state": "BOUNDARY ENFORCED",
        "state_cls": "enforced",
    },
    {
        "badge_cls": "signals",
        "badge": "Signal Interpretation",
        "label": "Can multiple risk signals be combined without inventing causality?",
        "question": "Which products currently show multiple independent supply-chain risk signals across fulfillment, delivery, and production?",
        "can": "Independent threshold breaches can be reported at product level.",
        "cannot": "Co-occurrence does not justify a weighted or causal risk score.",
        "state": "POLICY ACTIVE",
        "state_cls": "verified",
    },
]

# Persist each challenge's latest execution outcome so the card reflects reality.
if "_challenge_status" not in st.session_state:
    st.session_state["_challenge_status"] = {}
if "_challenge_results" not in st.session_state:
    st.session_state["_challenge_results"] = {}

st.markdown('<div class="inv-section-label">Boundary checks</div>', unsafe_allow_html=True)
ch_cols = st.columns(3, gap="medium")
for i, ch in enumerate(challenges):
    with ch_cols[i]:
        current_status = st.session_state["_challenge_status"].get(i, (ch["state"], ch["state_cls"]))
        state_label, state_class = current_status
        st.markdown(
            f'<div class="boundary-card">'
            f'<div class="boundary-head"><span class="boundary-type">{ch["badge"]}</span>'
            f'<span class="boundary-state {state_class}">{state_label}</span></div>'
            f'<div class="boundary-q">{ch["label"]}</div>'
            f'<div class="boundary-meta">Test the governed boundary against Cortex Analyst.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Test Boundary", key=f"ch_{i}", use_container_width=True):
            st.session_state[f"_run_challenge_{i}"] = True

# Execute selected checks, persist their result, and refresh the cards with the true outcome.
for i, ch in enumerate(challenges):
    if st.session_state.get(f"_run_challenge_{i}"):
        st.session_state[f"_run_challenge_{i}"] = False
        st.session_state["_challenge_status"][i] = ("RUNNING...", "warning")
        try:
            with st.spinner("Running governance boundary check..."):
                raw = call_analyst(ch["question"])
                parsed = parse_analyst_response(raw)
                execution_status, df, execution_message = run_analyst_sql(parsed["sql"])

                entry = {
                    "question": ch["question"],
                    "parsed": parsed,
                    "df": df,
                    "execution_status": execution_status,
                    "execution_message": execution_message,
                }
                if execution_status == "SUCCESS":
                    card_status = ("CHECK COMPLETE · REVIEW", "success")
                elif execution_status == "NO_ROWS":
                    card_status = ("EXECUTED — NO ROWS", "warning")
                elif execution_status == "NO_SQL":
                    card_status = ("NO SQL GENERATED", "warning")
                else:
                    card_status = ("EXECUTION FAILED", "error")

                st.session_state["_challenge_status"][i] = card_status
                st.session_state["_challenge_results"][i] = entry
        except Exception as e:
            st.session_state["_challenge_status"][i] = ("ANALYST ERROR", "error")
            st.session_state["_challenge_results"][i] = {"error": str(e)}
        st.rerun()

# Show the latest result beneath its card after the status has been refreshed.
for i, ch in enumerate(challenges):
    result = st.session_state["_challenge_results"].get(i)
    if not result:
        continue
    st.markdown(f"**{ch['badge']} — latest test result**")
    if "error" in result:
        st.error(f"Cortex Analyst error: {result['error']}")
        continue
    render_governed_result(
        result,
        governance={"can": ch["can"], "cannot": ch["cannot"]},
    )

# Permanent governance proof points — concise and reviewer-friendly.
with st.expander("Governance controls · 6 active", expanded=False):
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
