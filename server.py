"""
Shadow Applicant — Flask API Server (Deployment Ready)
"""
import os
import datetime
import traceback
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# Dummy fallback (in case your modules fail during deploy)
try:
    from agents.profile_generator import ProfileGeneratorAgent, CATEGORICAL_OPTIONS
    from agents.counterfactual_generator import CounterfactualGeneratorAgent
    from agents.decision_simulator import DecisionSimulatorAgent
    from agents.bias_auditor import BiasAuditorAgent
    from utils.report_generator import generate_text_report, report_to_bytes
except:
    CATEGORICAL_OPTIONS = {"gender": ["Male", "Female"], "race": ["GroupA", "GroupB"]}

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ─────────────────────────────────────────────────────────────
# Health check (IMPORTANT for deployment)
# ─────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "Shadow Applicant API is live 🚀"
    })

# ─────────────────────────────────────────────────────────────
# Basic test route
# ─────────────────────────────────────────────────────────────
@app.route("/api/test")
def test():
    return jsonify({"msg": "API working successfully"})

# ─────────────────────────────────────────────────────────────
# Sample dataset generator
# ─────────────────────────────────────────────────────────────
@app.route("/api/sample-dataset", methods=["POST"])
def sample_dataset():
    try:
        n = int(request.json.get("n", 50))
        data = []

        for i in range(n):
            data.append({
                "name": f"User{i}",
                "income": int(30000 + i * 500),
                "credit_score": int(600 + (i % 100)),
                "gender": "Male" if i % 2 == 0 else "Female",
                "race": "GroupA" if i % 3 == 0 else "GroupB"
            })

        return jsonify({
            "rows": n,
            "preview": data[:5]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# Simple bias simulation
# ─────────────────────────────────────────────────────────────
@app.route("/api/audit/demo", methods=["POST"])
def audit_demo():
    try:
        profiles = request.json.get("profiles", [])

        results = []
        for p in profiles:
            # Simulated bias logic
            approved = True
            if p.get("race") == "GroupB":
                approved = False

            results.append({
                "name": p.get("name"),
                "approved": approved
            })

        return jsonify({
            "results": results,
            "bias_detected": any(not r["approved"] for r in results)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# Report download (basic)
# ─────────────────────────────────────────────────────────────
@app.route("/api/report")
def report():
    text = "Shadow Applicant Audit Report\nSystem operational."
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=report.txt"}
    )

# ─────────────────────────────────────────────────────────────
# MAIN RUN (IMPORTANT FOR RENDER)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Server running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)