"""
Report Generator — Compliance Report Module
Generates a formatted, downloadable audit report.
"""

import io
import datetime
import pandas as pd
from typing import Optional
from agents.bias_auditor import AuditReport, FairnessMetrics


def _divider(char="─", width=72):
    return char * width


def _section(title: str) -> str:
    return f"\n{_divider()}\n  {title.upper()}\n{_divider()}\n"


def generate_text_report(
    report: AuditReport,
    metrics_df: pd.DataFrame,
    audit_name: str = "Unnamed Audit",
    model_name: str = "Enterprise Loan Decision Model v2.1",
    auditor_name: str = "Shadow Applicant Audit Engine",
) -> str:
    """
    Generate a comprehensive plain-text compliance report.
    Returns a string suitable for download or display.
    """
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = []

    # ── Header ───────────────────────────────────────────────
    lines += [
        "═" * 72,
        "   THE SHADOW APPLICANT",
        "   Enterprise AI Fairness Auditor",
        "   Compliance & Bias Audit Report",
        "═" * 72,
        "",
        f"  Report ID     : SA-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        f"  Audit Name    : {audit_name}",
        f"  Generated On  : {now}",
        f"  Auditor Engine: {auditor_name}",
        f"  Model Audited : {model_name}",
        f"  Framework     : ECOA · FCRA · EU AI Act · EEOC 4/5ths Rule",
        "",
        "  AI systems are making decisions that affect lives.",
        "  This platform ensures those decisions are fair.",
        "",
    ]

    # ── Executive Summary ────────────────────────────────────
    lines.append(_section("1. Executive Summary"))
    severity_label = (
        "🔴 CRITICAL — Immediate remediation required"
        if report.audit_score < 60
        else ("🟡 MODERATE — Remediation recommended" if report.audit_score < 80
              else "🟢 COMPLIANT — System within fairness thresholds")
    )
    lines += [
        f"  Overall Fairness Score : {report.audit_score:.1f} / 100",
        f"  Assessment             : {severity_label}",
        f"  Total Profiles Audited : {report.total_profiles:,}",
        f"  Overall Approval Rate  : {report.overall_approval_rate:.1%}",
        f"  Protected Attributes   : Gender, Race, Age Group, Disability Status",
        "",
        "  Fairness Score Interpretation:",
        "    ≥ 80  : Compliant — meets EEOC 4/5ths rule and EU AI Act requirements",
        "    60–79 : Moderate risk — bias present, remediation recommended",
        "    < 60  : Critical — potential regulatory violation, halt deployment",
        "",
    ]

    # ── Key Findings ─────────────────────────────────────────
    lines.append(_section("2. Critical Findings"))
    for i, finding in enumerate(report.critical_findings, 1):
        lines.append(f"  [{i}] {finding}")
    lines.append("")

    # ── Fairness Metrics Table ───────────────────────────────
    lines.append(_section("3. Fairness Metrics by Protected Group"))

    if not metrics_df.empty:
        lines += [
            f"  {'Attribute':<18} {'Comparison Group':<20} {'Ref Rate':>8} {'Cmp Rate':>8} "
            f"{'DIR':>7} {'SPD':>7} {'Severity':<30}",
            f"  {'-'*18} {'-'*20} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*30}",
        ]
        for _, row in metrics_df.iterrows():
            lines.append(
                f"  {str(row['Attribute']):<18} {str(row['Comparison Group']):<20} "
                f"  {str(row['Reference Approval %']):>6} {str(row['Comparison Approval %']):>8} "
                f"  {float(row['DIR']):>5.3f} {float(row['SPD']):>+6.3f}  {str(row['Bias Severity']):<30}"
            )
    else:
        lines.append("  No dataset metrics available.")
    lines.append("")

    # ── Metric Definitions ───────────────────────────────────
    lines.append(_section("4. Metric Definitions & Regulatory Thresholds"))
    lines += [
        "  Disparate Impact Ratio (DIR)",
        "    Formula  : Approval Rate (protected group) / Approval Rate (reference group)",
        "    Threshold: DIR < 0.80 indicates potential illegal discrimination (EEOC 4/5ths Rule)",
        "    Legal Ref: Griggs v. Duke Power Co. (1971); ECOA 12 CFR Part 202",
        "",
        "  Statistical Parity Difference (SPD)",
        "    Formula  : Approval Rate (protected) − Approval Rate (reference)",
        "    Threshold: |SPD| > 0.10 signals meaningful disparity",
        "    Legal Ref: EU AI Act Article 9 — Risk Management for High-Risk AI",
        "",
        "  Delta of Discrimination (DoD)",
        "    Formula  : |SPD| — magnitude of the approval rate gap",
        "    Threshold: DoD > 0.20 triggers mandatory review",
        "",
        "  Average Score Gap",
        "    Formula  : Mean decision score (protected) − Mean score (reference)",
        "    Threshold: Gap > 0.05 warrants investigation of scoring pipeline",
        "",
    ]

    # ── Most Biased Attribute ────────────────────────────────
    if report.most_biased_attribute:
        lines.append(_section("5. Highest-Risk Finding"))
        lines += [
            f"  Most Biased Attribute : {report.most_biased_attribute}",
            f"  Most Affected Group   : {report.most_biased_group}",
            "",
            "  This group shows the greatest deviation from the reference population",
            "  and presents the highest risk of regulatory non-compliance.",
            "",
        ]

    # ── Recommendations ──────────────────────────────────────
    lines.append(_section("6. Remediation Recommendations"))
    for i, rec in enumerate(report.recommendations, 1):
        lines.append(f"  {i:>2}. {rec}")
    lines.append("")

    # ── Regulatory Framework ────────────────────────────────
    lines.append(_section("7. Applicable Regulatory Frameworks"))
    lines += [
        "  United States:",
        "    • Equal Credit Opportunity Act (ECOA) — prohibits credit discrimination",
        "    • Fair Housing Act (FHA) — prohibits housing discrimination",
        "    • EEOC Uniform Guidelines — 4/5ths rule for adverse impact",
        "    • Age Discrimination in Employment Act (ADEA)",
        "    • Americans with Disabilities Act (ADA) — Section 501",
        "",
        "  European Union:",
        "    • EU AI Act (2024) — Article 5 (prohibited practices), Article 9 (risk management)",
        "    • GDPR Article 22 — right to explanation for automated decisions",
        "    • EU Equality Directives 2000/43/EC and 2006/54/EC",
        "",
        "  International:",
        "    • ISO/IEC TR 24027:2021 — Bias in AI systems",
        "    • NIST AI RMF 1.0 — AI Risk Management Framework",
        "",
    ]

    # ── Audit Methodology ────────────────────────────────────
    lines.append(_section("8. Audit Methodology"))
    lines += [
        "  This audit was conducted using the Shadow Applicant methodology:",
        "",
        "  Step 1 — Profile Generation (Agent 1)",
        "    Applicant profiles structured with 15 financial and demographic features.",
        "",
        "  Step 2 — Counterfactual Generation (Agent 2)",
        "    For each profile, shadow applicants are generated by systematically",
        "    varying protected attributes while holding financial merit constant.",
        "    This isolates the causal effect of protected attributes on decisions.",
        "",
        "  Step 3 — Decision Simulation (Agent 3)",
        "    Each profile is evaluated by the audited decision model.",
        "    Model type: Calibrated probabilistic scoring (logistic regression style)",
        "    Approval threshold: 0.50 (50th percentile score)",
        "",
        "  Step 4 — Bias Analysis (Agent 4)",
        "    Fairness metrics computed across all protected groups.",
        "    Reference population: Majority demographic within each attribute.",
        "",
    ]

    # ── Footer ───────────────────────────────────────────────
    lines += [
        "═" * 72,
        "",
        "  This report is generated by The Shadow Applicant Audit Engine.",
        "  For questions, contact your AI Risk & Compliance team.",
        "  Report generated automatically — human review recommended before action.",
        "",
        f"  © {datetime.datetime.utcnow().year} Shadow Applicant Enterprise | CONFIDENTIAL",
        "",
        "═" * 72,
    ]

    return "\n".join(lines)


def generate_csv_summary(metrics_df: pd.DataFrame) -> str:
    """Return metrics as CSV string for download."""
    return metrics_df.to_csv(index=False)


def report_to_bytes(text: str) -> bytes:
    """Convert report string to downloadable bytes."""
    return text.encode("utf-8")
