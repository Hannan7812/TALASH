# =============================================================================
# TALASH - CV Parser and Database Storage
# app/api/cv_upload.py
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import fitz
import os
import re
import shutil
from datetime import datetime

from app.db.database import get_db
from app.db.models import Candidate, ProcessingStatus
from app.llm.llm_client import ask_llm
from app.modules.preprocessing import build_and_export_dataset

router = APIRouter(prefix="/cv", tags=["CV Upload"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
LLM_PROMPT_MAX_CHARS = int(os.getenv("LLM_PROMPT_MAX_CHARS", "8000"))
LLM_RESPONSE_MAX_TOKENS = int(os.getenv("LLM_RESPONSE_MAX_TOKENS", "500"))


def sanitize_cv_text(text: str | None) -> str:
    """
    Remove characters PostgreSQL cannot store in TEXT/VARCHAR.
    Keep common formatting characters like newline and tab.
    """
    if not text:
        return ""

    # PostgreSQL rejects embedded NUL bytes.
    cleaned = text.replace("\x00", "")
    # Remove other non-printable control characters except \t, \n, \r.
    cleaned = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned


def _safe_filename_component(value: str) -> str:
    """Convert free-text into a filesystem-safe slug-like component."""
    if not value:
        return "candidate"
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value[:120] or "candidate"


def _unique_upload_path(filename: str) -> tuple[str, str]:
    """Return a unique filename + path in uploads to avoid collisions."""
    base, ext = os.path.splitext(filename)
    safe_base = _safe_filename_component(base)
    ext = ext if ext else ".pdf"

    candidate_name = f"{safe_base}{ext}"
    path = os.path.join(UPLOAD_DIR, candidate_name)
    counter = 1
    while os.path.exists(path):
        candidate_name = f"{safe_base}_{counter}{ext}"
        path = os.path.join(UPLOAD_DIR, candidate_name)
        counter += 1

    return candidate_name, path


def _rename_cv_filename_from_candidate_name(candidate: Candidate) -> None:
    """Use parsed full_name as cv_filename for easier tracking in dashboard."""
    if not candidate.full_name:
        return

    _, ext = os.path.splitext(candidate.cv_filename or "")
    ext = ext or ".pdf"
    safe_name = _safe_filename_component(candidate.full_name)
    candidate.cv_filename = f"{safe_name}{ext}"

    # File may already be deleted from uploads, but keep filepath metadata aligned.
    candidate.cv_filepath = os.path.join(UPLOAD_DIR, candidate.cv_filename)


def _candidate_analysis_prompts(raw_text: str) -> tuple[str, str]:
    system_prompt = """
You are an expert CV parser for hiring systems.
Return ONLY valid JSON (no markdown, no prose).
If a value is missing, use null.
carefully analyze the CV and dont put value of one field in another field
Read the text multiple time if needed to find the correct answer.
i have added the comments using # to guide you about the fields,dont include them in response, please follow them
Use exactly this JSON schema:
{
  "full_name": string|null, # Use the full name as it appears on the CV
  "email": string|null,  # email of the candidate
  "phone": string|null,  # phone number exactly as written in the CV, including any +, -, spaces or formatting for example +92 ... detect it from raw text 
  "address": string|null,  # currently living address of the candidate if available
  "linkedin_url": string|null,  # linkedin profile of the candidate, must have linkedin in the url dont mix it wiht github link or any other link
  "nationality": string|null,
  "universities": string|null,  # Names of the universities or educational institutions attended by the candidate look this in education section
  "overall_summary": string|null,
  "overall_score": number|null  # evaluate the candidate profile strength and assign an overall score out of 100 based on their experience, education, and skills. Do not return null, calculate an objective score. 
}

Rules:
- Keep overall_summary concise (max 120 words).
- overall_score must be 0 to 100 when present.
- Do not invent facts not supported by the CV.
"""

    user_prompt = f"""
Extract candidate profile fields from this CV raw text.

CV RAW TEXT:
{raw_text[:LLM_PROMPT_MAX_CHARS]}
"""

    return system_prompt, user_prompt


# HELPER — Extract raw text from PDF using PyMuPDF
def extract_text_from_pdf(filepath: str) -> str:
    """
    Opens a PDF file and extracts all text page by page.
    Returns a single clean string of the full CV text.
    """
    try:
        doc = fitz.open(filepath)
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            full_text += page.get_text()
            full_text += "\n"  # Separator between pages

        doc.close()

        # Basic cleanup
        full_text = full_text.strip()
        full_text = "\n".join(
            line.strip() for line in full_text.splitlines() if line.strip()
        )

        return sanitize_cv_text(full_text)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )


# HELPER — Save candidate to database
async def save_candidate_to_db(
    db: AsyncSession,
    filename: str,
    filepath: str,
    raw_text: str
) -> Candidate:
    """
    Creates a new candidate record in the database with the extracted CV text.
    Status is set to 'pending' — LLM analysis runs separately after this.
    """
    clean_text = sanitize_cv_text(raw_text)

    candidate = Candidate(
        cv_filename=filename,
        cv_filepath=filepath,
        cv_raw_text=clean_text,
        status=ProcessingStatus.PENDING
    )

    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    return candidate


async def _ingest_cv_from_file(
    db: AsyncSession,
    filename: str,
    filepath: str,
    delete_after_parse: bool = True,
) -> dict:
    """
    Parse one CV file and store one candidate.
    This guarantees each file is treated as a separate candidate record.
    """
    print(f"Parsing CV: {filename}")
    raw_text = sanitize_cv_text(extract_text_from_pdf(filepath))

    if not raw_text or len(raw_text) < 50:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract meaningful text from '{filename}'. It may be scanned or image-based."
        )

    print(f"Extracted {len(raw_text)} characters from {filename}")

    candidate = await save_candidate_to_db(
        db=db,
        filename=filename,
        filepath=filepath,
        raw_text=raw_text
    )

    print(f"Saved candidate ID {candidate.id} to database")

    if delete_after_parse:
        try:
            os.remove(filepath)
            print(f"Deleted parsed CV from uploads: {filepath}")
        except Exception as e:
            print(f"Failed to delete file {filepath}: {e}")

    return {
        "candidate_id": candidate.id,
        "filename": filename,
        "characters_extracted": len(raw_text),
        "status": candidate.status,
    }


@router.post("/upload")
async def upload_and_parse_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives a CV PDF from frontend, saves it to uploads/, extracts text,
    and inserts it into the database as a new candidate.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save the file with a unique path
    stored_filename, filepath = _unique_upload_path(file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = await _ingest_cv_from_file(
        db=db,
        filename=stored_filename,
        filepath=filepath,
        delete_after_parse=True,
    )

    return {
        "success": True,
        **result,
        "message": f"CV uploaded and parsed successfully. Candidate ID: {result['candidate_id']}"
    }


@router.post("/upload/bulk")
async def bulk_upload_and_parse_cv(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk upload endpoint: each PDF is parsed and stored as a separate candidate.
    This prevents token blowups from combining multiple CVs into one analysis payload.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results: list[dict] = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append(
                {
                    "filename": file.filename,
                    "success": False,
                    "error": "Only PDF files are supported.",
                }
            )
            continue

        stored_filename, filepath = _unique_upload_path(file.filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            parsed_result = await _ingest_cv_from_file(
                db=db,
                filename=stored_filename,
                filepath=filepath,
                delete_after_parse=True,
            )
            results.append({"success": True, **parsed_result})
        except Exception as e:
            results.append(
                {
                    "filename": stored_filename,
                    "success": False,
                    "error": str(e),
                }
            )

    processed = len([r for r in results if r.get("success")])
    failed = len(results) - processed

    return {
        "success": failed == 0,
        "total_received": len(files),
        "processed": processed,
        "failed": failed,
        "results": results,
    }


@router.post("/ingest/folder")
async def ingest_folder_cvs(
    folder_path: str = UPLOAD_DIR,
    delete_after_parse: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Reads all PDFs from a folder and ingests each as a separate candidate.
    """
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    pdf_files = sorted(
        [name for name in os.listdir(folder_path) if name.lower().endswith(".pdf")]
    )
    if not pdf_files:
        return {
            "success": True,
            "folder_path": folder_path,
            "total_found": 0,
            "processed": 0,
            "failed": 0,
            "results": [],
        }

    results: list[dict] = []
    for filename in pdf_files:
        filepath = os.path.join(folder_path, filename)
        try:
            parsed_result = await _ingest_cv_from_file(
                db=db,
                filename=filename,
                filepath=filepath,
                delete_after_parse=delete_after_parse,
            )
            results.append({"success": True, **parsed_result})
        except Exception as e:
            results.append(
                {
                    "filename": filename,
                    "success": False,
                    "error": str(e),
                }
            )

    processed = len([r for r in results if r.get("success")])
    failed = len(results) - processed
    return {
        "success": failed == 0,
        "folder_path": folder_path,
        "total_found": len(pdf_files),
        "processed": processed,
        "failed": failed,
        "results": results,
    }

# ENDPOINT — POST /cv/parse
# Called after frontend saves the PDF to uploads/ folder
# Frontend sends just the filename, backend does the rest
@router.post("/parse")
async def parse_cv(
    filename: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Parses a CV PDF that already exists in the uploads/ folder.
    Extracts raw text and saves the candidate record to the database.

    Steps:
    1. Check the file exists in uploads/
    2. Extract text using PyMuPDF
    3. Save candidate record to DB with raw text
    4. Return candidate ID for frontend to track

    Frontend calls this AFTER saving the PDF to uploads/.
    """

    # Step 1 — Build full file path and check it exists
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found in uploads folder. Make sure it was uploaded first."
        )

    # Check it's actually a PDF
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    result = await _ingest_cv_from_file(
        db=db,
        filename=filename,
        filepath=filepath,
        delete_after_parse=True,
    )

    # Step 4 — Return response to frontend
    return {
        "success": True,
        **result,
        "message": f"CV parsed successfully. Candidate ID: {result['candidate_id']}"
    }


# ENDPOINT — GET /cv/candidates
# Returns all candidates in the database (for dashboard)
@router.get("/candidates")
async def get_all_candidates(db: AsyncSession = Depends(get_db)):
    """
    Returns a list of all candidates with their basic info and status.
    Used by the frontend dashboard to show uploaded CVs.
    """
    result = await db.execute(
        select(Candidate).order_by(Candidate.uploaded_at.desc())
    )
    candidates = result.scalars().all()

    return {
        "total": len(candidates),
        "candidates": [
            {
                "id": c.id,
                "full_name": c.full_name or "Not yet extracted",
                "filename": c.cv_filename,
                "status": c.status,
                "uploaded_at": c.uploaded_at,
            }
            for c in candidates
        ]
    }


# ENDPOINT — GET /cv/candidate/{id}
# Returns full candidate record including raw text
@router.get("/candidate/{candidate_id}")
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full details of a single candidate by ID.
    """
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate with ID {candidate_id} not found."
        )

    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "address": candidate.address,
        "linkedin_url": candidate.linkedin_url,
        "nationality": candidate.nationality,
        "universities": candidate.universities,
        "filename": candidate.cv_filename,
        "status": candidate.status,
        "overall_summary": candidate.overall_summary,
        "overall_score": candidate.overall_score,
        "raw_text": candidate.cv_raw_text,
        "raw_text_preview": candidate.cv_raw_text[:500] if candidate.cv_raw_text else None,
        "uploaded_at": candidate.uploaded_at,
        "processed_at": candidate.processed_at,
    }


@router.post("/candidate/{candidate_id}/analyze")
async def analyze_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Sends stored raw CV text to Groq, parses JSON, and persists extracted fields
    for the selected candidate entry.
    """
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate with ID {candidate_id} not found."
        )

    if not candidate.cv_raw_text or len(candidate.cv_raw_text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Candidate has no usable raw CV text to analyze."
        )

    candidate.status = ProcessingStatus.PROCESSING
    await db.commit()

    try:
        system_prompt, user_prompt = _candidate_analysis_prompts(candidate.cv_raw_text)
        parsed = await ask_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=LLM_RESPONSE_MAX_TOKENS,
        )

        candidate.full_name = parsed.get("full_name")
        candidate.email = parsed.get("email")
        candidate.phone = parsed.get("phone")
        candidate.address = parsed.get("address")
        candidate.linkedin_url = parsed.get("linkedin_url")
        candidate.nationality = parsed.get("nationality")
        candidate.universities = parsed.get("universities")
        candidate.overall_summary = parsed.get("overall_summary")

        score = parsed.get("overall_score")
        if isinstance(score, (int, float)):
            candidate.overall_score = max(0.0, min(100.0, float(score)))

        _rename_cv_filename_from_candidate_name(candidate)

        candidate.status = ProcessingStatus.COMPLETED
        candidate.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(candidate)

        return {
            "success": True,
            "message": "Candidate analyzed and saved successfully.",
            "candidate_id": candidate.id,
            "status": candidate.status,
            "analysis": parsed,
        }

    except Exception as e:
        candidate.status = ProcessingStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"LLM analysis failed: {str(e)}"
        )


@router.post("/candidate/{candidate_id}/preprocess")
async def preprocess_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Build and export structured tabular data for one candidate.
    """
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate with ID {candidate_id} not found.")

    raw_text = candidate.cv_raw_text or ""
    if len(raw_text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Candidate has insufficient raw CV text for preprocessing.")

    dataset, exports = build_and_export_dataset(
        raw_text=raw_text,
        candidate_id=candidate.id,
        filename=candidate.cv_filename,
    )

    return {
        "success": True,
        "candidate_id": candidate.id,
        "dataset": dataset.to_dict(),
        "exports": exports,
    }


@router.post("/preprocess/export")
async def export_all_structured_datasets(db: AsyncSession = Depends(get_db)):
    """
    Generate structured exports for all candidates with available raw CV text.
    """
    result = await db.execute(select(Candidate).order_by(Candidate.uploaded_at.desc()))
    candidates = result.scalars().all()

    export_results: list[dict] = []
    for candidate in candidates:
        raw_text = (candidate.cv_raw_text or "").strip()
        if len(raw_text) < 50:
            continue

        dataset, exports = build_and_export_dataset(
            raw_text=raw_text,
            candidate_id=candidate.id,
            filename=candidate.cv_filename,
        )
        export_results.append(
            {
                "candidate_id": candidate.id,
                "filename": candidate.cv_filename,
                "exports": exports,
                "metadata": dataset.metadata,
            }
        )

    export_dir = export_results[0]["exports"]["directory"].rsplit(os.sep, 1)[0] if export_results else ""

    return {
        "success": True,
        "count": len(export_results),
        "export_dir": export_dir,
        "results": export_results,
    }


# =============================================================================
# HELPER — Detect blank pages and split a combined PDF into CV segments
# A page is "blank" when it has fewer than BLANK_THRESHOLD printable chars.
# Consecutive blank pages are treated as a single separator.
# =============================================================================

BLANK_THRESHOLD = 30  # characters


def _split_combined_cv_pdf(filepath: str) -> list[tuple[int, int]]:
    """
    Open a combined PDF and return a list of (start_page, end_page) tuples,
    one tuple per detected CV segment.

    Strategy:
      1. Mark every page whose extracted text < BLANK_THRESHOLD as blank.
      2. Walk the page list; when we hit a non-blank run, record it as a segment.
      3. A segment must contain at least 1 non-blank page.
    """
    doc = fitz.open(filepath)
    total_pages = len(doc)

    blank: set[int] = set()
    for page_num in range(total_pages):
        page_text = doc[page_num].get_text().strip()
        if len(page_text) < BLANK_THRESHOLD:
            blank.add(page_num)

    doc.close()

    segments: list[tuple[int, int]] = []
    i = 0
    while i < total_pages:
        # Skip over blank / separator pages
        if i in blank:
            i += 1
            continue

        # We are at the start of a non-blank run — record the segment
        seg_start = i
        while i < total_pages and i not in blank:
            i += 1
        seg_end = i - 1  # last non-blank page in this run

        if seg_end >= seg_start:
            segments.append((seg_start, seg_end))

    return segments


# =============================================================================
# ENDPOINT — POST /cv/upload/bulk-combined
# Accept ONE PDF that contains many CVs separated by blank pages.
# Splits it into individual segments and ingests each as a separate candidate.
# =============================================================================

@router.post("/upload/bulk-combined")
async def upload_bulk_combined_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a single PDF that contains multiple CVs separated by blank pages.

    Processing steps:
      1. Save the combined PDF to uploads/ temporarily.
      2. Detect blank-page separators with PyMuPDF.
      3. Extract each CV segment into a separate PDF file.
      4. Ingest each segment as an independent candidate record.
      5. Delete all temporary files.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # ---- Save the combined upload temporarily ----
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    temp_combined_name = f"_combined_{ts}.pdf"
    temp_combined_path = os.path.join(UPLOAD_DIR, temp_combined_name)

    with open(temp_combined_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # ---- Detect CV segments ----
    try:
        segments = _split_combined_cv_pdf(temp_combined_path)
    except Exception as exc:
        _try_remove(temp_combined_path)
        raise HTTPException(status_code=422, detail=f"Failed to analyse combined PDF: {str(exc)}")

    if not segments:
        _try_remove(temp_combined_path)
        raise HTTPException(
            status_code=422,
            detail=(
                "No CV segments detected in the PDF. "
                "Ensure individual CVs are separated by at least one blank page."
            ),
        )

    # ---- Extract and ingest each segment ----
    results: list[dict] = []
    segment_paths: list[str] = []

    for idx, (start_page, end_page) in enumerate(segments, start=1):
        seg_ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        seg_filename = f"_cv_seg{idx}_{seg_ts}.pdf"
        seg_path = os.path.join(UPLOAD_DIR, seg_filename)
        segment_paths.append(seg_path)

        try:
            # Write the page range into a new PDF file
            src_doc = fitz.open(temp_combined_path)
            seg_doc = fitz.open()
            seg_doc.insert_pdf(src_doc, from_page=start_page, to_page=end_page)
            seg_doc.save(seg_path)
            seg_doc.close()
            src_doc.close()

            # Validate extracted text before ingesting
            seg_text = sanitize_cv_text(extract_text_from_pdf(seg_path))
            if not seg_text or len(seg_text.strip()) < 50:
                results.append({
                    "success": False,
                    "segment": idx,
                    "pages": f"{start_page + 1}-{end_page + 1}",
                    "error": "Segment has insufficient text — may be an image-only CV.",
                })
                _try_remove(seg_path)
                continue

            parsed = await _ingest_cv_from_file(
                db=db,
                filename=seg_filename,
                filepath=seg_path,
                delete_after_parse=True,  # cleanup handled by ingestor
            )
            results.append({
                "success": True,
                "segment": idx,
                "pages": f"{start_page + 1}-{end_page + 1}",
                **parsed,
            })

        except Exception as exc:
            _try_remove(seg_path)
            results.append({
                "success": False,
                "segment": idx,
                "pages": f"{start_page + 1}-{end_page + 1}",
                "error": str(exc),
            })

    # ---- Clean up the combined temp file ----
    _try_remove(temp_combined_path)

    processed = sum(1 for r in results if r.get("success"))
    failed    = len(results) - processed

    return {
        "success":                failed == 0,
        "total_segments_detected": len(segments),
        "processed":              processed,
        "failed":                 failed,
        "results":                results,
    }


def _try_remove(path: str) -> None:
    """Delete a file silently — used for cleanup of temp files."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass