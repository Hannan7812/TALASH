from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    candidate_id: int


class AnalysisResponse(BaseModel):
    candidate_id: int
    message: str
    status: str
