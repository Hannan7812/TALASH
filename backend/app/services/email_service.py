from backend.app.models.candidate import Candidate


class EmailService:
    def draft_missing_info_email(self, candidate: Candidate) -> str:
        name = candidate.full_name or "Candidate"
        return (
            f"Dear {name},\n\n"
            "Thank you for your application. We are currently reviewing your profile and need a few clarifications "
            "to complete your evaluation. Please share any missing academic details, employment dates, and publication metadata.\n\n"
            "Best regards,\nTALASH Recruitment Team"
        )

