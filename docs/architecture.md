# TALASH System Architecture (Milestone 1)

```mermaid
flowchart LR
    A[Local CV Folder / Upload] --> B[FastAPI Upload Route]
    B --> C[PDF Parser Service - pdfplumber]
    C --> D[Raw Text]
    D --> E[LLM Service - Groq API]
    E --> F[Structured JSON]
    F --> G[(Supabase Postgres)]
    F --> H[Parsed JSON Files]
    G --> I[Candidates API]
    H --> J[CSV/Excel Export Service]
    I --> K[React Frontend]
    J --> K

    subgraph Backend
      B
      C
      E
      J
      I
    end

    subgraph Storage
      G
      H
    end

    subgraph Frontend
      K
    end
```

## Detailed Data Flow

1. User provides CVs either by uploading files or by passing a local folder path.
2. Backend scans all PDF files and extracts raw text from each document.
3. Raw CV text is sent to a Groq-hosted model with a strict JSON extraction prompt.
4. Extracted structured JSON is persisted in DB and also saved to disk.
5. Flattened records are exported into CSV and Excel for milestone submission.
6. Frontend reads candidate APIs to display table, detail pane, chart metrics, and email draft.
