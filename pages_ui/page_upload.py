"""
Page: Upload Data — CSV upload and sample dataset loader.
"""
import streamlit as st
import pandas as pd
from agents.profile_generator import ProfileGeneratorAgent


REQUIRED_COLS = [
    "age", "gender", "race", "marital_status", "disability_status",
    "income", "credit_score", "loan_amount", "debt_to_income",
    "years_employed", "num_dependents", "education_years",
    "employment_type", "loan_purpose", "collateral",
]


def render():
    st.markdown("## 📂 Upload Applicant Data")
    st.markdown("Upload a CSV dataset or use the built-in sample dataset to begin auditing.")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Option 1 — Upload CSV File")
        uploaded = st.file_uploader(
            "Drag and drop your CSV file here",
            type=["csv"],
            help=f"Required columns: {', '.join(REQUIRED_COLS)}",
        )

        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                missing = [c for c in REQUIRED_COLS if c not in df.columns]
                if missing:
                    st.error(f"❌ Missing required columns: **{', '.join(missing)}**")
                else:
                    df = df[REQUIRED_COLS].dropna().reset_index(drop=True)
                    st.session_state["dataset_df"] = df
                    st.session_state["data_source"] = f"📄 {uploaded.name}"
                    st.success(f"✅ Loaded **{len(df):,}** applicant records successfully.")
                    _preview_dataset(df)
            except Exception as e:
                st.error(f"❌ Failed to parse file: {e}")

    with col2:
        st.markdown("### Option 2 — Use Sample Dataset")
        st.markdown("""
        The built-in sample dataset contains **50 applicants** with
        intentionally varied demographics and embedded bias patterns — 
        ideal for demonstrating the audit engine.
        """)
        n_rows = st.slider("Number of synthetic records to generate", 50, 500, 100, step=50)

        if st.button("🔄 Load Sample Dataset", use_container_width=True, type="primary"):
            with st.spinner("Generating synthetic dataset..."):
                agent = ProfileGeneratorAgent()
                df = agent.build_sample_dataset(n=n_rows)
                st.session_state["dataset_df"] = df
                st.session_state["data_source"] = f"🧪 Synthetic ({n_rows} records)"
            st.success(f"✅ Generated **{n_rows}** synthetic applicant profiles.")
            _preview_dataset(df)

        st.markdown("---")
        st.markdown("#### 📥 Download Sample Template")
        try:
            with open("data/sample_dataset.csv", "rb") as f:
                st.download_button(
                    "Download CSV Template",
                    data=f,
                    file_name="shadow_applicant_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        except FileNotFoundError:
            pass

    # If dataset already in session
    if st.session_state.get("dataset_df") is not None and not uploaded:
        df = st.session_state["dataset_df"]
        st.markdown("---")
        st.info(f"📊 Current dataset: **{st.session_state.get('data_source', 'Unknown')}** — {len(df):,} records loaded.")
        _preview_dataset(df)


def _preview_dataset(df: pd.DataFrame):
    st.markdown("#### 👁 Data Preview")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Records", f"{len(df):,}")
    col_b.metric("Features", str(len(df.columns)))
    col_c.metric("Protected Attributes", "5")

    tab1, tab2 = st.tabs(["📋 Sample Rows", "📈 Column Stats"])
    with tab1:
        st.dataframe(df.head(10), use_container_width=True, height=280)
    with tab2:
        cat_cols = df.select_dtypes(include="object").columns.tolist()
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if cat_cols:
            chosen = st.selectbox("Categorical column distribution", cat_cols)
            dist = df[chosen].value_counts().reset_index()
            dist.columns = [chosen, "Count"]
            dist["Share"] = (dist["Count"] / len(df) * 100).round(1).astype(str) + "%"
            st.dataframe(dist, use_container_width=True)
        if num_cols:
            st.dataframe(df[num_cols].describe().T.round(2), use_container_width=True)
