from backend.app.models.candidate import Candidate


class AnalysisService:
    def generate_placeholder_summary(self, candidate: Candidate) -> dict:
        return {
            "candidate_id": candidate.id,
            "summary": "Milestone 1 placeholder: detailed analysis modules are planned for Milestone 2.",
            "status": "pending_m2",
        }

