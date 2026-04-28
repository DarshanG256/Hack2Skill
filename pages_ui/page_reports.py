"""
Page: Reports — Compliance report generation and download.
"""
import streamlit as st
import datetime
from utils.report_generator import generate_text_report, generate_csv_summary, report_to_bytes


def render():
    st.markdown("## 📄 Compliance Report")

    report     = st.session_state.get("audit_report")
    metrics_df = st.session_state.get("metrics_df")

    if report is None:
        st.warning("⚠️ No audit report available. Run a **Batch Dataset Audit** first.")
        return

    # ── Report Config ─────────────────────────────────────────
    st.markdown("### ⚙️ Report Configuration")
    rc1, rc2 = st.columns(2)
    with rc1:
        audit_name  = st.text_input("Audit Name", value="Q2 2025 Loan Decision Audit")
        model_name  = st.text_input("Model / System Name", value="Enterprise Loan Scoring Model v2.1")
    with rc2:
        org_name    = st.text_input("Organization", value="First National Bank Corp.")
        auditor_sig = st.text_input("Auditor", value="AI Risk & Compliance Division")

    st.markdown("---")
    st.markdown("### 📋 Report Preview")

    # Score badge
    score = report.audit_score
    badge_color = "#00D4A1" if score >= 80 else ("#FFB347" if score >= 60 else "#FF4B6E")
    badge_label = "COMPLIANT" if score >= 80 else ("MODERATE RISK" if score >= 60 else "CRITICAL RISK")

    st.markdown(f"""
    <div style="background:#161B22;border:1px solid #30363D;border-radius:12px;padding:24px;margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
                <div style="font-size:22px;font-weight:700;color:#E6EDF3">Shadow Applicant Compliance Report</div>
                <div style="color:#8B949E;margin-top:4px">{audit_name} · {org_name}</div>
                <div style="color:#8B949E;font-size:13px">Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
            </div>
            <div style="background:{badge_color}22;border:2px solid {badge_color};border-radius:8px;padding:12px 20px;text-align:center">
                <div style="font-size:28px;font-weight:800;color:{badge_color}">{score:.0f}</div>
                <div style="font-size:11px;color:{badge_color};letter-spacing:1px">{badge_label}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Profiles", f"{report.total_profiles:,}")
    col_b.metric("Overall Approval Rate", f"{report.overall_approval_rate:.1%}")
    col_c.metric("Biased Groups Found", str(sum(m.is_biased for m in report.metrics_by_attribute)))

    # Critical Findings
    st.markdown("#### 🔴 Critical Findings")
    for i, f in enumerate(report.critical_findings, 1):
        color = "#FF4B6E" if "CRITICAL" in f else "#FFB347"
        st.markdown(f'<div class="finding-card" style="border-left-color:{color}">'
                    f'<b>[{i}]</b> {f}</div>', unsafe_allow_html=True)

    # Metrics table
    if metrics_df is not None and not metrics_df.empty:
        st.markdown("#### 📊 Fairness Metrics")
        st.dataframe(metrics_df, use_container_width=True)

    # Recommendations
    st.markdown("#### ✅ Remediation Recommendations")
    for i, rec in enumerate(report.recommendations, 1):
        st.markdown(f"**{i}.** {rec}")

    st.markdown("---")
    st.markdown("### 📥 Download Report")

    d1, d2 = st.columns(2)

    with d1:
        full_report_text = generate_text_report(
            report, metrics_df if metrics_df is not None else __import__("pandas").DataFrame(),
            audit_name=audit_name, model_name=model_name, auditor_name=auditor_sig
        )
        st.download_button(
            label="📄 Download Full Compliance Report (.txt)",
            data=report_to_bytes(full_report_text),
            file_name=f"shadow_applicant_report_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
            type="primary",
        )

    with d2:
        if metrics_df is not None and not metrics_df.empty:
            csv_data = generate_csv_summary(metrics_df).encode()
            st.download_button(
                label="📊 Download Metrics CSV",
                data=csv_data,
                file_name=f"bias_metrics_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # Text preview
    with st.expander("👁 Preview Report Text"):
        st.text(full_report_text if 'full_report_text' in dir() else "Run download to generate preview.")
