import json
import re

from backend.app.core.config import settings
from backend.app.core.prompts import CV_EXTRACTION_PROMPT


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.max_json_retries = max(1, settings.LLM_MAX_JSON_RETRIES)

    def parse_cv_text(self, cv_text: str) -> dict:
        if not cv_text.strip():
            return self._empty_payload()

        if self.api_key:
            try:
                return self._call_groq_with_retries(cv_text)
            except Exception:
                return self._heuristic_parse(cv_text)

        return self._heuristic_parse(cv_text)

    def _call_groq_with_retries(self, cv_text: str) -> dict:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        user_content = cv_text[:120000]
        parse_error = ""
        last_raw = ""

        for attempt in range(1, self.max_json_retries + 1):
            if attempt == 1:
                prompt = user_content
            else:
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Return STRICT JSON only and ensure it matches the schema.\n\n"
                    f"Previous parse error: {parse_error}\n\n"
                    f"Previous response:\n{last_raw}\n\n"
                    "Now regenerate only valid JSON for this CV:\n"
                    f"{user_content}"
                )

            response = client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": CV_EXTRACTION_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            last_raw = raw

            try:
                return self._load_json(raw)
            except Exception as exc:
                parse_error = str(exc)

        # Raise after retries so caller can gracefully use fallback parser.
        raise ValueError(f"Invalid JSON after {self.max_json_retries} attempts. Last error: {parse_error}")

    def _load_json(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw).strip()
            raw = raw[:-3].strip() if raw.endswith("```") else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                raise
            return json.loads(match.group(0))

    def _heuristic_parse(self, cv_text: str) -> dict:
        lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
        first = lines[0] if lines else ""

        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cv_text)
        phone_match = re.search(r"(\+?\d[\d\s\-]{7,}\d)", cv_text)

        return {
            "personal_info": {
                "full_name": first if len(first.split()) <= 6 else "",
                "email": email_match.group(0) if email_match else "",
                "phone": phone_match.group(0) if phone_match else "",
                "location": "",
                "linkedin": "",
                "google_scholar": "",
            },
            "education": [],
            "experience": [],
            "skills": self._extract_skills_heuristic(cv_text),
            "publications": [],
            "patents": [],
            "books": [],
            "meta": {
                "parser": "heuristic_fallback",
                "note": "Set GROQ_API_KEY to enable full LLM extraction.",
            },
        }

    def _extract_skills_heuristic(self, cv_text: str) -> list[str]:
        skill_candidates = [
            "Python",
            "Java",
            "C++",
            "SQL",
            "Machine Learning",
            "Deep Learning",
            "NLP",
            "TensorFlow",
            "PyTorch",
            "FastAPI",
            "React",
        ]
        lower = cv_text.lower()
        return [s for s in skill_candidates if s.lower() in lower]

    def _empty_payload(self) -> dict:
        return {
            "personal_info": {
                "full_name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin": "",
                "google_scholar": "",
            },
            "education": [],
            "experience": [],
            "skills": [],
            "publications": [],
            "patents": [],
            "books": [],
        }

