"""
The Shadow Applicant: Enterprise AI Fairness Auditor
Main Streamlit Application Entry Point
"""
import streamlit as st

st.set_page_config(
    page_title="Shadow Applicant — AI Fairness Auditor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1117 0%, #161B22 100%) !important;
    border-right: 1px solid #21262D;
}
[data-testid="stSidebar"] .block-container { padding: 0 !important; }

/* ── Main area ── */
.main .block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px; }
[data-testid="stAppViewContainer"] { background: #0E1117; }

/* ── Hero Banner ── */
.hero-banner {
    display: flex; align-items: center; gap: 18px;
    background: linear-gradient(135deg, #1a1040 0%, #0f2027 50%, #141e30 100%);
    border: 1px solid #30363D; border-radius: 16px;
    padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 8px 32px rgba(108,99,255,0.15);
}
.hero-icon { font-size: 42px; }
.hero-title {
    font-size: 18px; font-weight: 500; color: #C9D1D9; line-height: 1.6;
}

/* ── KPI Cards ── */
.kpi-card {
    background: #161B22; border: 1px solid #21262D; border-radius: 12px;
    padding: 20px 18px; text-align: center; margin-bottom: 12px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
.kpi-value { font-size: 30px; font-weight: 800; color: #E6EDF3; line-height: 1.2; }
.kpi-label { font-size: 13px; color: #8B949E; margin-top: 4px; font-weight: 500; }
.kpi-sub { font-size: 11px; color: #6E7681; margin-top: 2px; }

/* ── Agent Cards ── */
.agent-card {
    display: flex; justify-content: space-between; align-items: center;
    background: #161B22; border: 1px solid #21262D; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 8px; transition: all 0.2s;
}
.agent-active { border-left: 3px solid #00D4A1 !important; }
.agent-idle   { border-left: 3px solid #30363D !important; }
.agent-id   { font-size: 12px; font-weight: 700; color: #6C63FF; min-width: 62px; }
.agent-name { font-size: 13px; color: #C9D1D9; flex: 1; padding: 0 10px; }
.agent-badge { font-size: 12px; color: #8B949E; }

/* ── Finding Cards ── */
.finding-card {
    background: rgba(255,75,110,0.07); border-left: 3px solid #FF4B6E;
    border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;
    color: #E6EDF3; font-size: 14px; line-height: 1.5;
}

/* ── Sidebar Nav Buttons ── */
.nav-header {
    padding: 24px 20px 10px; font-size: 11px; font-weight: 700;
    color: #6E7681; letter-spacing: 2px; text-transform: uppercase;
}
.nav-item {
    display: flex; align-items: center; gap: 12px;
    padding: 11px 20px; cursor: pointer; border-radius: 8px;
    margin: 2px 8px; color: #8B949E; font-size: 14px; font-weight: 500;
    transition: all 0.15s; text-decoration: none; border: none;
    background: transparent; width: calc(100% - 16px);
}
.nav-item:hover { background: #21262D; color: #E6EDF3; }
.nav-item.active { background: rgba(108,99,255,0.18); color: #6C63FF; font-weight: 600; }
.nav-icon { font-size: 18px; width: 22px; text-align: center; }

/* ── Metric / Dataframe tables ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
.stDataFrame thead tr th {
    background: #161B22 !important; color: #8B949E !important; font-size: 12px !important;
}

/* ── Forms ── */
[data-testid="stForm"] {
    background: #161B22; border: 1px solid #21262D;
    border-radius: 14px; padding: 24px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: #161B22; border-radius: 10px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; color: #8B949E; font-weight: 500; font-size: 13px;
}
.stTabs [aria-selected="true"] { background: #6C63FF !important; color: white !important; }

/* ── Buttons ── */
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #6C63FF, #8B83FF) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; letter-spacing: 0.3px !important;
    transition: all 0.2s !important;
}
.stButton>button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(108,99,255,0.4) !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div { background: linear-gradient(90deg,#6C63FF,#00D4A1) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0E1117; }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484F58; }

/* ── Divider ── */
hr { border-color: #21262D !important; margin: 24px 0 !important; }

/* ── Metric widgets ── */
[data-testid="stMetric"] {
    background: #161B22; border: 1px solid #21262D; border-radius: 10px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] p { color: #8B949E !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700 !important; color: #E6EDF3 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State Defaults ────────────────────────────────────────────────────
for key in ["page", "dataset_df", "audit_report", "metrics_df",
            "audit_full_df", "decision_df", "cf_results",
            "cf_profiles", "cf_decisions", "data_source"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state["page"] is None:
    st.session_state["page"] = "Dashboard"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:24px 20px 8px;text-align:center">
        <div style="font-size:32px">⚖️</div>
        <div style="font-size:16px;font-weight:800;color:#E6EDF3;margin-top:6px">Shadow Applicant</div>
        <div style="font-size:11px;color:#6C63FF;font-weight:600;letter-spacing:1.5px;margin-top:2px">
            ENTERPRISE AI FAIRNESS AUDITOR
        </div>
        <div style="height:1px;background:#21262D;margin:16px 0"></div>
    </div>
    """, unsafe_allow_html=True)

    NAV_ITEMS = [
        ("Dashboard",    "🏠", "Overview & system status"),
        ("Upload Data",  "📂", "Load applicant dataset"),
        ("Run Audit",    "🔬", "Counterfactual audit engine"),
        ("Analytics",    "📈", "Bias charts & heatmaps"),
        ("Reports",      "📄", "Compliance report export"),
    ]

    st.markdown('<div class="nav-header">Navigation</div>', unsafe_allow_html=True)
    for page_name, icon, desc in NAV_ITEMS:
        is_active = st.session_state["page"] == page_name
        css_class = "nav-item active" if is_active else "nav-item"
        if st.button(f"{icon}  {page_name}", key=f"nav_{page_name}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state["page"] = page_name
            st.rerun()

    st.markdown("---")

    # Status indicators
    st.markdown('<div class="nav-header">Status</div>', unsafe_allow_html=True)
    statuses = [
        ("Dataset", st.session_state["dataset_df"] is not None),
        ("Batch Audit", st.session_state["audit_report"] is not None),
        ("CF Audit", st.session_state["cf_results"] is not None),
    ]
    for label, active in statuses:
        dot = "🟢" if active else "🔴"
        text_color = "#00D4A1" if active else "#FF4B6E"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:6px 20px;">'
            f'{dot} <span style="font-size:13px;color:{text_color}">{label}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("""
    <div style="padding:12px 20px 20px;font-size:11px;color:#6E7681;line-height:1.6">
        <b style="color:#8B949E">Frameworks</b><br>
        ECOA · FCRA · EU AI Act<br>
        EEOC 4/5ths Rule · ADA · ADEA<br><br>
        <b style="color:#8B949E">Metrics</b><br>
        DIR · SPD · DoD · Score Gap
    </div>
    """, unsafe_allow_html=True)

# ── Page Routing ──────────────────────────────────────────────────────────────
page = st.session_state["page"]

if page == "Dashboard":
    from pages_ui.page_dashboard import render
    render()
elif page == "Upload Data":
    from pages_ui.page_upload import render
    render()
elif page == "Run Audit":
    from pages_ui.page_audit import render
    render()
elif page == "Analytics":
    from pages_ui.page_analytics import render
    render()
elif page == "Reports":
    from pages_ui.page_reports import render
    render()
