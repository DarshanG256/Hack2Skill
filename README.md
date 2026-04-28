# Shadow Applicant — AI Fairness Auditor

This repository contains a Flask-based demo application for auditing fairness in applicant decision datasets.

## Fixes Included
- Fixed CSV upload handling with robust column mapping and blank-value filtering.
- Fixed synthetic dataset preview rendering in the browser.
- Improved fairness scoring so datasets without protected-group comparisons do not automatically return `100%`.

## Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Then open `http://localhost:5000` in your browser.

## Deploy Publicly
You can deploy this app to Render, Railway, Heroku, or similar platforms.

### Example: Render
1. Push this repository to GitHub.
2. Create a new Web Service on Render.
3. Select `Python`.
4. Set the build command to `pip install -r requirements.txt`.
5. Set the start command to `gunicorn server:app --bind 0.0.0.0:$PORT`.

Once deployed, Render will provide a public URL you can share as your live demo.

## Notes
- If you want an exact public demo link, deploy the repository to a hosting service and use the generated URL.
- The app is ready to run as a Flask service.
