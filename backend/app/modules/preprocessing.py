from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))

DEGREE_KEYWORDS = {
    "SSE / Matric": ["matric", "ssc", "secondary school", "o-level"],
    "HSSC / Intermediate": ["intermediate", "hssc", "fsc", "fa ", "ics", "a-level"],
    "BS / BSc": ["bs ", "b.s", "bsc", "b.sc", "bachelor"],
    "MS / MPhil": ["ms ", "m.s", "mphil", "m.phil", "master"],
    "PhD": ["phd", "ph.d"],
}

SKILL_KEYWORDS = {
    "Programming": ["python", "java", "c++", "c#", "javascript", "typescript", "sql"],
    "Data / Analytics": ["data analysis", "pandas", "numpy", "power bi", "tableau", "statistics"],
    "AI / ML": ["machine learning", "deep learning", "nlp", "computer vision", "llm", "ai"],
    "Web / Software": ["fastapi", "django", "flask", "react", "node", "api", "software"],
    "Academic": ["research", "thesis", "publication", "journal", "conference", "supervisor"],
}

PUBLICATION_KEYWORDS = ["journal", "conference", "proceedings", "publication", "paper", "article"]
EXPERIENCE_KEYWORDS = ["experience", "employment", "worked", "position", "lecturer", "assistant professor", "intern", "engineer", "developer", "research assistant"]


@dataclass
class StructuredDataset:
    candidate_id: int | None
    filename: str | None
    generated_at: str
    personal_info: list[dict[str, Any]]
    education_records: list[dict[str, Any]]
    experience_records: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    publications: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "filename": self.filename,
            "generated_at": self.generated_at,
            "personal_info": self.personal_info,
            "education_records": self.education_records,
            "experience_records": self.experience_records,
            "skills": self.skills,
            "publications": self.publications,
            "gaps": self.gaps,
            "metadata": self.metadata,
        }


def normalize_whitespace(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _has_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def _extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))


def _extract_phones(text: str) -> list[str]:
    matches = re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}(?:[\s-]?\d{3,4})?", text)
    cleaned = []
    for match in matches:
        value = re.sub(r"\s+", " ", match).strip()
        if len(re.sub(r"\D", "", value)) >= 8:
            cleaned.append(value)
    return list(dict.fromkeys(cleaned))


def _extract_linkedin(text: str) -> list[str]:
    matches = re.findall(r"https?://(?:www\.)?linkedin\.com/[\w\-./?=&%]+", text, flags=re.IGNORECASE)
    return list(dict.fromkeys(matches))


def _find_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_personal_info(raw_text: str, candidate_id: int | None = None, filename: str | None = None) -> list[dict[str, Any]]:
    text = normalize_whitespace(raw_text)
    emails = _extract_emails(text)
    phones = _extract_phones(text)
    linkedins = _extract_linkedin(text)

    name_guess = None
    lines = _find_lines(raw_text)
    for line in lines[:12]:
        if any(token in line.lower() for token in ["cv", "resume", "curriculum vitae", "profile", "email", "phone"]):
            continue
        if 2 <= len(line.split()) <= 5 and not re.search(r"\d", line):
            name_guess = line
            break

    address_guess = None
    address_keywords = ["address", "street", "road", "avenue", "lane", "city", "town", "sector", "block"]
    for line in lines:
        if _has_any(line, address_keywords) and len(line) > 12:
            address_guess = line
            break

    nationality_guess = None
    nationality_match = re.search(r"\b(nationality|citizenship)[:\-]?\s*([A-Za-z][A-Za-z\s-]{2,30})", raw_text, flags=re.IGNORECASE)
    if nationality_match:
        nationality_guess = nationality_match.group(2).strip()

    return [
        {
            "candidate_id": candidate_id,
            "filename": filename,
            "full_name": name_guess,
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
            "address": address_guess,
            "linkedin_url": linkedins[0] if linkedins else None,
            "nationality": nationality_guess,
        }
    ]


def extract_education_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)

    degree_terms = [term for terms in DEGREE_KEYWORDS.values() for term in terms]
    for line in lines:
        lower = line.lower()
        if not _has_any(lower, degree_terms):
            continue

        degree_level = None
        for label, terms in DEGREE_KEYWORDS.items():
            if _has_any(lower, terms):
                degree_level = label
                break

        years = re.findall(r"\b(?:19|20)\d{2}\b", line)
        percentages = re.findall(r"\b\d{2,3}(?:\.\d+)?%\b", line)
        cgpas = re.findall(r"\b\d(?:\.\d{1,2})?\s*/\s*\d(?:\.\d{1,2})?\b|\b\d(?:\.\d{1,2})?\s*cgpa\b", line, flags=re.IGNORECASE)

        records.append(
            {
                "candidate_id": candidate_id,
                "degree_level": degree_level,
                "degree_title": line[:180],
                "specialization": None,
                "institution_name": None,
                "board_or_affiliation": None,
                "raw_result": line,
                "cgpa_normalized": None,
                "percentage_normalized": None,
                "year_start": int(years[0]) if years else None,
                "year_end": int(years[-1]) if years else None,
                "performance_note": "; ".join(filter(None, [
                    f"percentage={percentages[0]}" if percentages else None,
                    f"cgpa={cgpas[0]}" if cgpas else None,
                ])) or None,
            }
        )

    return records


def extract_experience_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)

    for line in lines:
        lower = line.lower()
        if not _has_any(lower, EXPERIENCE_KEYWORDS):
            continue

        years = re.findall(r"\b(?:19|20)\d{2}\b", line)
        organization = None
        split_tokens = [" at ", " in ", " @ ", " with "]
        for token in split_tokens:
            if token in lower:
                organization = line.split(token, 1)[1].strip()
                break

        records.append(
            {
                "candidate_id": candidate_id,
                "job_title": line[:160],
                "organization": organization,
                "employment_type": None,
                "start_date": int(years[0]) if years else None,
                "end_date": int(years[-1]) if years else None,
                "is_current": bool(re.search(r"current|present", lower)),
                "responsibilities": line,
                "career_level": None,
                "progression_note": None,
            }
        )

    return records


def extract_skill_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    text = raw_text.lower()
    records: list[dict[str, Any]] = []

    for category, terms in SKILL_KEYWORDS.items():
        for term in terms:
            if term in text:
                records.append(
                    {
                        "candidate_id": candidate_id,
                        "skill_name": term,
                        "skill_category": category,
                        "evidence_strength": "partial",
                        "supported_by_experience": _has_any(text, EXPERIENCE_KEYWORDS),
                        "supported_by_publications": _has_any(text, PUBLICATION_KEYWORDS),
                        "evidence_note": f"Detected keyword '{term}' in CV text.",
                        "job_relevance_score": None,
                    }
                )

    unique = []
    seen = set()
    for record in records:
        key = (record["skill_name"], record["skill_category"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def extract_publication_records(raw_text: str, candidate_id: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    lines = _find_lines(raw_text)

    for line in lines:
        lower = line.lower()
        if not _has_any(lower, PUBLICATION_KEYWORDS):
            continue

        year_match = re.search(r"\b(?:19|20)\d{2}\b", line)
        pub_type = "conference" if "conference" in lower or "proceedings" in lower else "journal" if "journal" in lower else "publication"

        records.append(
            {
                "candidate_id": candidate_id,
                "pub_type": pub_type,
                "title": line[:240],
                "authors_raw": None,
                "year": int(year_match.group(0)) if year_match else None,
                "authorship_role": None,
                "candidate_author_position": None,
                "quality_note": line[:240],
            }
        )

    return records


def detect_gaps(raw_text: str, education_records: list[dict[str, Any]], experience_records: list[dict[str, Any]], candidate_id: int | None = None) -> list[dict[str, Any]]:
    years: list[int] = []

    for record in education_records:
        for key in ("year_start", "year_end"):
            value = record.get(key)
            if isinstance(value, int):
                years.append(value)

    for record in experience_records:
        for key in ("start_date", "end_date"):
            value = record.get(key)
            if isinstance(value, int):
                years.append(value)

    years = sorted(set(years))
    gaps: list[dict[str, Any]] = []
    for index in range(1, len(years)):
        gap_years = years[index] - years[index - 1]
        if gap_years >= 3:
            gaps.append(
                {
                    "candidate_id": candidate_id,
                    "gap_between": f"{years[index - 1]}-{years[index]}",
                    "gap_duration_months": gap_years * 12,
                    "is_justified": None,
                    "justification_note": None,
                }
            )

    return gaps


def build_structured_dataset(raw_text: str, candidate_id: int | None = None, filename: str | None = None) -> StructuredDataset:
    cleaned = normalize_whitespace(raw_text)
    now = datetime.utcnow().isoformat(timespec="seconds")

    personal_info = extract_personal_info(raw_text, candidate_id=candidate_id, filename=filename)
    education_records = extract_education_records(raw_text, candidate_id=candidate_id)
    experience_records = extract_experience_records(raw_text, candidate_id=candidate_id)
    skills = extract_skill_records(raw_text, candidate_id=candidate_id)
    publications = extract_publication_records(raw_text, candidate_id=candidate_id)
    gaps = detect_gaps(raw_text, education_records, experience_records, candidate_id=candidate_id)

    detected_sections = []
    for label, terms in {
        "education": ["education", "qualification", "academic"],
        "experience": ["experience", "employment", "career"],
        "research": ["publication", "conference", "journal", "research"],
        "skills": ["skills", "technical", "tools"],
    }.items():
        if _has_any(cleaned, terms):
            detected_sections.append(label)

    metadata = {
        "character_count": len(raw_text or ""),
        "line_count": len(_find_lines(raw_text)),
        "detected_sections": detected_sections,
        "personal_info_completeness": sum(1 for field in personal_info[0].values() if field) if personal_info else 0,
        "education_records_count": len(education_records),
        "experience_records_count": len(experience_records),
        "skills_count": len(skills),
        "publications_count": len(publications),
        "gaps_count": len(gaps),
    }

    return StructuredDataset(
        candidate_id=candidate_id,
        filename=filename,
        generated_at=now,
        personal_info=personal_info,
        education_records=education_records,
        experience_records=experience_records,
        skills=skills,
        publications=publications,
        gaps=gaps,
        metadata=metadata,
    )


def _table_rows(dataset: StructuredDataset) -> dict[str, list[dict[str, Any]]]:
    return {
        "personal_info": dataset.personal_info,
        "education_records": dataset.education_records,
        "experience_records": dataset.experience_records,
        "skills": dataset.skills,
        "publications": dataset.publications,
        "gaps": dataset.gaps,
    }


def export_structured_dataset(dataset: StructuredDataset, export_dir: Path | None = None) -> dict[str, str]:
    base_dir = export_dir or DEFAULT_EXPORT_DIR
    candidate_label = f"candidate_{dataset.candidate_id}" if dataset.candidate_id is not None else "dataset"
    target_dir = base_dir / candidate_label
    target_dir.mkdir(parents=True, exist_ok=True)

    rows = _table_rows(dataset)
    csv_files: dict[str, str] = {}

    for table_name, table_rows in rows.items():
        csv_path = target_dir / f"{table_name}.csv"
        fieldnames = sorted({key for row in table_rows for key in row.keys()}) if table_rows else []
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(table_rows)
        csv_files[table_name] = str(csv_path)

    workbook_path = target_dir / f"{candidate_label}_structured_profile.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        for table_name, table_rows in rows.items():
            pd.DataFrame(table_rows).to_excel(writer, sheet_name=table_name[:31], index=False)
        pd.DataFrame([dataset.metadata]).to_excel(writer, sheet_name="summary", index=False)

    manifest = {
        "candidate_id": str(dataset.candidate_id) if dataset.candidate_id is not None else "",
        "filename": dataset.filename or "",
        "generated_at": dataset.generated_at,
        "workbook_path": str(workbook_path),
        "tables": json.dumps(csv_files, ensure_ascii=False),
    }
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "directory": str(target_dir),
        "workbook": str(workbook_path),
        "manifest": str(manifest_path),
        **csv_files,
    }


def build_and_export_dataset(raw_text: str, candidate_id: int | None = None, filename: str | None = None, export_dir: Path | None = None) -> tuple[StructuredDataset, dict[str, str]]:
    dataset = build_structured_dataset(raw_text=raw_text, candidate_id=candidate_id, filename=filename)
    exports = export_structured_dataset(dataset, export_dir=export_dir)
    return dataset, exports
