"""
Page: Run Audit — Profile input form + counterfactual generation + decisions.
"""
import streamlit as st
import pandas as pd
import time
from agents.profile_generator import (
    ProfileGeneratorAgent, CATEGORICAL_OPTIONS, FEATURE_RANGES
)
from agents.counterfactual_generator import CounterfactualGeneratorAgent
from agents.decision_simulator import DecisionSimulatorAgent
from agents.bias_auditor import BiasAuditorAgent
from utils.visualizations import (
    plot_counterfactual_scores, plot_decision_factors, plot_approval_rates_by_group
)


def render():
    st.markdown("## 🔬 Run Audit")

    tab_single, tab_batch = st.tabs(["🧑 Single Applicant Audit", "📊 Batch Dataset Audit"])

    with tab_single:
        _single_applicant_audit()

    with tab_batch:
        _batch_dataset_audit()


# ── Single Applicant ──────────────────────────────────────────────────────────

def _single_applicant_audit():
    st.markdown("### Step 1 — Enter Applicant Profile")
    st.caption("All financial fields are identical across counterfactuals. Only protected attributes change.")

    with st.form("applicant_form"):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**📋 Demographics (Protected)**")
            age    = st.number_input("Age", 18, 100, 38)
            gender = st.selectbox("Gender", CATEGORICAL_OPTIONS["gender"])
            race   = st.selectbox("Race / Ethnicity", CATEGORICAL_OPTIONS["race"])
            marital= st.selectbox("Marital Status", CATEGORICAL_OPTIONS["marital_status"])
            disability = st.selectbox("Disability Status", CATEGORICAL_OPTIONS["disability_status"])

        with c2:
            st.markdown("**💰 Financial Profile**")
            income       = st.number_input("Annual Income ($)", 5000, 1000000, 75000, step=1000)
            credit_score = st.slider("Credit Score", 300, 850, 680)
            loan_amount  = st.number_input("Loan Amount ($)", 1000, 2000000, 150000, step=5000)
            dti          = st.slider("Debt-to-Income Ratio", 0.0, 0.80, 0.25, step=0.01)
            yrs_emp      = st.slider("Years Employed", 0, 40, 5)

        with c3:
            st.markdown("**📄 Loan Context**")
            emp_type    = st.selectbox("Employment Type", CATEGORICAL_OPTIONS["employment_type"])
            purpose     = st.selectbox("Loan Purpose", CATEGORICAL_OPTIONS["loan_purpose"])
            collateral  = st.selectbox("Collateral", CATEGORICAL_OPTIONS["collateral"])
            edu_years   = st.slider("Education (years)", 8, 22, 16)
            dependents  = st.slider("Number of Dependents", 0, 8, 0)

        st.markdown("---")
        st.markdown("**🎯 Counterfactual Configuration**")
        cc1, cc2 = st.columns(2)
        with cc1:
            cf_attrs = st.multiselect(
                "Protected attributes to vary",
                ["gender", "race", "age_group", "disability_status", "marital_status"],
                default=["gender", "race"],
            )
        with cc2:
            noise = st.slider("Model noise level", 0.0, 0.15, 0.05, 0.01,
                              help="Simulated model randomness")

        submitted = st.form_submit_button("🚀 Generate Counterfactuals & Run Audit", type="primary", use_container_width=True)

    if submitted:
        form_data = dict(
            age=age, gender=gender, race=race, marital_status=marital,
            disability_status=disability, income=income, credit_score=credit_score,
            loan_amount=loan_amount, debt_to_income=dti, years_employed=yrs_emp,
            employment_type=emp_type, loan_purpose=purpose, collateral=collateral,
            education_years=edu_years, num_dependents=dependents,
        )

        profile_agent = ProfileGeneratorAgent()
        original = profile_agent.build_from_form(form_data)

        if not profile_agent.is_valid:
            for err in profile_agent.validation_errors:
                st.error(err)
            return

        progress = st.progress(0, "Initialising agents...")
        time.sleep(0.2)

        # Agent 2
        progress.progress(25, "Agent 2: Generating counterfactuals...")
        cf_agent   = CounterfactualGeneratorAgent()
        profiles   = cf_agent.generate_all_counterfactuals(original, cf_attrs)
        time.sleep(0.3)

        # Agent 3
        progress.progress(55, "Agent 3: Simulating decisions...")
        dec_agent  = DecisionSimulatorAgent(noise_level=noise)
        decisions  = dec_agent.decide_batch(profiles)
        time.sleep(0.3)

        # Agent 4
        progress.progress(80, "Agent 4: Running bias analysis...")
        bias_agent = BiasAuditorAgent()
        cf_result  = bias_agent.audit_counterfactuals(profiles, decisions, cf_attrs[0] if cf_attrs else "race")
        time.sleep(0.2)

        progress.progress(100, "✅ Audit complete!")
        time.sleep(0.3)
        progress.empty()

        st.session_state["cf_profiles"]  = profiles
        st.session_state["cf_decisions"] = decisions
        st.session_state["cf_results"]   = cf_result

        _render_cf_results(profiles, decisions, cf_result, cf_agent)


def _render_cf_results(profiles, decisions, cf_result, cf_agent):
    st.markdown("---")
    st.markdown("### 📊 Audit Results")

    orig_dec = decisions[0]
    decision_color = "#00D4A1" if orig_dec.approved else "#FF4B6E"
    decision_label = "✅ APPROVED" if orig_dec.approved else "❌ DENIED"

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:{decision_color}">{decision_label}</div><div class="kpi-label">Original Decision</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:#6C63FF">{orig_dec.score:.3f}</div><div class="kpi-label">Approval Score</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{orig_dec.risk_tier}</div><div class="kpi-label">Risk Tier</div></div>', unsafe_allow_html=True)
    reversal_color = "#FF4B6E" if cf_result["any_reversal"] else "#00D4A1"
    reversal_label = "⚠️ YES" if cf_result["any_reversal"] else "✅ NO"
    c4.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:{reversal_color}">{reversal_label}</div><div class="kpi-label">Decision Reversal</div></div>', unsafe_allow_html=True)

    tab_chart, tab_table, tab_factors = st.tabs(["📈 Score Chart", "📋 Variant Table", "🔎 Decision Factors"])

    with tab_chart:
        fig = plot_counterfactual_scores(cf_result["variants"], cf_result["original_score"])
        st.plotly_chart(fig, use_container_width=True)

    with tab_table:
        rows = [{"Profile": "ORIGINAL (Baseline)",
                 "Score": f"{cf_result['original_score']:.4f}",
                 "Decision": "✅ Approved" if cf_result["original_approved"] else "❌ Denied",
                 "Score Δ": "—", "Decision Δ": "—"}]
        for v in cf_result["variants"]:
            rows.append({
                "Profile": v["profile_id"],
                "Score": f"{v['score']:.4f}",
                "Decision": "✅ Approved" if v["approved"] else "❌ Denied",
                "Score Δ": f"{v['score_delta']:+.4f}",
                "Decision Δ": "↕️ REVERSED" if v["decision_delta"] != 0 else "Same",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        if cf_result["any_reversal"]:
            st.error("⚠️ **Decision reversal detected.** Identical financial profiles received different outcomes — strong indicator of algorithmic bias.")

    with tab_factors:
        chosen = st.selectbox("Select profile to inspect", [d.profile_id for d in decisions])
        dec = next((d for d in decisions if d.profile_id == chosen), decisions[0])
        fig2 = plot_decision_factors(dec.decision_factors, dec.profile_id)
        st.plotly_chart(fig2, use_container_width=True)
        if dec.denial_reasons:
            st.markdown("**Denial Reasons:**")
            for r in dec.denial_reasons:
                st.markdown(f"- {r}")


# ── Batch Dataset ──────────────────────────────────────────────────────────────

def _batch_dataset_audit():
    st.markdown("### Batch Dataset Audit")

    df = st.session_state.get("dataset_df")
    if df is None:
        st.warning("⚠️ No dataset loaded. Go to **Upload Data** to load a CSV or generate a sample dataset.")
        return

    st.success(f"✅ Dataset ready: **{len(df):,} records** — {st.session_state.get('data_source', '')}")

    audit_attr = st.multiselect(
        "Protected attributes to audit",
        ["gender", "race", "age_group", "disability_status"],
        default=["race", "gender"],
    )

    if st.button("🚀 Run Full Batch Audit", type="primary", use_container_width=True):
        progress = st.progress(0, "Agent 3: Running decisions on dataset...")
        dec_agent  = DecisionSimulatorAgent()
        decision_df = dec_agent.decide_dataframe(df)
        progress.progress(50, "Agent 4: Computing fairness metrics...")
        bias_agent = BiasAuditorAgent()

        full_df = pd.concat([df.reset_index(drop=True), decision_df.reset_index(drop=True)], axis=1)
        # Add age_group column
        def age_group(a):
            if a < 30: return "Young Adult (18-29)"
            elif a < 45: return "Adult (30-44)"
            elif a < 60: return "Middle-aged (45-59)"
            else: return "Senior (60+)"
        full_df["age_group"] = full_df["age"].apply(age_group)

        report = bias_agent.audit_dataset(df, decision_df)
        progress.progress(100, "✅ Batch audit complete!")
        progress.empty()

        st.session_state["audit_report"]   = report
        st.session_state["audit_full_df"]  = full_df
        st.session_state["decision_df"]    = decision_df
        st.session_state["bias_agent"]     = bias_agent

        metrics_df = bias_agent.metrics_to_dataframe(report.metrics_by_attribute)
        st.session_state["metrics_df"] = metrics_df

        st.success(f"🎯 Audit complete! Fairness Score: **{report.audit_score:.1f}/100**")
        st.info("📊 Head to the **Analytics** page to explore charts, or **Reports** to download the compliance report.")

        # Quick summary table
        if not metrics_df.empty:
            st.markdown("#### Quick Bias Summary")
            st.dataframe(metrics_df, use_container_width=True)

        # Approval rate bar for first attribute
        if audit_attr and audit_attr[0] in full_df.columns:
            from utils.visualizations import plot_approval_rates_by_group
            fig = plot_approval_rates_by_group(full_df, audit_attr[0])
            st.plotly_chart(fig, use_container_width=True)
