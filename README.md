# E-YUVA Grant Programme Manager

FastAPI app for centre-level grant accounting and fellow subgrant tracking.

## Overview

- Double-entry journal with guardrails (positive amounts, mixed entry types, balanced totals)
- Budget and project tracking with centre summary endpoints
- Bank statement import and reconciliation
- Events with prior-approval rendering
- Reports/templates (HTML/DOC/DOCX) with placeholders
- Lightweight dashboard UI

## Key API

- `POST /transactions` (balanced journal required)
- `POST /transactions/{id}/reverse`
- `GET /transactions/centre-summary`
- `POST /events/{event_id}/prior-approval?template_id=...`
- `POST /reports/generate`
- `POST /reports/templates/upload-word`
- `POST /reports/placeholders`

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs`.

### Windows (PowerShell)

```powershell
py -m venv .venv
\.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

## Environment

```bash
export SECRET_KEY="<strong-random-secret>"
export CORS_ALLOWED_ORIGINS="http://127.0.0.1:8000,http://localhost:8000"
export SEED_DEFAULTS=true
export SEED_COORDINATOR_PASSWORD="change-me-now"
```

`SECRET_KEY` is required unless `ALLOW_INSECURE_DEV_SECRET=true` for local dev only.

## Testing

```bash
pytest tests/ -v
```

```bash
pytest tests/test_transaction_guardrails.py -v
```
