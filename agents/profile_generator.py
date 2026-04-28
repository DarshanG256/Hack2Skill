"""
Agent 1: Profile Generator
Constructs and validates structured applicant profiles for auditing.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


PROTECTED_ATTRIBUTES = ["gender", "race", "age_group", "disability_status", "marital_status"]

FEATURE_RANGES = {
    "age": (18, 75),
    "income": (20000, 250000),
    "credit_score": (300, 850),
    "loan_amount": (5000, 500000),
    "years_employed": (0, 40),
    "debt_to_income": (0.0, 0.6),
    "num_dependents": (0, 6),
    "education_years": (8, 22),
}

CATEGORICAL_OPTIONS = {
    "gender": ["Male", "Female", "Non-binary"],
    "race": ["White", "Black", "Hispanic", "Asian", "Native American", "Other"],
    "marital_status": ["Single", "Married", "Divorced", "Widowed"],
    "employment_type": ["Full-time", "Part-time", "Self-employed", "Unemployed"],
    "disability_status": ["No", "Yes"],
    "loan_purpose": ["Home Purchase", "Auto Loan", "Business", "Personal", "Education"],
    "collateral": ["None", "Property", "Vehicle", "Investments"],
}


@dataclass
class ApplicantProfile:
    """Structured applicant profile with all features."""
    # Demographics (Protected)
    age: int = 35
    gender: str = "Male"
    race: str = "White"
    marital_status: str = "Single"
    disability_status: str = "No"

    # Financials
    income: float = 75000.0
    credit_score: int = 680
    loan_amount: float = 150000.0
    debt_to_income: float = 0.25
    years_employed: int = 5
    num_dependents: int = 0
    education_years: int = 16

    # Loan Context
    employment_type: str = "Full-time"
    loan_purpose: str = "Home Purchase"
    collateral: str = "None"

    # Derived Fields
    profile_id: str = "ORIGINAL"
    age_group: str = field(init=False)

    def __post_init__(self):
        self.age_group = self._compute_age_group()

    def _compute_age_group(self) -> str:
        if self.age < 30:
            return "Young Adult (18-29)"
        elif self.age < 45:
            return "Adult (30-44)"
        elif self.age < 60:
            return "Middle-aged (45-59)"
        else:
            return "Senior (60+)"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def to_series(self) -> pd.Series:
        return pd.Series(self.to_dict())


class ProfileGeneratorAgent:
    """
    Agent 1 — Profile Generator
    Responsible for constructing, validating, and normalizing applicant profiles.
    """

    def __init__(self):
        self.validation_errors: List[str] = []

    def build_from_form(self, form_data: Dict[str, Any]) -> ApplicantProfile:
        """Build a validated profile from Streamlit form inputs."""
        self.validation_errors = []
        self._validate(form_data)
        profile = ApplicantProfile(
            age=int(form_data.get("age", 35)),
            gender=form_data.get("gender", "Male"),
            race=form_data.get("race", "White"),
            marital_status=form_data.get("marital_status", "Single"),
            disability_status=form_data.get("disability_status", "No"),
            income=float(form_data.get("income", 75000)),
            credit_score=int(form_data.get("credit_score", 680)),
            loan_amount=float(form_data.get("loan_amount", 150000)),
            debt_to_income=float(form_data.get("debt_to_income", 0.25)),
            years_employed=int(form_data.get("years_employed", 5)),
            num_dependents=int(form_data.get("num_dependents", 0)),
            education_years=int(form_data.get("education_years", 16)),
            employment_type=form_data.get("employment_type", "Full-time"),
            loan_purpose=form_data.get("loan_purpose", "Home Purchase"),
            collateral=form_data.get("collateral", "None"),
            profile_id="ORIGINAL",
        )
        return profile

    def build_from_row(self, row: pd.Series, profile_id: str = "UPLOADED") -> ApplicantProfile:
        """Build a profile from a DataFrame row."""
        form_data = row.to_dict()
        form_data["profile_id"] = profile_id
        profile = self.build_from_form(form_data)
        profile.profile_id = profile_id
        return profile

    def build_sample_dataset(self, n: int = 100, seed: int = 42) -> pd.DataFrame:
        """Generate a synthetic demo dataset for auditing."""
        rng = np.random.default_rng(seed)

        genders = rng.choice(["Male", "Female"], size=n, p=[0.52, 0.48])
        races = rng.choice(
            ["White", "Black", "Hispanic", "Asian", "Native American"],
            size=n,
            p=[0.45, 0.20, 0.18, 0.12, 0.05],
        )

        # Introduce systematic bias: lower income & credit for minorities
        base_income = np.where(
            races == "White", rng.integers(55000, 150000, n),
            np.where(races == "Black", rng.integers(30000, 90000, n),
            np.where(races == "Hispanic", rng.integers(28000, 85000, n),
            rng.integers(35000, 120000, n)))
        )
        base_credit = np.where(
            races == "White", rng.integers(640, 820, n),
            np.where(races == "Black", rng.integers(560, 740, n),
            np.where(races == "Hispanic", rng.integers(550, 720, n),
            rng.integers(580, 780, n)))
        )

        data = {
            "age": rng.integers(22, 68, n),
            "gender": genders,
            "race": races,
            "marital_status": rng.choice(["Single", "Married", "Divorced"], size=n, p=[0.40, 0.45, 0.15]),
            "disability_status": rng.choice(["No", "Yes"], size=n, p=[0.88, 0.12]),
            "income": base_income.astype(float),
            "credit_score": base_credit,
            "loan_amount": rng.integers(15000, 400000, n).astype(float),
            "debt_to_income": rng.uniform(0.05, 0.55, n).round(2),
            "years_employed": rng.integers(0, 30, n),
            "num_dependents": rng.integers(0, 5, n),
            "education_years": rng.integers(10, 22, n),
            "employment_type": rng.choice(["Full-time", "Part-time", "Self-employed", "Unemployed"], size=n, p=[0.65, 0.15, 0.12, 0.08]),
            "loan_purpose": rng.choice(["Home Purchase", "Auto Loan", "Business", "Personal", "Education"], size=n),
            "collateral": rng.choice(["None", "Property", "Vehicle", "Investments"], size=n, p=[0.35, 0.30, 0.25, 0.10]),
        }
        return pd.DataFrame(data)

    def _validate(self, form_data: Dict[str, Any]) -> bool:
        """Validate form inputs and collect errors."""
        age = int(form_data.get("age", 35))
        credit = int(form_data.get("credit_score", 680))
        income = float(form_data.get("income", 75000))
        dti = float(form_data.get("debt_to_income", 0.25))

        if not (18 <= age <= 100):
            self.validation_errors.append("Age must be between 18 and 100.")
        if not (300 <= credit <= 850):
            self.validation_errors.append("Credit score must be between 300 and 850.")
        if income < 0:
            self.validation_errors.append("Income cannot be negative.")
        if not (0.0 <= dti <= 1.0):
            self.validation_errors.append("Debt-to-income ratio must be between 0.0 and 1.0.")
        return len(self.validation_errors) == 0

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0
