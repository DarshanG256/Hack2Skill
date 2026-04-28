"""
Page: Dashboard — Overview metrics and system status.
"""
import streamlit as st
import pandas as pd
from utils.visualizations import plot_fairness_gauge, PALETTE


def render():
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-icon">⚖️</div>
        <div>
            <div class="hero-title">AI systems are making decisions that affect lives.<br>
            <span style="color:#6C63FF;">This platform ensures those decisions are fair.</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Platform Overview")

    has_audit = st.session_state.get("audit_report") is not None
    has_cf    = st.session_state.get("cf_results")   is not None
    has_data  = st.session_state.get("dataset_df")   is not None

    audit_score = st.session_state.get("audit_report").audit_score if has_audit else None
    total_prof  = st.session_state.get("audit_report").total_profiles if has_audit else 0
    approval    = st.session_state.get("audit_report").overall_approval_rate if has_audit else 0
    findings    = len(st.session_state.get("audit_report").critical_findings) if has_audit else 0

    c1, c2, c3, c4 = st.columns(4)
    def kpi(col, label, value, sub="", color="#6C63FF"):
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{color}">{value}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

    kpi(c1, "Profiles Audited", f"{total_prof:,}" if total_prof else "—", "Total applicants evaluated")
    kpi(c2, "Overall Approval Rate", f"{approval:.1%}" if has_audit else "—", "Across all groups",
        PALETTE["success"] if approval >= 0.5 else PALETTE["danger"])
    kpi(c3, "Critical Findings", str(findings) if has_audit else "—", "Bias flags detected",
        PALETTE["danger"] if findings > 1 else PALETTE["success"])
    kpi(c4, "Fairness Score", f"{audit_score:.0f}/100" if audit_score else "—", "Overall compliance score",
        PALETTE["success"] if (audit_score or 0) >= 80 else PALETTE["danger"])

    st.markdown("---")

    col_g, col_s = st.columns([1, 1])
    with col_g:
        if has_audit:
            st.plotly_chart(plot_fairness_gauge(audit_score), use_container_width=True)
        else:
            st.info("🔍 No audit run yet. Go to **Run Audit** to begin.")

    with col_s:
        st.markdown("#### 🤖 Agent Pipeline Status")
        agents = [
            ("Agent 1", "Profile Generator",        has_data or has_cf),
            ("Agent 2", "Counterfactual Generator", has_cf),
            ("Agent 3", "Decision Simulator",       has_cf),
            ("Agent 4", "Bias Auditor",             has_audit),
        ]
        for aid, aname, active in agents:
            badge = "🟢 Active" if active else "⚪ Idle"
            st.markdown(f"""
            <div class="agent-card {'agent-active' if active else 'agent-idle'}">
                <span class="agent-id">{aid}</span>
                <span class="agent-name">{aname}</span>
                <span class="agent-badge">{badge}</span>
            </div>""", unsafe_allow_html=True)

    if has_audit:
        st.markdown("---")
        st.markdown("#### 🔴 Critical Findings")
        report = st.session_state["audit_report"]
        for f in report.critical_findings:
            color = "#FF4B6E" if "CRITICAL" in f else "#FFB347"
            st.markdown(f'<div class="finding-card" style="border-left-color:{color}">{f}</div>',
                        unsafe_allow_html=True)
        if report.most_biased_attribute:
            st.error(f"⚠️ Most biased attribute: **{report.most_biased_attribute}** "
                     f"— most affected group: **{report.most_biased_group}**")
