"""
Visualization utilities for the Shadow Applicant Dashboard.
All charts use Plotly for interactivity.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

# ── Design Tokens ─────────────────────────────────────────
PALETTE = {
    "primary": "#6C63FF",
    "success": "#00D4A1",
    "danger": "#FF4B6E",
    "warning": "#FFB347",
    "bg_dark": "#0E1117",
    "bg_card": "#161B22",
    "bg_surface": "#1E2430",
    "text_primary": "#E6EDF3",
    "text_muted": "#8B949E",
    "border": "#30363D",
}

FAIR_COLOR = "#00D4A1"
BIASED_COLOR = "#FF4B6E"
MARGINAL_COLOR = "#FFB347"
NEUTRAL_COLOR = "#6C63FF"

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=PALETTE["text_primary"]),
    margin=dict(l=20, r=20, t=50, b=20),
)


def _apply_layout(fig, title: str = "", height: int = 400) -> go.Figure:
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=16, color=PALETTE["text_primary"])),
        height=height,
        xaxis=dict(gridcolor=PALETTE["border"], zeroline=False),
        yaxis=dict(gridcolor=PALETTE["border"], zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=PALETTE["border"]),
    )
    return fig


# ─────────────────────────────────────────────────────────
# Chart 1: Approval Rate Bar Chart by Group
# ─────────────────────────────────────────────────────────

def plot_approval_rates_by_group(
    df: pd.DataFrame, attribute: str, decision_col: str = "approved"
) -> go.Figure:
    """Grouped bar chart showing approval rates by protected group."""
    grp = df.groupby(attribute)[decision_col].agg(["mean", "count"]).reset_index()
    grp.columns = [attribute, "approval_rate", "count"]
    grp = grp.sort_values("approval_rate", ascending=True)

    colors = [
        FAIR_COLOR if r >= 0.50 else BIASED_COLOR
        for r in grp["approval_rate"]
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grp["approval_rate"] * 100,
        y=grp[attribute],
        orientation="h",
        marker=dict(color=colors, line=dict(color=PALETTE["border"], width=0.5)),
        text=[f"{r:.1%}" for r in grp["approval_rate"]],
        textposition="outside",
        hovertemplate=(
            f"<b>%{{y}}</b><br>Approval Rate: %{{x:.1f}}%<br>"
            f"Applicants: %{{customdata}}<extra></extra>"
        ),
        customdata=grp["count"],
    ))

    fig.add_vline(x=80, line_dash="dash", line_color=MARGINAL_COLOR,
                  annotation_text="80% Fairness Threshold", annotation_position="top right")
    _apply_layout(fig, f"Approval Rate by {attribute.replace('_', ' ').title()}", height=max(350, len(grp) * 45 + 80))
    fig.update_layout(xaxis_title="Approval Rate (%)", yaxis_title="")
    return fig


# ─────────────────────────────────────────────────────────
# Chart 2: Counterfactual Score Comparison
# ─────────────────────────────────────────────────────────

def plot_counterfactual_scores(results: List[Dict], original_score: float) -> go.Figure:
    """Horizontal bar chart comparing scores across counterfactual profiles."""
    labels = ["ORIGINAL"] + [r.get("profile_id", "?").replace("CF_", "") for r in results]
    scores = [original_score] + [r["score"] for r in results]
    approved = [original_score >= 0.5] + [r["approved"] for r in results]

    colors = [FAIR_COLOR if a else BIASED_COLOR for a in approved]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=scores,
        y=labels,
        orientation="h",
        marker=dict(color=colors),
        text=[f"{s:.3f}" for s in scores],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Score: %{x:.4f}<extra></extra>",
    ))
    fig.add_vline(x=0.5, line_dash="dot", line_color="white",
                  annotation_text="Decision Threshold (0.5)", annotation_position="top right")
    _apply_layout(fig, "Counterfactual Score Comparison", height=max(300, len(labels) * 40 + 80))
    fig.update_layout(xaxis=dict(range=[0, 1.05], title="Approval Score"),
                      yaxis_title="")
    return fig


# ─────────────────────────────────────────────────────────
# Chart 3: Bias Heatmap
# ─────────────────────────────────────────────────────────

def plot_bias_heatmap(metrics_df: pd.DataFrame) -> go.Figure:
    """Heatmap of Disparate Impact Ratio across all protected groups."""
    if metrics_df.empty:
        fig = go.Figure()
        _apply_layout(fig, "Bias Heatmap (No data)")
        return fig

    pivot_data = {}
    for _, row in metrics_df.iterrows():
        attr = row["Attribute"]
        group = row["Comparison Group"]
        dir_val = row["DIR"]
        if attr not in pivot_data:
            pivot_data[attr] = {}
        pivot_data[attr][group] = dir_val

    attrs = list(pivot_data.keys())
    all_groups = sorted(set(g for groups in pivot_data.values() for g in groups.keys()))

    matrix = []
    for attr in attrs:
        row_vals = [pivot_data[attr].get(g, np.nan) for g in all_groups]
        matrix.append(row_vals)

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=all_groups,
        y=attrs,
        colorscale=[
            [0.0, BIASED_COLOR],
            [0.5, MARGINAL_COLOR],
            [0.8, "#A8FF78"],
            [1.0, FAIR_COLOR],
        ],
        zmin=0.4, zmax=1.2,
        text=[[f"{v:.2f}" if not np.isnan(v) else "N/A" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="Attribute: %{y}<br>Group: %{x}<br>DIR: %{z:.3f}<extra></extra>",
        colorbar=dict(
            title="DIR",
            tickvals=[0.4, 0.6, 0.8, 1.0, 1.2],
            ticktext=["0.4 (Severe)", "0.6 (High)", "0.8 (Threshold)", "1.0 (Fair)", "1.2 (Favored)"],
            bgcolor="rgba(0,0,0,0)",
            tickfont=dict(color=PALETTE["text_primary"]),
        ),
    ))
    _apply_layout(fig, "Disparate Impact Ratio Heatmap", height=max(300, len(attrs) * 70 + 100))
    return fig


# ─────────────────────────────────────────────────────────
# Chart 4: SPD / DIR Combined Bar
# ─────────────────────────────────────────────────────────

def plot_metrics_comparison(metrics_df: pd.DataFrame) -> go.Figure:
    """Multi-metric comparison bar chart."""
    if metrics_df.empty:
        fig = go.Figure()
        _apply_layout(fig, "Fairness Metrics Comparison (No data)")
        return fig

    labels = [f"{row['Attribute']}:{row['Comparison Group']}" for _, row in metrics_df.iterrows()]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Disparate Impact Ratio (DIR)", "Statistical Parity Difference (SPD)"],
        shared_yaxes=True,
    )

    dir_colors = [FAIR_COLOR if v >= 0.8 else (MARGINAL_COLOR if v >= 0.6 else BIASED_COLOR) for v in metrics_df["DIR"]]
    spd_colors = [FAIR_COLOR if abs(v) <= 0.1 else (MARGINAL_COLOR if abs(v) <= 0.2 else BIASED_COLOR) for v in metrics_df["SPD"]]

    fig.add_trace(go.Bar(
        y=labels, x=metrics_df["DIR"], orientation="h",
        marker_color=dir_colors, name="DIR",
        text=[f"{v:.3f}" for v in metrics_df["DIR"]], textposition="outside",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        y=labels, x=metrics_df["SPD"], orientation="h",
        marker_color=spd_colors, name="SPD",
        text=[f"{v:+.3f}" for v in metrics_df["SPD"]], textposition="outside",
    ), row=1, col=2)

    fig.update_layout(**CHART_LAYOUT, height=max(350, len(labels) * 42 + 80),
                      title_text="Fairness Metrics by Protected Group",
                      showlegend=False)
    fig.add_vline(x=0.8, line_dash="dash", line_color=MARGINAL_COLOR, row=1, col=1)
    fig.add_vline(x=0.0, line_dash="dot", line_color="white", row=1, col=2)
    return fig


# ─────────────────────────────────────────────────────────
# Chart 5: Score Distribution by Group
# ─────────────────────────────────────────────────────────

def plot_score_distribution(df: pd.DataFrame, attribute: str, score_col: str = "score") -> go.Figure:
    """Violin/box plot of score distributions by group."""
    if attribute not in df.columns or score_col not in df.columns:
        fig = go.Figure()
        _apply_layout(fig, "Score Distribution")
        return fig

    groups = df[attribute].unique()
    palette = px.colors.qualitative.Set3
    fig = go.Figure()

    for i, grp in enumerate(sorted(groups)):
        grp_data = df[df[attribute] == grp][score_col]
        fig.add_trace(go.Violin(
            y=grp_data,
            name=str(grp),
            box_visible=True,
            meanline_visible=True,
            line_color=palette[i % len(palette)],
            fillcolor=palette[i % len(palette)],
            opacity=0.7,
        ))

    fig.add_hline(y=0.5, line_dash="dash", line_color="white",
                  annotation_text="Decision Threshold", annotation_position="top right")
    _apply_layout(fig, f"Score Distribution by {attribute.replace('_', ' ').title()}", height=420)
    fig.update_layout(yaxis_title="Approval Score", xaxis_title="")
    return fig


# ─────────────────────────────────────────────────────────
# Chart 6: Audit Score Gauge
# ─────────────────────────────────────────────────────────

def plot_fairness_gauge(audit_score: float) -> go.Figure:
    """Gauge chart for overall fairness score."""
    color = FAIR_COLOR if audit_score >= 80 else (MARGINAL_COLOR if audit_score >= 60 else BIASED_COLOR)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=audit_score,
        delta={"reference": 80, "increasing": {"color": FAIR_COLOR}, "decreasing": {"color": BIASED_COLOR}},
        title={"text": "Overall Fairness Score", "font": {"size": 18, "color": PALETTE["text_primary"]}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": PALETTE["text_muted"]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 60], "color": "rgba(255,75,110,0.2)"},
                {"range": [60, 80], "color": "rgba(255,179,71,0.2)"},
                {"range": [80, 100], "color": "rgba(0,212,161,0.2)"},
            ],
            "threshold": {
                "line": {"color": PALETTE["text_primary"], "width": 3},
                "thickness": 0.8,
                "value": 80,
            },
        },
        number={"suffix": "/100", "font": {"size": 36, "color": color}},
    ))
    fig.update_layout(**CHART_LAYOUT, height=280)
    return fig


# ─────────────────────────────────────────────────────────
# Chart 7: Feature Importance / Decision Factors
# ─────────────────────────────────────────────────────────

def plot_decision_factors(factors: Dict[str, float], profile_id: str = "") -> go.Figure:
    """Horizontal bar showing contribution of each feature to the decision score."""
    labels = list(factors.keys())
    values = list(factors.values())
    colors = [FAIR_COLOR if v >= 0 else BIASED_COLOR for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.4f}" for v in values],
        textposition="outside",
    ))
    _apply_layout(fig, f"Decision Factor Contributions — {profile_id}", height=360)
    fig.update_layout(xaxis_title="Score Contribution", yaxis_title="")
    fig.add_vline(x=0, line_dash="solid", line_color=PALETTE["text_muted"])
    return fig
