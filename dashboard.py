import streamlit as st
from scanner import get_idle_instances, get_cost_summary, auto_remediate


@st.cache_data(ttl=300)
def cached_cost_summary():
    return get_cost_summary()


@st.cache_data(ttl=300)
def cached_idle_instances():
    return get_idle_instances()


st.title("AWS Cost Optimizer Dashboard")

try:
    st.metric("Last 30 Days Spend", cached_cost_summary())
except Exception as e:
    st.error(f"Could not load cost data: {e}")

st.subheader("Idle EC2 Instances")
try:
    idle = cached_idle_instances()
except Exception as e:
    st.error(f"Could not load instance data: {e}")
    idle = []

if idle:
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
    if st.button("Simulate Remediation"):
        st.write("DRY RUN:")
        for inst in idle:
            st.write(
                f"- Would stop {inst['id']} ({inst['type']}, avg CPU {inst.get('avg_cpu', '?')}%)"
                f" → Save {inst['estimated_monthly_cost']}/mo"
            )
else:
    st.success("No idle instances — optimized!")

st.divider()
if st.checkbox("Enable Auto-Stop (irreversible in live mode)"):
    st.warning("This will stop real EC2 instances. Use with caution.")
    if st.button("Run Remediation (Live)"):
        try:
            stopped = auto_remediate(dry_run=False)
            st.cache_data.clear()
            st.success(f"Stopped {stopped} instance(s).")
        except Exception as e:
            st.error(f"Remediation failed: {e}")
        