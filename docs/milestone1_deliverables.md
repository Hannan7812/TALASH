# TALASH Milestone 1 Deliverables Checklist

## Step 1: System Architecture Design
- Completed: architecture diagram and detailed flow in `docs/architecture.md`.

## Step 2: UI/UX Wireframes
- Completed: upload/list/detail/dashboard/email draft wireframes in `docs/wireframes.md`.

## Step 3: Preprocessing Module
- Completed backend pipeline:
  - Accept folder of PDFs.
  - Extract text with pdfplumber.
  - Parse structured JSON via Groq API prompt.
  - Save candidate data to Supabase Postgres via SQLAlchemy.
  - Save parsed JSON files under backend/data/parsed_json.
  - Export CSV/Excel under backend/data/exports.

## Step 4: Early Prototype
- Completed:
  - FastAPI endpoints for processing and candidate retrieval.
  - React dashboard for upload, table, candidate detail, and chart.
  - CLI demo scripts for milestone demonstrations.

## Demo Commands

### Backend
```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

### CLI Prototype
```bash
python scripts/run_pipeline.py backend/data/raw_cvs --overwrite
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
