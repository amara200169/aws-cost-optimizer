import streamlit as st
from scanner import get_idle_instances, get_cost_summary, auto_remediate

st.set_page_config(
    page_title="AWS Cost Optimizer",
    page_icon="☁️",
    layout="wide",
)

st.markdown("""
<style>
/* ── Background ── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05);
}

/* ── Main content padding ── */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 2.5rem;
}

/* ── Title ── */
h1 {
    color: #ffffff !important;
    font-size: 2.6rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    text-align: center;
    margin-bottom: 0.2rem !important;
}

/* ── Subheaders ── */
h2, h3 {
    color: #e0e0ff !important;
    font-weight: 700 !important;
}

/* ── Metric card ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.2rem 1.8rem;
    backdrop-filter: blur(10px);
}
[data-testid="stMetricLabel"] p {
    color: #a0aec0 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
[data-testid="stMetricValue"] {
    color: #68d391 !important;
    font-size: 2.8rem !important;
    font-weight: 800 !important;
}

/* ── Table ── */
[data-testid="stTable"] table {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
    width: 100%;
}
[data-testid="stTable"] th {
    background: rgba(99,102,241,0.4) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    font-size: 0.78rem;
    letter-spacing: 1px;
    padding: 0.9rem 1rem !important;
}
[data-testid="stTable"] td {
    color: #e2e8f0 !important;
    padding: 0.75rem 1rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.07) !important;
    font-size: 0.95rem;
}
[data-testid="stTable"] tr:hover td {
    background: rgba(255,255,255,0.06) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.6rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: opacity 0.2s;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* ── Alerts / success / warning ── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
}

/* ── Checkbox label ── */
[data-testid="stCheckbox"] label p {
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
}

/* ── Divider ── */
hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── Text ── */
p, li, span {
    color: #cbd5e0;
}

/* ── Subtitle tag ── */
.subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 1rem;
    margin-bottom: 2.5rem;
}

/* ── Savings badge ── */
.savings-banner {
    background: linear-gradient(90deg, rgba(104,211,145,0.15), rgba(99,102,241,0.15));
    border: 1px solid rgba(104,211,145,0.3);
    border-radius: 12px;
    padding: 0.9rem 1.4rem;
    color: #68d391;
    font-size: 1.05rem;
    font-weight: 600;
    text-align: center;
    margin-bottom: 1.2rem;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def cached_cost_summary():
    return get_cost_summary()


@st.cache_data(ttl=300)
def cached_idle_instances():
    return get_idle_instances()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<h1>☁️ AWS Cost Optimizer</h1>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Real-time EC2 idle detection & cost remediation</p>', unsafe_allow_html=True)

# ── Cost metric ───────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    try:
        st.metric("Last 30 Days Spend", cached_cost_summary())
    except Exception as e:
        st.error(f"Could not load cost data: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Idle instances ────────────────────────────────────────────────────────────
st.subheader("Idle EC2 Instances")
try:
    idle = cached_idle_instances()
except Exception as e:
    st.error(f"Could not load instance data: {e}")
    idle = []

if idle:
    total_savings = sum(
        float(inst['estimated_monthly_cost'].replace('$', ''))
        for inst in idle
    )
    st.markdown(
        f'<div class="savings-banner">💰 {len(idle)} idle instance(s) detected — potential savings of <strong>${total_savings:.2f}/month</strong></div>',
        unsafe_allow_html=True,
    )

    data = [
        {
            "ID": inst['id'],
            "Type": inst['type'],
            "Avg CPU %": inst.get('avg_cpu', 'N/A'),
            "Launched": inst['launch_time'][:10],
            "Est. Savings/mo": inst['estimated_monthly_cost'],
        }
        for inst in idle
    ]
    st.table(data)

    if st.button("▶ Simulate Remediation"):
        st.info("DRY RUN — no instances will be stopped")
        for inst in idle:
            st.write(
                f"• Would stop **{inst['id']}** ({inst['type']}, avg CPU {inst.get('avg_cpu', '?')}%)"
                f" → Save {inst['estimated_monthly_cost']}/mo"
            )
else:
    st.success("✅ No idle instances — your account is optimized!")

st.divider()

# ── Live remediation ──────────────────────────────────────────────────────────
if st.checkbox("Enable Auto-Stop (irreversible in live mode)"):
    st.warning("⚠️ This will stop real EC2 instances. Use with caution.")
    if st.button("⛔ Run Remediation (Live)"):
        try:
            stopped = auto_remediate(dry_run=False)
            st.cache_data.clear()
            st.success(f"✅ Stopped {stopped} instance(s).")
        except Exception as e:
            st.error(f"Remediation failed: {e}")
