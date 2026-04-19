from __future__ import annotations

import re
from typing import Any

from app.modules.preprocessing import extract_education_records, extract_experience_records

PRODUCTIVE_ACTIVITY_KEYWORDS = {
    "higher education": ["ms", "mphil", "phd", "masters", "degree", "university"],
    "research assistantship": ["research assistant", "ra"],
    "internship": ["intern", "internship"],
    "freelancing": ["freelance", "freelancer"],
    "consultancy": ["consultant", "consultancy"],
    "entrepreneurship": ["startup", "entrepreneur", "founder"],
    "training": ["training", "certification", "course"],
    "teaching": ["lecturer", "teaching", "instructor", "assistant professor"],
}


def _period(record_start: int | None, record_end: int | None) -> tuple[int | None, int | None]:
    if record_start is None and record_end is None:
        return None, None
    if record_start is None:
        return record_end, record_end
    if record_end is None:
        return record_start, record_start
    return min(record_start, record_end), max(record_start, record_end)


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) <= min(a_end, b_end)


def _job_level_score(title: str | None) -> int:
    if not title:
        return 0
    lower = title.lower()
    if any(token in lower for token in ["head", "director", "chair", "professor"]):
        return 5
    if any(token in lower for token in ["lead", "principal", "senior", "manager", "assistant professor"]):
        return 4
    if any(token in lower for token in ["engineer", "developer", "analyst", "lecturer"]):
        return 3
    if any(token in lower for token in ["associate", "junior", "intern", "trainee", "assistant"]):
        return 2
    return 1


def _extract_gap_justification(raw_text: str, gap_start: int, gap_end: int) -> tuple[bool, str | None]:
    lower = raw_text.lower()
    years_in_gap = {str(year) for year in range(gap_start, gap_end + 1)}

    for label, keywords in PRODUCTIVE_ACTIVITY_KEYWORDS.items():
        if not any(keyword in lower for keyword in keywords):
            continue

        # Prefer stronger justification if the activity is close to timeline years in gap.
        for line in raw_text.splitlines():
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords) and (
                any(year in line for year in years_in_gap) or not years_in_gap
            ):
                return True, f"Gap likely justified by {label} activity: '{line.strip()[:140]}'"

        return True, f"Gap may be justified by {label} activity mentioned in CV."

    return False, None


async def analyze_experience(raw_text: str) -> dict[str, Any]:
    """
    Analyze professional timeline quality including overlaps and gap justification.

    Includes:
    - education-employment overlap logic
    - job-job overlap logic
    - explicit justification reasoning for professional gaps
    """
    education_records = extract_education_records(raw_text)
    experience_records = extract_experience_records(raw_text)

    education_periods: list[dict[str, Any]] = []
    for edu in education_records:
        start, end = _period(edu.get("year_start"), edu.get("year_end"))
        if start is None or end is None:
            continue
        education_periods.append(
            {
                "label": edu.get("degree_level") or edu.get("degree_title") or "education",
                "start_year": start,
                "end_year": end,
            }
        )

    job_periods: list[dict[str, Any]] = []
    for job in experience_records:
        start, end = _period(job.get("start_date"), job.get("end_date"))
        if start is None or end is None:
            continue
        job_periods.append(
            {
                "job_title": job.get("job_title") or "role",
                "organization": job.get("organization"),
                "start_year": start,
                "end_year": end,
            }
        )

    education_employment_overlaps: list[dict[str, Any]] = []
    for edu in education_periods:
        for job in job_periods:
            if _overlap(edu["start_year"], edu["end_year"], job["start_year"], job["end_year"]):
                education_employment_overlaps.append(
                    {
                        "education": edu["label"],
                        "job_title": job["job_title"],
                        "organization": job["organization"],
                        "overlap_window": f"{max(edu['start_year'], job['start_year'])}-{min(edu['end_year'], job['end_year'])}",
                    }
                )

    job_overlaps: list[dict[str, Any]] = []
    for i in range(len(job_periods)):
        for j in range(i + 1, len(job_periods)):
            left, right = job_periods[i], job_periods[j]
            if _overlap(left["start_year"], left["end_year"], right["start_year"], right["end_year"]):
                job_overlaps.append(
                    {
                        "job_a": left["job_title"],
                        "job_b": right["job_title"],
                        "overlap_window": f"{max(left['start_year'], right['start_year'])}-{min(left['end_year'], right['end_year'])}",
                    }
                )

    sorted_jobs = sorted(job_periods, key=lambda item: (item["start_year"], item["end_year"]))
    professional_gaps: list[dict[str, Any]] = []
    for idx in range(1, len(sorted_jobs)):
        prev_end = sorted_jobs[idx - 1]["end_year"]
        next_start = sorted_jobs[idx]["start_year"]
        gap_years = next_start - prev_end
        if gap_years <= 1:
            continue

        gap_start = prev_end + 1
        gap_end = next_start - 1
        is_justified, justification_note = _extract_gap_justification(raw_text, gap_start, gap_end)

        professional_gaps.append(
            {
                "gap_window": f"{gap_start}-{gap_end}",
                "gap_duration_years": gap_years - 1,
                "is_justified": is_justified,
                "justification_note": justification_note or "No clear productive activity found in CV text for this gap.",
            }
        )

    progression_signal = "insufficient data"
    if len(sorted_jobs) >= 2:
        first_score = _job_level_score(sorted_jobs[0].get("job_title"))
        last_score = _job_level_score(sorted_jobs[-1].get("job_title"))
        if last_score > first_score:
            progression_signal = "upward"
        elif last_score < first_score:
            progression_signal = "downward"
        else:
            progression_signal = "stable"

    return {
        "records": experience_records,
        "timeline_checks": {
            "education_employment_overlaps": education_employment_overlaps,
            "job_overlaps": job_overlaps,
            "professional_gaps": professional_gaps,
            "progression_signal": progression_signal,
        },
        "summary": {
            "records_count": len(experience_records),
            "education_employment_overlap_count": len(education_employment_overlaps),
            "job_overlap_count": len(job_overlaps),
            "professional_gap_count": len(professional_gaps),
            "unjustified_gap_count": len([gap for gap in professional_gaps if not gap.get("is_justified")]),
        },
    }
