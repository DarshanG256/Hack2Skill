"""
The Shadow Applicant — Flask API Server
Serves the React-style SPA and all agent pipeline endpoints.
"""
import json, io, csv, datetime, traceback
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# ── agent imports ──────────────────────────────────────────────────────────────
from agents.profile_generator import ProfileGeneratorAgent, CATEGORICAL_OPTIONS
from agents.counterfactual_generator import CounterfactualGeneratorAgent
from agents.decision_simulator import DecisionSimulatorAgent
from agents.bias_auditor import BiasAuditorAgent
from utils.report_generator import generate_text_report, report_to_bytes

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ── in-memory state ────────────────────────────────────────────────────────────
_state = {
    "dataset_df": None,
    "audit_report": None,
    "metrics_df": None,
    "full_df": None,
    "decision_df": None,
    "cf_result": None,
    "cf_decisions": None,
}


# ══════════════════════════════════════════════════════════════════════════════
# Static / SPA
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ══════════════════════════════════════════════════════════════════════════════
# API — Metadata
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/options")
def get_options():
    """Return categorical options for form dropdowns."""
    return jsonify(CATEGORICAL_OPTIONS)


@app.route("/api/status")
def get_status():
    return jsonify({
        "dataset_loaded": _state["dataset_df"] is not None,
        "audit_run":      _state["audit_report"] is not None,
        "cf_run":         _state["cf_result"] is not None,
        "dataset_size":   len(_state["dataset_df"]) if _state["dataset_df"] is not None else 0,
        "data_source":    _state.get("data_source", ""),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API — Data Upload
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/upload", methods=["POST"])
def upload_csv():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        df = pd.read_csv(file)
        required = ["age","gender","race","marital_status","disability_status",
                    "income","credit_score","loan_amount","debt_to_income",
                    "years_employed","num_dependents","education_years",
                    "employment_type","loan_purpose","collateral"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return jsonify({"error": f"Missing columns: {', '.join(missing)}"}), 400
        df = df[required].dropna().reset_index(drop=True)
        _state["dataset_df"] = df
        _state["data_source"] = file.filename
        return jsonify({"message": f"Loaded {len(df)} records", "rows": len(df), "cols": len(df.columns)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sample-dataset", methods=["POST"])
def load_sample():
    try:
        n = int(request.json.get("n", 100))
        agent = ProfileGeneratorAgent()
        df = agent.build_sample_dataset(n=n)
        _state["dataset_df"] = df
        _state["data_source"] = f"Synthetic ({n} records)"
        # Return preview
        preview = df.head(10).to_dict(orient="records")
        stats = _get_dataset_stats(df)
        return jsonify({"message": f"Generated {n} records", "rows": n, "preview": preview, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dataset/preview")
def dataset_preview():
    df = _state["dataset_df"]
    if df is None:
        return jsonify({"error": "No dataset loaded"}), 400
    return jsonify({
        "preview": df.head(20).to_dict(orient="records"),
        "stats": _get_dataset_stats(df),
        "rows": len(df),
        "cols": len(df.columns),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API — Single Applicant Audit
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/audit/single", methods=["POST"])
def audit_single():
    try:
        body = request.json
        form_data = body.get("profile", {})
        cf_attrs  = body.get("cf_attributes", ["gender", "race"])
        noise     = float(body.get("noise", 0.05))

        # Agent 1
        p_agent   = ProfileGeneratorAgent()
        original  = p_agent.build_from_form(form_data)
        if not p_agent.is_valid:
            return jsonify({"error": "; ".join(p_agent.validation_errors)}), 400

        # Agent 2
        cf_agent  = CounterfactualGeneratorAgent()
        profiles  = cf_agent.generate_all_counterfactuals(original, cf_attrs)

        # Agent 3
        dec_agent = DecisionSimulatorAgent(noise_level=noise)
        decisions = dec_agent.decide_batch(profiles)

        # Agent 4
        b_agent   = BiasAuditorAgent()
        cf_result = b_agent.audit_counterfactuals(profiles, decisions, cf_attrs[0] if cf_attrs else "race")

        _state["cf_result"]    = cf_result
        _state["cf_decisions"] = decisions

        # Build response
        orig_dec = decisions[0]
        variants_out = []
        for p, d in zip(profiles, decisions):
            variants_out.append({
                "profile_id":   d.profile_id,
                "gender":       p.gender,
                "race":         p.race,
                "age_group":    p.age_group,
                "disability":   p.disability_status,
                "approved":     d.approved,
                "score":        round(d.score, 4),
                "risk_tier":    d.risk_tier,
                "confidence":   round(d.confidence, 4),
                "factors":      d.decision_factors,
                "denial":       d.denial_reasons,
            })

        return jsonify({
            "original": {
                "approved": orig_dec.approved,
                "score":    round(orig_dec.score, 4),
                "risk_tier": orig_dec.risk_tier,
                "factors":  orig_dec.decision_factors,
                "denial":   orig_dec.denial_reasons,
            },
            "variants": variants_out,
            "summary": {
                "any_reversal":   cf_result["any_reversal"],
                "max_score_gap":  round(cf_result["max_score_gap"], 4),
                "original_group": cf_result["original_group"],
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# API — Batch Dataset Audit
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/audit/batch", methods=["POST"])
def audit_batch():
    try:
        df = _state["dataset_df"]
        if df is None:
            return jsonify({"error": "No dataset loaded"}), 400

        # Agent 3 — decisions
        dec_agent   = DecisionSimulatorAgent()
        decision_df = dec_agent.decide_dataframe(df)

        # Merge + age_group
        full_df = pd.concat([df.reset_index(drop=True), decision_df.reset_index(drop=True)], axis=1)
        full_df["age_group"] = full_df["age"].apply(_age_group)

        # Agent 4 — bias audit
        b_agent = BiasAuditorAgent()
        report  = b_agent.audit_dataset(df, decision_df)
        metrics_df = b_agent.metrics_to_dataframe(report.metrics_by_attribute)

        _state["audit_report"] = report
        _state["metrics_df"]   = metrics_df
        _state["full_df"]      = full_df
        _state["decision_df"]  = decision_df

        # Approval rates by group for charts
        approval_charts = {}
        for attr in ["gender", "race", "age_group", "disability_status"]:
            if attr in full_df.columns:
                grp = full_df.groupby(attr)["approved"].agg(["mean","count"]).reset_index()
                grp.columns = [attr, "rate", "count"]
                grp["rate"] = grp["rate"].round(4)
                approval_charts[attr] = grp.to_dict(orient="records")

        # Score distribution by race
        score_dist = {}
        for attr in ["gender", "race", "age_group"]:
            if attr in full_df.columns:
                grp_scores = {}
                for g in full_df[attr].unique():
                    scores = full_df[full_df[attr] == g]["score"].tolist()
                    grp_scores[str(g)] = scores
                score_dist[attr] = grp_scores

        return jsonify({
            "audit_score":        round(report.audit_score, 1),
            "total_profiles":     report.total_profiles,
            "overall_approval":   round(report.overall_approval_rate, 4),
            "most_biased_attr":   report.most_biased_attribute,
            "most_biased_group":  report.most_biased_group,
            "critical_findings":  report.critical_findings,
            "recommendations":    report.recommendations,
            "metrics":            metrics_df.to_dict(orient="records") if not metrics_df.empty else [],
            "approval_charts":    approval_charts,
            "score_dist":         score_dist,
            "biased_count":       sum(m.is_biased for m in report.metrics_by_attribute),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# API — Report Download
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/report/download")
def download_report():
    report     = _state["audit_report"]
    metrics_df = _state["metrics_df"]
    if report is None:
        return jsonify({"error": "No audit report available"}), 400
    audit_name = request.args.get("name", "AI Fairness Audit")
    model_name = request.args.get("model", "Enterprise Decision Model v2.1")
    text = generate_text_report(report, metrics_df if metrics_df is not None else pd.DataFrame(),
                                audit_name=audit_name, model_name=model_name)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
    return Response(
        report_to_bytes(text),
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=shadow_applicant_report_{timestamp}.txt"}
    )

@app.route("/api/report/metrics-csv")
def download_metrics_csv():
    metrics_df = _state["metrics_df"]
    if metrics_df is None:
        return jsonify({"error": "No metrics available"}), 400
    csv_str = metrics_df.to_csv(index=False)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
    return Response(
        csv_str.encode(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=bias_metrics_{timestamp}.csv"}
    )


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def _age_group(a):
    if a < 30:   return "Young Adult (18-29)"
    elif a < 45: return "Adult (30-44)"
    elif a < 60: return "Middle-aged (45-59)"
    else:        return "Senior (60+)"

def _get_dataset_stats(df):
    stats = {}
    for col in ["gender","race","marital_status","disability_status","employment_type"]:
        if col in df.columns:
            vc = df[col].value_counts()
            stats[col] = [{"label": str(k), "count": int(v)} for k, v in vc.items()]
    return stats


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ⚖️  Shadow Applicant — Enterprise AI Fairness Auditor")
    print("  🌐  Open http://localhost:5000 in your browser")
    print("="*60 + "\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
