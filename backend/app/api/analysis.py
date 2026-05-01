# =============================================================================
# TALASH - Full Candidate Analysis API
# app/api/analysis.py
# =============================================================================

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Candidate, ProcessingStatus
from app.modules.education_analysis import analyze_education
from app.modules.experience_analysis import analyze_experience
from app.modules.missing_info import detect_missing_fields, draft_missing_info_email
from app.modules.research_analysis import analyze_research, analyze_publications_deep

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _load_json_col(value: str | None) -> dict | list | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _dump_json(obj: dict | list | None) -> str | None:
    if obj is None:
        return None
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return None


# =============================================================================
# FULL ANALYSIS — education + experience + research (basic)
# =============================================================================

@router.post("/candidate/{candidate_id}/full")
async def run_full_analysis(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    raw = candidate.cv_raw_text or ""
    if len(raw.strip()) < 50:
        raise HTTPException(status_code=422, detail="Not enough CV text to analyze.")

    candidate.status = ProcessingStatus.PROCESSING
    await db.commit()

    try:
        education = await analyze_education(raw, candidate_universities=candidate.universities)
        experience = await analyze_experience(raw)
        research = await analyze_research(raw)

        candidate_snapshot = {
            "full_name": candidate.full_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "nationality": candidate.nationality,
            "universities": candidate.universities,
        }
        missing_fields = detect_missing_fields(candidate_snapshot, education, experience, research)
        draft_email = await draft_missing_info_email(candidate_snapshot, missing_fields)

        await db.execute(
            text(
                """
                UPDATE candidates
                SET education_json    = :edu,
                    experience_json   = :exp,
                    research_json     = :res,
                    missing_info_json = :miss,
                    missing_info_email = :email,
                    status            = CAST(:status AS processing_status),
                    processed_at      = :now
                WHERE id = :cid
                """
            ),
            {
                "edu":    _dump_json(education),
                "exp":    _dump_json(experience),
                "res":    _dump_json(research),
                "miss":   _dump_json(missing_fields),
                "email":  draft_email,
                "status": ProcessingStatus.COMPLETED.value,
                "now":    datetime.utcnow(),
                "cid":    candidate_id,
            },
        )
        await db.commit()

        return {
            "success": True,
            "candidate_id": candidate_id,
            "education": education,
            "experience": experience,
            "research": research,
            "missing_fields": missing_fields,
            "draft_email": draft_email,
        }

    except Exception as exc:
        await db.rollback()
        try:
            result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
            fresh = result.scalar_one_or_none()
            if fresh:
                fresh.status = ProcessingStatus.FAILED
                fresh.processed_at = datetime.utcnow()
                await db.commit()
        except Exception:
            await db.rollback()

        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")


# =============================================================================
# GET ANALYSIS — return cached full analysis
# =============================================================================

@router.get("/candidate/{candidate_id}")
async def get_analysis(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text(
            """
            SELECT id, full_name, education_json, experience_json,
                   research_json, missing_info_json, missing_info_email, status
            FROM candidates
            WHERE id = :cid
            """
        ),
        {"cid": candidate_id},
    )
    record = row.mappings().first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    edu  = _load_json_col(record["education_json"])
    exp  = _load_json_col(record["experience_json"])
    res  = _load_json_col(record["research_json"])
    miss = _load_json_col(record["missing_info_json"])

    return {
        "candidate_id": candidate_id,
        "full_name": record["full_name"],
        "status": record["status"],
        "education": edu,
        "experience": exp,
        "research": res,
        "missing_fields": miss or [],
        "draft_email": record["missing_info_email"] or "",
        "is_analysed": edu is not None or exp is not None,
    }


# =============================================================================
# REDRAFT EMAIL
# =============================================================================

@router.post("/candidate/{candidate_id}/email")
async def redraft_email(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT full_name, email, phone, nationality, universities, missing_info_json FROM candidates WHERE id = :cid"),
        {"cid": candidate_id},
    )
    record = row.mappings().first()
    if not record:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    missing_fields = _load_json_col(record["missing_info_json"]) or []
    candidate_snapshot = {
        "full_name": record["full_name"],
        "email": record["email"],
        "phone": record["phone"],
        "nationality": record["nationality"],
        "universities": record["universities"],
    }
    draft = await draft_missing_info_email(candidate_snapshot, missing_fields)

    await db.execute(
        text("UPDATE candidates SET missing_info_email = :email WHERE id = :cid"),
        {"email": draft, "cid": candidate_id},
    )
    await db.commit()

    return {"success": True, "draft_email": draft}


# =============================================================================
# DEEP PUBLICATION ANALYSIS — POST (run + persist)
# Uses the dedicated second Groq API key for thorough extraction
# Fills: publications, journal_details, conference_details,
#        publication_co_authors, coauthor_analysis, topic_variability
# =============================================================================

@router.post("/candidate/{candidate_id}/publications")
async def run_publication_analysis(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Run deep LLM publication analysis for a candidate.
    Clears and re-fills all publication-related DB tables for this candidate,
    then caches the full result in candidates.publication_analysis_json.
    """
    # --- Fetch candidate ---
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    raw = candidate.cv_raw_text or ""
    if len(raw.strip()) < 50:
        raise HTTPException(status_code=422, detail="Candidate has insufficient CV text for publication analysis.")

    # --- Run LLM analysis ---
    try:
        analysis = await analyze_publications_deep(
            raw_text=raw,
            candidate_name=candidate.full_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Publication analysis failed: {str(exc)}")

    publications   = analysis.get("publications") or []
    coauthor_data  = analysis.get("coauthor_analysis") or {}
    topic_data     = analysis.get("topic_variability") or {}

    # --- Clear existing publication records for this candidate ---
    try:
        # Delete in dependency order (FK constraints)
        await db.execute(text(
            "DELETE FROM topic_variability WHERE candidate_id = :cid"
        ), {"cid": candidate_id})

        await db.execute(text(
            "DELETE FROM coauthor_analysis WHERE candidate_id = :cid"
        ), {"cid": candidate_id})

        await db.execute(text("""
            DELETE FROM publication_co_authors
            WHERE publication_id IN (
                SELECT id FROM publications WHERE candidate_id = :cid
            )
        """), {"cid": candidate_id})

        await db.execute(text("""
            DELETE FROM journal_details
            WHERE publication_id IN (
                SELECT id FROM publications WHERE candidate_id = :cid
            )
        """), {"cid": candidate_id})

        await db.execute(text("""
            DELETE FROM conference_details
            WHERE publication_id IN (
                SELECT id FROM publications WHERE candidate_id = :cid
            )
        """), {"cid": candidate_id})

        await db.execute(text(
            "DELETE FROM publications WHERE candidate_id = :cid"
        ), {"cid": candidate_id})

        await db.commit()

    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear existing publications: {str(exc)}")

    # --- Insert new publications ---
    inserted_pub_ids: list[int] = []

    try:
        for pub in publications:
            # Determine authorship_role safely (nullable enum — use NULL if unsure)
            authorship_role = _safe_authorship_role(pub, publications, candidate.full_name)

            insert_result = await db.execute(text("""
                INSERT INTO publications
                    (candidate_id, pub_type, title, authors_raw, year,
                     authorship_role, candidate_author_position, quality_note)
                VALUES
                    (:candidate_id, :pub_type, :title, :authors_raw, :year,
                     :authorship_role, :candidate_author_position, :quality_note)
                RETURNING id
            """), {
                "candidate_id":              candidate_id,
                "pub_type":                  _safe_str(pub.get("pub_type"), 50) or "other",
                "title":                     _safe_str(pub.get("title")),
                "authors_raw":               _safe_str(pub.get("authors_raw")),
                "year":                      _safe_int(pub.get("year")),
                "authorship_role":           authorship_role,
                "candidate_author_position": _safe_int(pub.get("candidate_author_position")),
                "quality_note":              _safe_str(pub.get("quality_note")),
            })

            pub_id = insert_result.scalar_one()
            inserted_pub_ids.append(pub_id)

            # --- journal_details ---
            journal = pub.get("journal") or {}
            if pub.get("pub_type") == "journal" and any(journal.values()):
                await db.execute(text("""
                    INSERT INTO journal_details
                        (publication_id, journal_name, issn,
                         is_wos_indexed, impact_factor, is_scopus_indexed,
                         quartile, is_predatory)
                    VALUES
                        (:pub_id, :journal_name, :issn,
                         :is_wos_indexed, :impact_factor, :is_scopus_indexed,
                         :quartile, :is_predatory)
                """), {
                    "pub_id":           pub_id,
                    "journal_name":     _safe_str(journal.get("journal_name"), 255),
                    "issn":             _safe_str(journal.get("issn"), 50),
                    "is_wos_indexed":   _safe_bool(journal.get("is_wos_indexed")),
                    "impact_factor":    _safe_float(journal.get("impact_factor")),
                    "is_scopus_indexed":_safe_bool(journal.get("is_scopus_indexed")),
                    "quartile":         _safe_str(journal.get("quartile"), 10),
                    "is_predatory":     _safe_bool(journal.get("is_predatory")),
                })

            # --- conference_details ---
            conf = pub.get("conference") or {}
            if pub.get("pub_type") == "conference" and any(conf.values()):
                await db.execute(text("""
                    INSERT INTO conference_details
                        (publication_id, conference_name, proceedings_title,
                         core_rank, is_a_star, series_edition,
                         is_scopus_indexed, is_ieee_xplore, is_springer,
                         is_acm, other_indexing)
                    VALUES
                        (:pub_id, :conference_name, :proceedings_title,
                         :core_rank, :is_a_star, :series_edition,
                         :is_scopus_indexed, :is_ieee_xplore, :is_springer,
                         :is_acm, :other_indexing)
                """), {
                    "pub_id":            pub_id,
                    "conference_name":   _safe_str(conf.get("conference_name"), 255),
                    "proceedings_title": _safe_str(conf.get("proceedings_title")),
                    "core_rank":         _safe_str(conf.get("core_rank"), 20),
                    "is_a_star":         _safe_bool(conf.get("is_a_star")),
                    "series_edition":    _safe_str(conf.get("series_edition"), 100),
                    "is_scopus_indexed": _safe_bool(conf.get("is_scopus_indexed")),
                    "is_ieee_xplore":    _safe_bool(conf.get("is_ieee_xplore")),
                    "is_springer":       _safe_bool(conf.get("is_springer")),
                    "is_acm":            _safe_bool(conf.get("is_acm")),
                    "other_indexing":    _safe_str(conf.get("other_indexing"), 255),
                })

            # --- publication_co_authors ---
            co_authors = pub.get("co_authors") or []
            for position, co in enumerate(co_authors, start=1):
                if not isinstance(co, dict):
                    continue
                co_name = _safe_str(co.get("co_author_name"), 255)
                if not co_name:
                    continue
                # Determine if this co-author is recurring (appears in multiple papers)
                is_recurring = _is_recurring_coauthor(co_name, publications)

                await db.execute(text("""
                    INSERT INTO publication_co_authors
                        (publication_id, co_author_name, author_position, is_recurring)
                    VALUES
                        (:pub_id, :co_author_name, :author_position, :is_recurring)
                """), {
                    "pub_id":         pub_id,
                    "co_author_name": co_name,
                    "author_position": _safe_int(co.get("author_position")) or position,
                    "is_recurring":   is_recurring,
                })

        await db.commit()

    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert publication records: {str(exc)}")

    # --- Insert coauthor_analysis ---
    try:
        if coauthor_data:
            recurring_json = json.dumps(coauthor_data.get("recurring_collaborators") or [], ensure_ascii=False)
            await db.execute(text("""
                INSERT INTO coauthor_analysis
                    (candidate_id, total_unique_coauthors, avg_coauthors_per_paper,
                     max_coauthors_in_paper, recurring_collaborators,
                     most_frequent_collaborator, collaboration_diversity_score,
                     has_student_collaborations, has_international_collaborations,
                     collaboration_summary)
                VALUES
                    (:candidate_id, :total_unique_coauthors, :avg_coauthors_per_paper,
                     :max_coauthors_in_paper, CAST(:recurring_collaborators AS jsonb),
                     :most_frequent_collaborator, :collaboration_diversity_score,
                     :has_student_collaborations, :has_international_collaborations,
                     :collaboration_summary)
            """), {
                "candidate_id":                  candidate_id,
                "total_unique_coauthors":         _safe_int(coauthor_data.get("total_unique_coauthors")),
                "avg_coauthors_per_paper":        _safe_float(coauthor_data.get("avg_coauthors_per_paper")),
                "max_coauthors_in_paper":         _safe_int(coauthor_data.get("max_coauthors_in_paper")),
                "recurring_collaborators":        recurring_json,
                "most_frequent_collaborator":     _safe_str(coauthor_data.get("most_frequent_collaborator"), 255),
                "collaboration_diversity_score":  _safe_float(coauthor_data.get("collaboration_diversity_score")),
                "has_student_collaborations":     _safe_bool(coauthor_data.get("has_student_collaborations")),
                "has_international_collaborations": _safe_bool(coauthor_data.get("has_international_collaborations")),
                "collaboration_summary":          _safe_str(coauthor_data.get("collaboration_summary")),
            })
            await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert coauthor_analysis: {str(exc)}")

    # --- Insert topic_variability ---
    try:
        if topic_data:
            clusters_json = json.dumps(topic_data.get("topic_clusters") or [], ensure_ascii=False)
            await db.execute(text("""
                INSERT INTO topic_variability
                    (candidate_id, dominant_topic, diversity_score,
                     topic_clusters, topic_trend, variability_summary)
                VALUES
                    (:candidate_id, :dominant_topic, :diversity_score,
                     CAST(:topic_clusters AS jsonb), :topic_trend, :variability_summary)
            """), {
                "candidate_id":      candidate_id,
                "dominant_topic":    _safe_str(topic_data.get("dominant_topic"), 255),
                "diversity_score":   _safe_float(topic_data.get("diversity_score")),
                "topic_clusters":    clusters_json,
                "topic_trend":       _safe_str(topic_data.get("topic_trend")),
                "variability_summary": _safe_str(topic_data.get("variability_summary")),
            })
            await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert topic_variability: {str(exc)}")

    # --- Cache the full analysis JSON on the candidate row ---
    try:
        await db.execute(text(
            "UPDATE candidates SET publication_analysis_json = :pub_json WHERE id = :cid"
        ), {
            "pub_json": json.dumps(analysis, ensure_ascii=False),
            "cid":      candidate_id,
        })
        await db.commit()
    except Exception:
        await db.rollback()
        # Non-fatal — data is already in the normalised tables

    return {
        "success": True,
        "candidate_id":     candidate_id,
        "publications_inserted": len(inserted_pub_ids),
        "analysis": analysis,
    }


# =============================================================================
# DEEP PUBLICATION ANALYSIS — GET (return cached result)
# =============================================================================

@router.get("/candidate/{candidate_id}/publications")
async def get_publication_analysis(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the cached deep publication analysis for a candidate.
    Also reads live data from the normalised tables for freshness.
    """
    row = await db.execute(
        text("SELECT id, full_name, publication_analysis_json FROM candidates WHERE id = :cid"),
        {"cid": candidate_id},
    )
    record = row.mappings().first()

    if not record:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    # Load the cached JSON result
    cached = _load_json_col(record["publication_analysis_json"])

    # Also pull live counts from normalised tables for the summary header
    pub_row = await db.execute(
        text("SELECT COUNT(*) AS cnt FROM publications WHERE candidate_id = :cid"),
        {"cid": candidate_id},
    )
    pub_count = pub_row.scalar() or 0

    coauthor_row = await db.execute(
        text("SELECT * FROM coauthor_analysis WHERE candidate_id = :cid LIMIT 1"),
        {"cid": candidate_id},
    )
    coauthor_record = coauthor_row.mappings().first()

    topic_row = await db.execute(
        text("SELECT * FROM topic_variability WHERE candidate_id = :cid LIMIT 1"),
        {"cid": candidate_id},
    )
    topic_record = topic_row.mappings().first()

    return {
        "candidate_id":       candidate_id,
        "full_name":          record["full_name"],
        "is_analysed":        cached is not None,
        "publications_count": pub_count,
        "coauthor_analysis":  dict(coauthor_record) if coauthor_record else None,
        "topic_variability":  dict(topic_record) if topic_record else None,
        "cached_analysis":    cached,
    }


# =============================================================================
# SAFE TYPE HELPERS
# =============================================================================

def _safe_str(value, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if not result:
        return None
    if max_len and len(result) > max_len:
        result = result[:max_len]
    return result


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value)


def _safe_authorship_role(pub: dict, all_pubs: list, candidate_name: str | None) -> str | None:
    """
    Determine authorship role from candidate_author_position.
    Returns a string value compatible with the authorship_role enum,
    or None if cannot be determined (NULL is safe — the column is nullable).
    """
    position = _safe_int(pub.get("candidate_author_position"))
    if position == 1:
        return "FIRST_AUTHOR"
    if position and position > 1:
        return "CO_AUTHOR"
    return None


def _is_recurring_coauthor(co_name: str, all_pubs: list) -> bool:
    """Check if this co-author appears in more than one publication."""
    count = 0
    co_name_lower = co_name.lower()
    for pub in all_pubs:
        co_list = pub.get("co_authors") or []
        for co in co_list:
            if isinstance(co, dict):
                name = (co.get("co_author_name") or "").lower()
                if name and co_name_lower in name or name in co_name_lower:
                    count += 1
                    break
    return count > 1
