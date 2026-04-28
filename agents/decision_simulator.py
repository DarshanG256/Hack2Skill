"""
Agent 3: Decision Simulator
Simulates an AI loan/hiring decision system using a calibrated probabilistic model.
Returns approval decisions and confidence scores.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from agents.profile_generator import ApplicantProfile


@dataclass
class DecisionResult:
    """Result from the decision simulation engine."""
    profile_id: str
    approved: bool
    score: float          # 0.0 – 1.0 probability of approval
    risk_tier: str        # Low / Medium / High / Very High
    confidence: float     # Model confidence in this decision
    decision_factors: Dict[str, float]   # Feature contribution breakdown
    denial_reasons: List[str]


RISK_TIER_THRESHOLDS = {
    "Low Risk": (0.75, 1.00),
    "Medium Risk": (0.50, 0.75),
    "High Risk": (0.30, 0.50),
    "Very High Risk": (0.00, 0.30),
}

APPROVAL_THRESHOLD = 0.50


class DecisionSimulatorAgent:
    """
    Agent 3 — Decision Simulator
    A calibrated logistic regression-style model that scores applicants.
    Uses feature weights derived from historical lending data patterns.
    Deliberately does NOT use protected attributes — bias comes from
    correlated financial features that historically disadvantaged groups.
    """

    # Feature weights (interpretable model)
    WEIGHTS = {
        "credit_score_norm": 0.42,
        "income_norm": 0.28,
        "dti_penalty": -0.35,
        "employment_stability": 0.18,
        "loan_to_income_ratio": -0.22,
        "collateral_bonus": 0.12,
        "education_bonus": 0.08,
        "dependents_penalty": -0.05,
    }

    BIAS_SEED = 137  # Reproducible randomness

    def __init__(self, model_type: str = "logistic", noise_level: float = 0.05):
        self.model_type = model_type
        self.noise_level = noise_level
        self._rng = np.random.default_rng(self.BIAS_SEED)

    def decide(self, profile: ApplicantProfile) -> DecisionResult:
        """Run decision on a single profile."""
        features, score_components = self._extract_features(profile)
        raw_score = self._compute_score(features)
        score = float(np.clip(raw_score, 0.0, 1.0))
        approved = score >= APPROVAL_THRESHOLD
        risk_tier = self._assign_risk_tier(score)
        denial_reasons = self._get_denial_reasons(profile, features) if not approved else []

        return DecisionResult(
            profile_id=profile.profile_id,
            approved=approved,
            score=round(score, 4),
            risk_tier=risk_tier,
            confidence=round(abs(score - 0.5) * 2, 4),
            decision_factors=score_components,
            denial_reasons=denial_reasons,
        )

    def decide_batch(self, profiles: List[ApplicantProfile]) -> List[DecisionResult]:
        """Run decisions on a list of profiles."""
        return [self.decide(p) for p in profiles]

    def decide_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run decisions on a full DataFrame (from CSV upload).
        Returns DataFrame with decision columns appended.
        """
        from agents.profile_generator import ProfileGeneratorAgent
        agent = ProfileGeneratorAgent()
        results = []
        for idx, row in df.iterrows():
            profile = agent.build_from_row(row, profile_id=f"ROW_{idx}")
            result = self.decide(profile)
            results.append({
                "profile_id": result.profile_id,
                "approved": result.approved,
                "score": result.score,
                "risk_tier": result.risk_tier,
                "confidence": result.confidence,
            })
        return pd.DataFrame(results)

    def _extract_features(self, p: ApplicantProfile) -> Tuple[Dict, Dict]:
        """Normalize and extract model features from a profile."""
        credit_norm = (p.credit_score - 300) / 550.0
        income_norm = min(p.income / 200000.0, 1.0)
        dti_penalty = p.debt_to_income
        emp_stability = min(p.years_employed / 20.0, 1.0)
        lti = min(p.loan_amount / max(p.income, 1), 5.0) / 5.0
        collateral_bonus = 1.0 if p.collateral in ["Property", "Investments"] else (0.5 if p.collateral == "Vehicle" else 0.0)
        edu_bonus = min((p.education_years - 8) / 14.0, 1.0)
        dep_penalty = p.num_dependents / 6.0

        features = {
            "credit_score_norm": credit_norm,
            "income_norm": income_norm,
            "dti_penalty": dti_penalty,
            "employment_stability": emp_stability,
            "loan_to_income_ratio": lti,
            "collateral_bonus": collateral_bonus,
            "education_bonus": edu_bonus,
            "dependents_penalty": dep_penalty,
        }

        # Compute contributions
        components = {
            k: round(v * self.WEIGHTS[k], 4) for k, v in features.items()
        }
        return features, components

    def _compute_score(self, features: Dict) -> float:
        """Logistic scoring function."""
        linear = sum(features[k] * self.WEIGHTS[k] for k in features)
        # Bias: add noise to simulate model uncertainty
        noise = self._rng.normal(0, self.noise_level)
        logit = linear + noise + 0.1  # slight positive base
        score = 1.0 / (1.0 + np.exp(-logit * 5))  # sigmoid
        return score

    def _assign_risk_tier(self, score: float) -> str:
        for tier, (low, high) in RISK_TIER_THRESHOLDS.items():
            if low <= score <= high:
                return tier
        return "Very High Risk"

    def _get_denial_reasons(self, p: ApplicantProfile, features: Dict) -> List[str]:
        """Generate human-readable denial reasons."""
        reasons = []
        if p.credit_score < 620:
            reasons.append(f"Credit score too low ({p.credit_score} < 620)")
        if p.debt_to_income > 0.43:
            reasons.append(f"Debt-to-income ratio exceeds threshold ({p.debt_to_income:.0%} > 43%)")
        if features["loan_to_income_ratio"] > 0.7:
            reasons.append(f"Loan amount high relative to income")
        if p.years_employed < 2:
            reasons.append("Insufficient employment history (< 2 years)")
        if p.employment_type == "Unemployed":
            reasons.append("Applicant currently unemployed")
        if not reasons:
            reasons.append("Overall risk profile does not meet minimum threshold")
        return reasons
