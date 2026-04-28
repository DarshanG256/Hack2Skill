"""
Page: Analytics — Full visualization dashboard.
"""
import streamlit as st
import pandas as pd
from utils.visualizations import (
    plot_approval_rates_by_group,
    plot_bias_heatmap,
    plot_metrics_comparison,
    plot_score_distribution,
    plot_fairness_gauge,
)


def render():
    st.markdown("## 📈 Analytics Dashboard")

    full_df    = st.session_state.get("audit_full_df")
    metrics_df = st.session_state.get("metrics_df")
    report     = st.session_state.get("audit_report")

    if full_df is None or report is None:
        st.warning("⚠️ No batch audit results available. Please run a **Batch Dataset Audit** first.")
        return

    # ── Top KPIs ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    def kpi(col, label, value, color="#E6EDF3"):
        col.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:{color}">{value}</div>'
                     f'<div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

    kpi(c1, "Fairness Score", f"{report.audit_score:.0f}/100",
        "#00D4A1" if report.audit_score >= 80 else "#FF4B6E")
    kpi(c2, "Biased Groups", str(sum(m.is_biased for m in report.metrics_by_attribute)), "#FF4B6E")
    kpi(c3, "Overall Approval Rate", f"{report.overall_approval_rate:.1%}", "#6C63FF")
    kpi(c4, "Profiles Audited", f"{report.total_profiles:,}")

    st.markdown("---")

    # ── Fairness Gauge ────────────────────────────────────────
    col_g, col_h = st.columns([1, 2])
    with col_g:
        st.plotly_chart(plot_fairness_gauge(report.audit_score), use_container_width=True)
    with col_h:
        st.markdown("#### 📋 Metrics Summary Table")
        if metrics_df is not None and not metrics_df.empty:
            def style_severity(val):
                if "Critical" in str(val): return "color:#FF4B6E;font-weight:bold"
                if "Moderate" in str(val): return "color:#FFB347;font-weight:bold"
                if "Marginal" in str(val): return "color:#FFB347"
                return "color:#00D4A1"
            st.dataframe(
                metrics_df.style.applymap(style_severity, subset=["Bias Severity"]),
                use_container_width=True, height=250
            )

    st.markdown("---")

    # ── Approval Rate Charts ──────────────────────────────────
    st.markdown("#### 📊 Approval Rates by Protected Group")
    attr_options = [a for a in ["race", "gender", "age_group", "disability_status"] if a in full_df.columns]
    tabs = st.tabs([a.replace("_", " ").title() for a in attr_options])
    for tab, attr in zip(tabs, attr_options):
        with tab:
            fig = plot_approval_rates_by_group(full_df, attr)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Bias Heatmap ──────────────────────────────────────────
    st.markdown("#### 🌡️ Disparate Impact Heatmap")
    if metrics_df is not None and not metrics_df.empty:
        fig = plot_bias_heatmap(metrics_df)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No metrics data to display.")

    st.markdown("---")

    # ── Multi-Metric Comparison ───────────────────────────────
    st.markdown("#### ⚖️ DIR vs SPD Comparison")
    if metrics_df is not None and not metrics_df.empty:
        fig = plot_metrics_comparison(metrics_df)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Score Distributions ───────────────────────────────────
    st.markdown("#### 🎻 Score Distribution by Group")
    chosen_attr = st.selectbox("Select attribute for distribution", attr_options, key="dist_attr")
    if chosen_attr and "score" in full_df.columns:
        fig = plot_score_distribution(full_df, chosen_attr)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Raw Data Explorer ────────────────────────────────────
    with st.expander("🔍 Explore Raw Audit Data"):
        filter_attr = st.selectbox("Filter by attribute", ["(all)"] + attr_options, key="explore_filter")
        disp_df = full_df.copy()
        if filter_attr != "(all)":
            chosen_val = st.selectbox("Value", sorted(full_df[filter_attr].unique()), key="explore_val")
            disp_df = disp_df[disp_df[filter_attr] == chosen_val]
        st.dataframe(disp_df.head(200), use_container_width=True)
        csv = disp_df.to_csv(index=False).encode()
        st.download_button("📥 Download Filtered Data", csv, "filtered_audit_data.csv", "text/csv")
