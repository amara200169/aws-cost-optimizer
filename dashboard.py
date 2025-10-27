import streamlit as st
import boto3
from datetime import datetime, timedelta, timezone
from scanner import get_idle_instances, get_cost_summary  # Imports our functions

st.title("🛡️ AWS Cost Optimizer Dashboard")

# Cost metric
st.metric("Last 30 Days Spend", get_cost_summary())

# Idle instances table
st.subheader("Idle EC2 Instances")
idle = get_idle_instances()
if idle:
    data = [{"ID": inst['id'], "Type": inst['type'], "Launched": inst['launch_time'][:10], "Est. Savings/mo": inst['estimated_monthly_cost']} for inst in idle]
    st.table(data)
    if st.button("Simulate Remediation"):
        st.write("DRY RUN:")
        for inst in idle:
            st.write(f"- Would stop {inst['id']} ({inst['type']}) → Save {inst['estimated_monthly_cost']}")
else:
    st.success("✅ No idle instances—optimized!")

# Remediation toggle (calls your func)
if st.checkbox("Enable Auto-Stop (Test Only)"):
    if st.button("Run Remediation"):
        from scanner import auto_remediate
        stopped = auto_remediate(dry_run=False)  # Or True for sim
        st.success(f"Stopped {stopped} instances!")