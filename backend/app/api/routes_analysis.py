from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.candidate import Candidate
from backend.app.schemas.analysis_schema import AnalysisResponse
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.email_service import EmailService


router = APIRouter()


@router.get("/summary/{candidate_id}", response_model=AnalysisResponse)
def get_summary(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    result = AnalysisService().generate_placeholder_summary(candidate)
    return AnalysisResponse(candidate_id=candidate_id, message=result["summary"], status=result["status"])


@router.get("/email-draft/{candidate_id}")
def get_email_draft(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    draft = EmailService().draft_missing_info_email(candidate)
    return {"candidate_id": candidate_id, "draft": draft}

