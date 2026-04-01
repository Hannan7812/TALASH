# TALASH

Talent Acquisition & Learning Automation for Smart Hiring.

TALASH is a full-stack CV ingestion, parsing, analysis, and candidate profiling system, implemented with end-to-end backend analysis, candidate-wise dashboards, research profiling, exports, and a comparative analytics UI.

## Project Status

Implemented features:
- FastAPI backend with async PostgreSQL connection
- PDF upload, bulk upload, and folder-based ingestion
- Candidate records stored in the database
- LLM analysis via Groq to extract structured profile fields
- Education, experience, research, and missing-information analysis
- Candidate summary generation and personalized draft email creation
- React + Vite frontend for upload, insights, and analytics dashboards
- Tabular outputs, sortable comparisons, and charts/graphs for candidate review
- Folder-based CV processing for multiple candidates
- Candidate-wise tabular outputs and comparative dashboard views
- Graphical analytics with chart-based summaries
- Candidate summary generation
- Personalized missing-information email drafting
- Structured CSV/XLSX export for one or all candidates

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy (async)
- PostgreSQL (`asyncpg`)
- PyMuPDF (`fitz`)
- Groq API client

Frontend:
- React
- Vite

## Repository Structure

```text
talash/
  backend/
    app/
      api/
      db/
      llm/
      modules/
    requirements.txt
  frontend/
    src/
  database_structure.csv
  ```

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Groq API key

## Backend Setup

From `talash/backend`:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env` in `talash/backend`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/talash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
UPLOAD_DIR=uploads
```

Run backend:

```bash
uvicorn app.main:app --reload
```

Backend URLs:
- API root: http://localhost:8000/
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs

## Frontend Setup

From `talash/frontend`:

```bash
npm install
npm run dev
```

Frontend default URL:
- http://localhost:5173

Note: frontend components currently call backend at `http://localhost:8000` directly.

## Current API Endpoints

Base prefix: `/cv`

- `POST /cv/upload`
  - Upload a PDF CV (`multipart/form-data`, field: `file`)
  - Extracts text and creates a candidate record
- `POST /cv/upload/bulk`
  - Upload and process multiple PDF CVs in one request
- `POST /cv/ingest/folder`
  - Parse PDFs from a server-side folder path
- `POST /cv/parse`
  - Parses a PDF already present in uploads folder (filename input)
- `GET /cv/candidates`
  - List candidate records with pagination, filtering, and sorting
- `GET /cv/candidate/{candidate_id}`
  - Get full candidate details, including raw text
- `POST /cv/candidate/{candidate_id}/analyze`
  - Run LLM analysis and persist structured fields
- `POST /cv/candidate/{candidate_id}/preprocess`
  - Generate structured preprocessing tables plus CSV/XLSX exports for one candidate
- `POST /cv/preprocess/export`
  - Generate structured preprocessing exports for all usable candidates

Base prefix: `/analysis`

- `POST /analysis/candidate/{candidate_id}/full`
  - Run the complete multi-module analysis pipeline
- `GET /analysis/candidate/{candidate_id}`
  - Retrieve stored analysis results
- `POST /analysis/candidate/{candidate_id}/email`
  - Regenerate the missing-information email draft

## Database Notes

- The running backend currently relies on the `candidates` table model in `backend/app/db/models.py`.
- A broader target schema for future modules exists in `database_structure.csv`.
- Structured preprocessing exports are written under `backend/exports/` by default.
- Research analysis includes co-author metrics, research domains, publication diversity, and research scoring.

## Quick Test Commands

From `talash/backend`:

```bash
python test_db.py
python app/test_llm.py
```