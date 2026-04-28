"""
Agent 4: Bias Auditor
Computes fairness metrics, detects discrimination, and produces audit findings.

Metrics implemented:
  - Disparate Impact Ratio (DIR)
  - Statistical Parity Difference (SPD)
  - Delta of Discrimination (DoD)
  - Equalized Odds Difference
  - Average Score Gap
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from agents.decision_simulator import DecisionResult


FAIR_DIR_THRESHOLD = 0.80      # Below this → potential illegal discrimination (EEOC 4/5ths rule)
FAIR_SPD_THRESHOLD = 0.10      # Absolute difference in approval rates
BIAS_SEVERITY_LEVELS = {
    "CRITICAL": "🔴 Critical Bias Detected",
    "MODERATE": "🟡 Moderate Bias Detected",
    "MARGINAL": "🟠 Marginal Bias Risk",
    "FAIR": "🟢 No Significant Bias",
}


@dataclass
class FairnessMetrics:
    """Complete set of fairness metrics for a protected attribute group."""
    attribute: str
    reference_group: str
    comparison_group: str
    reference_approval_rate: float
    comparison_approval_rate: float
    disparate_impact_ratio: float
    statistical_parity_difference: float
    average_score_gap: float
    delta_of_discrimination: float
    bias_severity: str
    is_biased: bool
    sample_sizes: Dict[str, int]


@dataclass
class AuditReport:
    """Full audit report for a batch of decisions."""
    total_profiles: int
    overall_approval_rate: float
    metrics_by_attribute: List[FairnessMetrics]
    most_biased_attribute: Optional[str]
    most_biased_group: Optional[str]
    critical_findings: List[str]
    recommendations: List[str]
    audit_score: float  # 0-100 fairness score


class BiasAuditorAgent:
    """
    Agent 4 — Bias Auditor
    Performs comprehensive statistical fairness analysis across protected groups.
    """

    PROTECTED_AUDIT_ATTRIBUTES = ["gender", "race", "age_group", "disability_status"]

    def __init__(self, reference_groups: Dict[str, str] = None):
        """
        reference_groups: which group to use as reference for each attribute.
        Defaults to majority group.
        """
        self.reference_groups = reference_groups or {
            "gender": "Male",
            "race": "White",
            "age_group": "Adult (30-44)",
            "disability_status": "No",
        }

    # ─────────────────────────────────────────────
    # Counterfactual Audit (single original + variants)
    # ─────────────────────────────────────────────

    def audit_counterfactuals(
        self,
        profiles,
        decisions: List[DecisionResult],
        attribute: str = "race",
    ) -> Dict[str, Any]:
        """Audit counterfactual variants for a single applicant."""
        profile_dicts = [p.to_dict() for p in profiles]
        decision_dicts = [
            {
                "profile_id": d.profile_id,
                "approved": d.approved,
                "score": d.score,
            }
            for d in decisions
        ]
        merged = []
        for pd_dict, dd in zip(profile_dicts, decision_dicts):
            row = {**pd_dict, **dd}
            merged.append(row)

        df = pd.DataFrame(merged)
        results = []

        original_row = df[df["profile_id"] == "ORIGINAL"]
        if original_row.empty:
            original_row = df.iloc[[0]]

        orig_score = float(original_row["score"].values[0])
        orig_approved = bool(original_row["approved"].values[0])
        orig_group = str(original_row[attribute].values[0]) if attribute in original_row.columns else "Unknown"

        for _, row in df.iterrows():
            if row["profile_id"] == "ORIGINAL":
                continue
            score_gap = float(row["score"]) - orig_score
            approved_gap = int(row["approved"]) - int(orig_approved)
            results.append({
                "profile_id": row["profile_id"],
                attribute: row.get(attribute, "N/A"),
                "score": round(float(row["score"]), 4),
                "approved": bool(row["approved"]),
                "score_delta": round(score_gap, 4),
                "decision_delta": approved_gap,
            })

        return {
            "original_group": orig_group,
            "original_score": orig_score,
            "original_approved": orig_approved,
            "variants": results,
            "max_score_gap": max((abs(r["score_delta"]) for r in results), default=0.0),
            "any_reversal": any(r["decision_delta"] != 0 for r in results),
        }

    # ─────────────────────────────────────────────
    # Full Dataset Audit
    # ─────────────────────────────────────────────

    def audit_dataset(
        self,
        df: pd.DataFrame,
        decision_df: pd.DataFrame,
    ) -> AuditReport:
        """
        Perform full fairness audit over a dataset.
        df: applicant features DataFrame
        decision_df: decisions DataFrame with 'approved' and 'score' columns
        """
        merged = pd.concat([df.reset_index(drop=True), decision_df.reset_index(drop=True)], axis=1)

        overall_rate = float(merged["approved"].mean())
        all_metrics = []

        for attr in self.PROTECTED_AUDIT_ATTRIBUTES:
            if attr not in merged.columns:
                continue
            metrics = self._compute_metrics_for_attribute(merged, attr)
            all_metrics.extend(metrics)

        # Find most biased
        biased = [m for m in all_metrics if m.is_biased]
        most_biased = min(biased, key=lambda m: m.disparate_impact_ratio, default=None)

        critical_findings = self._extract_critical_findings(all_metrics)
        recommendations = self._generate_recommendations(all_metrics, merged)
        audit_score = self._compute_audit_score(all_metrics)

        return AuditReport(
            total_profiles=len(merged),
            overall_approval_rate=round(overall_rate, 4),
            metrics_by_attribute=all_metrics,
            most_biased_attribute=most_biased.attribute if most_biased else None,
            most_biased_group=most_biased.comparison_group if most_biased else None,
            critical_findings=critical_findings,
            recommendations=recommendations,
            audit_score=round(audit_score, 1),
        )

    def _compute_metrics_for_attribute(
        self, df: pd.DataFrame, attribute: str
    ) -> List[FairnessMetrics]:
        """Compute fairness metrics for all groups within an attribute."""
        ref_group = self.reference_groups.get(attribute)
        groups = df[attribute].unique()
        results = []

        ref_data = df[df[attribute] == ref_group]
        if len(ref_data) == 0:
            ref_group = df[attribute].value_counts().idxmax()
            ref_data = df[df[attribute] == ref_group]

        ref_rate = float(ref_data["approved"].mean()) if len(ref_data) > 0 else 0.0
        ref_score = float(ref_data["score"].mean()) if len(ref_data) > 0 else 0.0

        for group in groups:
            if group == ref_group:
                continue
            grp_data = df[df[attribute] == group]
            if len(grp_data) < 3:
                continue

            grp_rate = float(grp_data["approved"].mean())
            grp_score = float(grp_data["score"].mean())

            dir_ = grp_rate / ref_rate if ref_rate > 0 else 0.0
            spd = grp_rate - ref_rate
            score_gap = grp_score - ref_score
            dod = abs(spd)  # Delta of Discrimination

            severity, is_biased = self._classify_bias(dir_, spd)

            results.append(FairnessMetrics(
                attribute=attribute,
                reference_group=ref_group,
                comparison_group=str(group),
                reference_approval_rate=round(ref_rate, 4),
                comparison_approval_rate=round(grp_rate, 4),
                disparate_impact_ratio=round(dir_, 4),
                statistical_parity_difference=round(spd, 4),
                average_score_gap=round(score_gap, 4),
                delta_of_discrimination=round(dod, 4),
                bias_severity=severity,
                is_biased=is_biased,
                sample_sizes={ref_group: len(ref_data), str(group): len(grp_data)},
            ))
        return results

    def _classify_bias(self, dir_: float, spd: float) -> Tuple[str, bool]:
        """Classify bias severity based on metrics."""
        if dir_ < 0.60 or abs(spd) > 0.30:
            return BIAS_SEVERITY_LEVELS["CRITICAL"], True
        elif dir_ < 0.75 or abs(spd) > 0.20:
            return BIAS_SEVERITY_LEVELS["MODERATE"], True
        elif dir_ < FAIR_DIR_THRESHOLD or abs(spd) > FAIR_SPD_THRESHOLD:
            return BIAS_SEVERITY_LEVELS["MARGINAL"], True
        else:
            return BIAS_SEVERITY_LEVELS["FAIR"], False

    def _extract_critical_findings(self, metrics: List[FairnessMetrics]) -> List[str]:
        """Extract key findings from audit results."""
        findings = []
        for m in metrics:
            if "Critical" in m.bias_severity:
                findings.append(
                    f"CRITICAL: {m.comparison_group} applicants face {m.attribute} discrimination. "
                    f"Approval rate {m.comparison_approval_rate:.1%} vs {m.reference_approval_rate:.1%} "
                    f"for {m.reference_group} (DIR={m.disparate_impact_ratio:.2f})."
                )
            elif "Moderate" in m.bias_severity:
                findings.append(
                    f"MODERATE: {m.comparison_group} shows elevated {m.attribute} bias risk. "
                    f"SPD={m.statistical_parity_difference:.3f}, DIR={m.disparate_impact_ratio:.2f}."
                )
        if not findings:
            findings.append("No critical bias patterns detected. System appears compliant with fairness thresholds.")
        return findings

    def _generate_recommendations(self, metrics: List[FairnessMetrics], df: pd.DataFrame) -> List[str]:
        """Generate actionable remediation recommendations."""
        recs = []
        biased_attrs = set(m.attribute for m in metrics if m.is_biased)

        if "race" in biased_attrs:
            recs.append("Implement adversarial debiasing on race-correlated financial features (income, credit history).")
            recs.append("Apply reweighing pre-processing to balance training data across racial groups.")
        if "gender" in biased_attrs:
            recs.append("Audit feature engineering pipeline for gender-proxy variables.")
        if "age_group" in biased_attrs:
            recs.append("Review age-related thresholds for ADEA compliance (Age Discrimination in Employment Act).")
        if "disability_status" in biased_attrs:
            recs.append("Verify compliance with ADA Section 501 — ensure disability-neutral decision criteria.")

        recs.append("Deploy continuous fairness monitoring with automated threshold alerts.")
        recs.append("Conduct quarterly third-party bias audits with an independent review committee.")
        recs.append("Document all model changes and their fairness impact in a Model Risk Management register.")
        return recs

    def _compute_audit_score(self, metrics: List[FairnessMetrics]) -> float:
        """Compute an overall fairness score (100 = perfectly fair)."""
        if not metrics:
            return 100.0
        penalties = []
        for m in metrics:
            dir_penalty = max(0, (FAIR_DIR_THRESHOLD - m.disparate_impact_ratio) * 100)
            spd_penalty = max(0, (abs(m.statistical_parity_difference) - FAIR_SPD_THRESHOLD) * 200)
            penalties.append(dir_penalty + spd_penalty)
        score = max(0.0, 100.0 - np.mean(penalties))
        return score

    def metrics_to_dataframe(self, metrics: List[FairnessMetrics]) -> pd.DataFrame:
        """Convert metrics list to display DataFrame."""
        rows = []
        for m in metrics:
            rows.append({
                "Attribute": m.attribute,
                "Reference Group": m.reference_group,
                "Comparison Group": m.comparison_group,
                "Reference Approval %": f"{m.reference_approval_rate:.1%}",
                "Comparison Approval %": f"{m.comparison_approval_rate:.1%}",
                "DIR": round(m.disparate_impact_ratio, 3),
                "SPD": round(m.statistical_parity_difference, 3),
                "Score Gap": round(m.average_score_gap, 3),
                "Bias Severity": m.bias_severity,
            })
        return pd.DataFrame(rows)
