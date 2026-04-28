from __future__ import annotations

import re
from typing import Any

from app.llm.llm_client import ask_publication_llm


# =============================================================================
# PUBLICATION SECTION EXTRACTION
# Strategy: find the start of the publications section and extract a generous
# chunk of text from that point forward. We are deliberately NOT cutting at
# "awards" etc. because tables often span pages and a conservative cut was
# the root cause of missed publications.
# =============================================================================

_PUB_SECTION_HEADERS = [
    "research publication", "publications", "research papers", "journal papers",
    "conference papers", "papers published", "published papers", "articles",
    "research work", "scholarly work", "peer-reviewed", "refereed",
]

# Only cut at clearly unrelated sections that would never contain publications
_HARD_STOP_HEADERS = [
    "declaration", "personal detail", "hobby", "interest",
    "volunteer", "membership", "affiliation", "language proficiency",
    "objective", "career objective",
]

# Maximum chars we send to the LLM (large to capture multi-page tables)
_MAX_SECTION_CHARS = 20_000
# Minimum chars required to conclude there are publications worth analysing
_MIN_SECTION_CHARS = 30


def _extract_publications_section(raw_text: str) -> str:
    """
    Locate the publications portion of the CV text and return a generous slice.
    - Searches for common publication section headers.
    - Only cuts at hard-stop sections (declaration, hobbies, …) so that
      publications spread across multiple pages are NOT truncated early.
    - Falls back to the whole CV (truncated) when no header is found.
    """
    lower = raw_text.lower()

    # Find the earliest publications section header
    start_idx = -1
    for header in _PUB_SECTION_HEADERS:
        idx = lower.find(header)
        if idx != -1 and (start_idx == -1 or idx < start_idx):
            start_idx = idx

    if start_idx == -1:
        # No section header — send the full CV, LLM will find publications
        return raw_text[:_MAX_SECTION_CHARS]

    # Find an early hard-stop if present (ignore soft stops like "awards")
    end_idx = len(raw_text)
    search_region = lower[start_idx + 80:]  # skip past the header itself
    for stop in _HARD_STOP_HEADERS:
        idx = search_region.find(stop)
        if idx != -1:
            candidate_end = start_idx + 80 + idx
            if candidate_end < end_idx:
                end_idx = candidate_end

    section_text = raw_text[start_idx:end_idx]

    # If section is tiny, fall back to full CV — perhaps headers are embedded in tables
    if len(section_text.strip()) < _MIN_SECTION_CHARS:
        return raw_text[:_MAX_SECTION_CHARS]

    return section_text[:_MAX_SECTION_CHARS]


# =============================================================================
# LLM PROMPTS
# =============================================================================

_SYSTEM_PROMPT = """
You are an expert academic CV analyser specialising in research publication extraction.
Extract EVERY SINGLE publication listed in the CV — journals, conferences, books, book chapters.

Publications often appear in TABLES with columns like:
  Paper Title | Name of Author | Name of CO-Author | Published In | No | Impact Factor | Vol | PP | Date

Extract EVERY TABLE ROW as a separate publication. Do not skip any row.
The CV may span multiple pages — ensure all publications across all pages are captured.

Return ONLY valid JSON with no markdown fences, no prose, no trailing commas.
If a value cannot be determined, use null.

JSON schema (return exactly this):
{
  "publications": [
    {
      "title": string|null,
      "pub_type": "journal"|"conference"|"book"|"book_chapter"|"other",
      "authors_raw": string|null,
      "year": integer|null,
      "candidate_author_position": integer|null,
      "quality_note": string|null,
      "journal": {
        "journal_name": string|null,
        "issn": string|null,
        "is_wos_indexed": boolean|null,
        "impact_factor": number|null,
        "is_scopus_indexed": boolean|null,
        "quartile": string|null,
        "is_predatory": boolean|null
      },
      "conference": {
        "conference_name": string|null,
        "proceedings_title": string|null,
        "core_rank": string|null,
        "is_a_star": boolean|null,
        "series_edition": string|null,
        "is_scopus_indexed": boolean|null,
        "is_ieee_xplore": boolean|null,
        "is_springer": boolean|null,
        "is_acm": boolean|null,
        "other_indexing": string|null
      },
      "co_authors": [
        { "co_author_name": string, "author_position": integer|null }
      ]
    }
  ],
  "coauthor_analysis": {
    "total_unique_coauthors": integer|null,
    "avg_coauthors_per_paper": number|null,
    "max_coauthors_in_paper": integer|null,
    "recurring_collaborators": [{"name": string, "count": integer}],
    "most_frequent_collaborator": string|null,
    "collaboration_diversity_score": number|null,
    "has_student_collaborations": boolean|null,
    "has_international_collaborations": boolean|null,
    "collaboration_summary": string|null
  },
  "topic_variability": {
    "dominant_topic": string|null,
    "diversity_score": number|null,
    "topic_clusters": [string],
    "topic_trend": string|null, # briefly describe how topics evolved over years, e.g. "Started with networking, moved to deep learning". Calculate this based on publication years.
    "variability_summary": string|null
  }
}

Critical rules:
- pub_type "journal" → fill journal object, set conference fields to null.
- pub_type "conference" → fill conference object, set journal fields to null.
- candidate_author_position: position of THIS candidate in the author list (1 = first).
- impact_factor: numeric value only (e.g. 2.10 not "2.10 / 5").
- is_wos_indexed / is_scopus_indexed: infer from impact_factor presence or explicit mention.
- collaboration_diversity_score: 0.0–1.0 (higher = more diverse).
- diversity_score: 0.0–1.0 (higher = more varied topics).
- Do NOT invent data absent from the text.
- Do NOT stop early — extract every single publication present.
""".strip()


def _build_user_prompt(cv_section: str, candidate_name: str | None) -> str:
    name_hint = (
        f"The candidate's name is: {candidate_name}. "
        "Exclude this name when listing co_authors.\n"
    ) if candidate_name else ""
    return (
        f"Extract ALL publications from the following CV text.\n"
        f"{name_hint}"
        "Pay special attention to table rows — each row is a separate publication.\n"
        "The table may span multiple pages; extract every row you see.\n\n"
        f"CV TEXT:\n{cv_section}"
    )


# =============================================================================
# PUBLIC API
# =============================================================================

async def analyze_publications_deep(
    raw_text: str,
    candidate_name: str | None = None,
) -> dict[str, Any]:
    """
    Deep LLM-powered publication analysis using the dedicated second Groq API key.
    Returns a structured dict ready for DB insertion.
    """
    pub_section = _extract_publications_section(raw_text)

    if len(pub_section.strip()) < _MIN_SECTION_CHARS:
        return _empty_result()

    user_prompt = _build_user_prompt(pub_section, candidate_name)

    try:
        parsed = await ask_publication_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,   # deterministic extraction
            max_tokens=8000,   # generous — 5+ publications with full metadata
        )
        print(parsed)
    except Exception as exc:
        raise RuntimeError(f"Publication LLM analysis failed: {exc}") from exc

    publications  = parsed.get("publications") or []
    coauthor_data = parsed.get("coauthor_analysis") or {}
    topic_data    = parsed.get("topic_variability") or {}

    publications = [p for p in publications if isinstance(p, dict)]

    # Compute summary statistics
    journal_count    = sum(1 for p in publications if p.get("pub_type") == "journal")
    conference_count = sum(1 for p in publications if p.get("pub_type") == "conference")
    years = sorted({p["year"] for p in publications if isinstance(p.get("year"), int)})
    ifs   = [
        float(p["journal"]["impact_factor"])
        for p in publications
        if isinstance((p.get("journal") or {}).get("impact_factor"), (int, float))
    ]
    avg_if = round(sum(ifs) / len(ifs), 3) if ifs else None

    return {
        "publications":      publications,
        "coauthor_analysis": coauthor_data,
        "topic_variability": topic_data,
        "summary": {
            "total_publications":   len(publications),
            "journal_count":        journal_count,
            "conference_count":     conference_count,
            "publication_years":    years,
            "avg_impact_factor":    avg_if,
            "max_impact_factor":    max(ifs) if ifs else None,
            "wos_indexed_count":    sum(
                1 for p in publications
                if (p.get("journal") or {}).get("is_wos_indexed") is True
            ),
            "scopus_indexed_count": sum(
                1 for p in publications
                if (
                    (p.get("journal") or {}).get("is_scopus_indexed") is True
                    or (p.get("conference") or {}).get("is_scopus_indexed") is True
                )
            ),
        },
    }


# =============================================================================
# Legacy stub — kept for backward compatibility with the /analysis/full endpoint
# =============================================================================

async def analyze_research(raw_text: str) -> dict[str, Any]:
    """
    Lightweight research profile used by the full-analysis pipeline.
    Returns basic publication counts without deep LLM calls.
    """
    from app.modules.preprocessing import extract_publication_records

    publications     = extract_publication_records(raw_text)
    journal_count    = sum(1 for p in publications if p.get("pub_type") == "journal")
    conference_count = sum(1 for p in publications if p.get("pub_type") == "conference")

    return {
        "publications": publications,
        "summary": {
            "publications_count":    len(publications),
            "journal_count":         journal_count,
            "conference_count":      conference_count,
            "is_partial_processing": True,
        },
    }


def _empty_result() -> dict[str, Any]:
    return {
        "publications":      [],
        "coauthor_analysis": {},
        "topic_variability": {},
        "summary": {
            "total_publications":   0,
            "journal_count":        0,
            "conference_count":     0,
            "publication_years":    [],
            "avg_impact_factor":    None,
            "max_impact_factor":    None,
            "wos_indexed_count":    0,
            "scopus_indexed_count": 0,
        },
    }
