from __future__ import annotations

import re
from typing import Any

from app.modules.preprocessing import extract_education_records
from app.modules.qs_ranking_matcher import get_qs_ranking


def _split_universities(raw: str) -> list[str]:
    """
    Split a comma/semicolon/newline separated university string into
    individual institution names, cleaning up whitespace.
    """
    parts = re.split(r"[,;\n]+", raw or "")
    return [p.strip() for p in parts if p.strip()]


async def analyze_education(raw_text: str, candidate_universities: str | None = None) -> dict[str, Any]:
    """Build a structured educational profile summary from CV text."""
    records = extract_education_records(raw_text)

    levels = [r.get("degree_level") for r in records if r.get("degree_level")]
    years = sorted(
        {
            year
            for r in records
            for year in (r.get("year_start"), r.get("year_end"))
            if isinstance(year, int)
        }
    )

    # ---- QS ranking: search EACH university separately ----
    qs_results: list[dict[str, Any]] = []
    if candidate_universities:
        uni_list = _split_universities(candidate_universities)
        for uni in uni_list:
            matched_name, ranking = get_qs_ranking(uni)
            qs_results.append({
                "searched_university": uni,
                "matched_institution": matched_name if ranking is not None else None,
                "qs_ranking": ranking,
                "available": ranking is not None,
            })

    # Build education gap list
    gaps: list[dict[str, Any]] = []
    for idx in range(1, len(years)):
        gap_years = years[idx] - years[idx - 1]
        if gap_years >= 3:
            gaps.append(
                {
                    "gap_between": f"{years[idx - 1]}-{years[idx]}",
                    "gap_years": gap_years,
                }
            )

    # Attach best available QS ranking info to the last education record
    if records and qs_results:
        best = next((q for q in qs_results if q["available"]), qs_results[0])
        records[-1]["institution_name"] = best.get("matched_institution") or candidate_universities
        records[-1]["qs_ranking"] = best.get("qs_ranking")

    # For backward compatibility, expose a single qs_ranking_info as well as the list
    first_ranked = next((q for q in qs_results if q["available"]), None)
    qs_ranking_info_legacy = {
        "searched_university": candidate_universities,
        "matched_institution": first_ranked["matched_institution"] if first_ranked else None,
        "qs_ranking": first_ranked["qs_ranking"] if first_ranked else None,
    }

    return {
        "records": records,
        "highest_qualification": levels[-1] if levels else None,
        "degree_path": levels,
        "educational_years": years,
        "education_gaps": gaps,
        "qs_rankings": qs_results,           # NEW: full per-university list
        "qs_ranking_info": qs_ranking_info_legacy,  # kept for backward compat
        "summary": {
            "records_count": len(records),
            "has_school_stage": any(
                level in {"SSE / Matric", "HSSC / Intermediate"} for level in levels
            ),
            "has_higher_education": any(
                level in {"BS / BSc", "MS / MPhil", "PhD"} for level in levels
            ),
            "gap_count": len(gaps),
        },
    }
