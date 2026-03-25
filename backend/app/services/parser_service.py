import json
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.candidate import Candidate
from backend.app.services.llm_service import LLMService
from backend.app.utils.file_utils import ensure_dir, timestamp_slug
from backend.app.utils.pdf_utils import extract_text_from_pdf


class ParserService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()
        ensure_dir(settings.RAW_CV_DIR)
        ensure_dir(settings.PARSED_JSON_DIR)
        ensure_dir(settings.EXPORT_DIR)

    def process_folder(self, folder_path: str, overwrite_existing: bool = False) -> dict:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        pdf_files = sorted(folder.glob("*.pdf"))
        results: list[dict] = []
        rows_for_export: list[dict] = []

        processed = skipped = failed = 0
        for pdf_path in pdf_files:
            existing = self.db.query(Candidate).filter(Candidate.source_file == pdf_path.name).first()
            if existing and not overwrite_existing:
                skipped += 1
                results.append({"file": pdf_path.name, "status": "skipped", "reason": "already_exists"})
                continue

            try:
                raw_text = extract_text_from_pdf(pdf_path)
                parsed = self.llm.parse_cv_text(raw_text)
                saved = self._save_candidate(pdf_path.name, raw_text, parsed, existing)
                self._save_json_file(pdf_path.stem, parsed)

                rows_for_export.append(self._flatten_for_export(saved.id, pdf_path.name, parsed))
                processed += 1
                results.append({"file": pdf_path.name, "status": "processed", "candidate_id": saved.id})
            except Exception as exc:
                failed += 1
                results.append({"file": pdf_path.name, "status": "failed", "error": str(exc)})

        export_csv, export_xlsx = self._export_rows(rows_for_export)
        return {
            "processed_count": processed,
            "skipped_count": skipped,
            "failed_count": failed,
            "files": results,
            "export_csv": str(export_csv),
            "export_xlsx": str(export_xlsx),
        }

    def _save_candidate(self, source_file: str, raw_text: str, parsed: dict, existing: Candidate | None) -> Candidate:
        info = parsed.get("personal_info", {})
        skills = parsed.get("skills", [])

        model = existing or Candidate(source_file=source_file, raw_text=raw_text, parsed_json=json.dumps(parsed))
        model.full_name = info.get("full_name")
        model.email = info.get("email")
        model.phone = info.get("phone")
        model.location = info.get("location")
        model.skills_csv = ", ".join(skills) if isinstance(skills, list) else str(skills)
        model.raw_text = raw_text
        model.parsed_json = json.dumps(parsed, ensure_ascii=False)

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def _save_json_file(self, stem: str, parsed: dict) -> Path:
        out = settings.PARSED_JSON_DIR / f"{stem}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def _flatten_for_export(self, candidate_id: int, source_file: str, parsed: dict) -> dict:
        info = parsed.get("personal_info", {})
        skills = parsed.get("skills", [])
        return {
            "candidate_id": candidate_id,
            "source_file": source_file,
            "full_name": info.get("full_name", ""),
            "email": info.get("email", ""),
            "phone": info.get("phone", ""),
            "location": info.get("location", ""),
            "skills": " | ".join(skills) if isinstance(skills, list) else str(skills),
            "education_count": len(parsed.get("education", [])),
            "experience_count": len(parsed.get("experience", [])),
            "publication_count": len(parsed.get("publications", [])),
            "patent_count": len(parsed.get("patents", [])),
            "book_count": len(parsed.get("books", [])),
        }

    def _export_rows(self, rows: list[dict]) -> tuple[Path, Path]:
        stamp = timestamp_slug()
        csv_path = settings.EXPORT_DIR / f"talash_export_{stamp}.csv"
        xlsx_path = settings.EXPORT_DIR / f"talash_export_{stamp}.xlsx"

        frame = pd.DataFrame(rows)
        frame.to_csv(csv_path, index=False)
        frame.to_excel(xlsx_path, index=False)
        return csv_path, xlsx_path

