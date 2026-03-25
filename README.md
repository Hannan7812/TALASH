# TALASH - Milestone 1 Implementation

This repository contains a complete Milestone 1 implementation for TALASH, aligned with the roadmap requirements.

## Implemented Scope

- FastAPI backend for CV ingestion and candidate management.
- PDF preprocessing using `pdfplumber`.
- Groq-compatible LLM extraction prompt and parsing service.
- Candidate persistence using SQLAlchemy + Supabase Postgres.
- JSON and CSV/Excel exports for structured candidate data.
- React + Tailwind + Recharts prototype frontend.
- CLI scripts for milestone demo runs.
- Architecture and wireframe documentation.

## Project Structure

The code follows the structure defined in the assignment file map:

- `backend/app`: API, services, DB, models, schemas, utilities
- `backend/data`: raw CVs, parsed JSON, exports
- `frontend/src`: components, services, pages, charts
- `scripts`: pipeline and batch scripts
- `docs`: architecture, prompts, wireframes, milestone checklist

## Quick Start

## 1) Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Backend URL: `http://localhost:8000`

## 2) Run Preprocessing (CLI)

```bash
python scripts/run_pipeline.py backend/data/raw_cvs --overwrite
```

Outputs:
- Parsed JSON: `backend/data/parsed_json`
- Exports: `backend/data/exports`
- Database rows in Supabase Postgres

## 3) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

## Environment Variables

Copy `.env.example` values into your shell environment:

- `GROQ_API_KEY`: required for full LLM extraction
- `GROQ_MODEL`: optional model override
- `LLM_MAX_JSON_RETRIES`: number of retries when LLM returns invalid JSON
- `SUPABASE_DB_URL`: Supabase Postgres connection URL
- `AUTO_INIT_DB`: set `true` to auto-run SQLAlchemy `create_all` on startup

Without `GROQ_API_KEY`, the app uses a fallback heuristic parser for demo continuity.

## Supabase Setup

1. Create a Supabase project.
2. Copy the Postgres connection string and set `SUPABASE_DB_URL` in your environment.
3. Run [docs/supabase_schema.sql](docs/supabase_schema.sql) in Supabase SQL Editor.
4. Keep `AUTO_INIT_DB=false` for production-managed environments.

Supported model examples:

- `llama-3.3-70b-versatile`
- `mixtral-8x7b-32768`
- `deepseek-r1-distill-llama-70b`

## Key API Endpoints

- `GET /health`
- `POST /api/upload/process-folder`
- `POST /api/upload/upload-files`
- `GET /api/candidates/`
- `GET /api/candidates/{candidate_id}`
- `GET /api/analysis/summary/{candidate_id}`
- `GET /api/analysis/email-draft/{candidate_id}`

## Milestone 1 Mapping

- Architecture: `docs/architecture.md`
- Wireframes: `docs/wireframes.md`
- Prompt design: `docs/prompts.md`
- Deliverables checklist: `docs/milestone1_deliverables.md`
