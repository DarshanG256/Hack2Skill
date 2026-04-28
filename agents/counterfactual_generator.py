"""
Agent 2: Counterfactual Generator
Generates adversarial profile variants by systematically modifying
protected attributes while holding financial features constant.
"""

import copy
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from agents.profile_generator import ApplicantProfile, CATEGORICAL_OPTIONS, PROTECTED_ATTRIBUTES


PROTECTED_PERTURBATIONS = {
    "gender": ["Male", "Female", "Non-binary"],
    "race": ["White", "Black", "Hispanic", "Asian", "Native American"],
    "age_group": ["Young Adult (18-29)", "Adult (30-44)", "Middle-aged (45-59)", "Senior (60+)"],
    "disability_status": ["No", "Yes"],
    "marital_status": ["Single", "Married", "Divorced", "Widowed"],
}

AGE_GROUP_TO_AGE = {
    "Young Adult (18-29)": 25,
    "Adult (30-44)": 38,
    "Middle-aged (45-59)": 52,
    "Senior (60+)": 65,
}


class CounterfactualGeneratorAgent:
    """
    Agent 2 — Counterfactual Generator
    Produces shadow applicants that are identical in financial merit but
    differ in protected characteristics — exposing discriminatory patterns.
    """

    def __init__(self):
        self.generated_variants: List[ApplicantProfile] = []

    def generate_all_counterfactuals(
        self, original: ApplicantProfile, attributes: List[str] = None
    ) -> List[ApplicantProfile]:
        """
        Generate full counterfactual set by varying all selected protected attributes.
        Returns list of profiles (original + all variants).
        """
        if attributes is None:
            attributes = ["gender", "race"]

        self.generated_variants = [original]
        seen_ids = set()
        seen_ids.add(f"{original.gender}|{original.race}|{original.age}|{original.disability_status}|{original.marital_status}")

        for attr in attributes:
            options = PROTECTED_PERTURBATIONS.get(attr, [])
            for value in options:
                current_val = getattr(original, attr, None)
                # Skip the original value (we already have original)
                if str(value) == str(current_val):
                    continue

                variant = self._clone_with_change(original, attr, value)
                fingerprint = f"{variant.gender}|{variant.race}|{variant.age}|{variant.disability_status}|{variant.marital_status}"
                if fingerprint not in seen_ids:
                    seen_ids.add(fingerprint)
                    self.generated_variants.append(variant)

        return self.generated_variants

    def generate_pairwise_counterfactuals(
        self, original: ApplicantProfile, attribute: str
    ) -> List[ApplicantProfile]:
        """Generate pairwise counterfactuals for a single attribute."""
        options = PROTECTED_PERTURBATIONS.get(attribute, [])
        variants = [original]
        for value in options:
            current_val = getattr(original, attribute, None)
            if str(value) == str(current_val):
                continue
            variant = self._clone_with_change(original, attribute, value)
            variants.append(variant)
        return variants

    def to_dataframe(self, profiles: List[ApplicantProfile]) -> pd.DataFrame:
        """Convert list of profiles to comparison DataFrame."""
        rows = [p.to_dict() for p in profiles]
        df = pd.DataFrame(rows)
        return df

    def highlight_changes(
        self, original: ApplicantProfile, variants: List[ApplicantProfile]
    ) -> List[Dict[str, Any]]:
        """
        Return list of dicts describing what changed in each variant vs original.
        """
        orig_dict = original.to_dict()
        changes = []
        for variant in variants[1:]:
            var_dict = variant.to_dict()
            diff_fields = {
                k: {"from": orig_dict[k], "to": var_dict[k]}
                for k in orig_dict
                if orig_dict[k] != var_dict[k] and k not in ("profile_id", "age_group")
            }
            changes.append(
                {
                    "profile_id": variant.profile_id,
                    "changes": diff_fields,
                    "num_changes": len(diff_fields),
                }
            )
        return changes

    def _clone_with_change(
        self, original: ApplicantProfile, attribute: str, new_value: Any
    ) -> ApplicantProfile:
        """Deep clone a profile and change a single attribute."""
        data = original.to_dict()
        data.pop("age_group", None)  # recalculated by __post_init__

        if attribute == "age_group":
            # Map age group back to concrete age value
            data["age"] = AGE_GROUP_TO_AGE.get(new_value, original.age)
        else:
            data[attribute] = new_value

        # Build a profile_id label
        original_val = getattr(original, attribute, "?")
        data["profile_id"] = f"CF_{attribute.upper()}={new_value}"

        profile = ApplicantProfile(**data)
        return profile

    def get_summary_stats(self, profiles: List[ApplicantProfile]) -> pd.DataFrame:
        """Compute summary statistics across counterfactual profiles."""
        df = self.to_dataframe(profiles)
        numeric_cols = ["income", "credit_score", "debt_to_income", "years_employed", "loan_amount"]
        return df[["profile_id"] + numeric_cols]
