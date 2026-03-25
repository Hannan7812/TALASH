CV_EXTRACTION_PROMPT = """
You are an expert academic and professional CV parser.

Task:
Extract the candidate data from the provided CV text and return STRICT JSON only.

Output JSON schema:
{
  "personal_info": {
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "google_scholar": ""
  },
  "education": [
    {
      "degree": "",
      "institution": "",
      "year_start": "",
      "year_end": "",
      "cgpa_or_score": ""
    }
  ],
  "experience": [
    {
      "role": "",
      "organization": "",
      "start_date": "",
      "end_date": "",
      "details": ""
    }
  ],
  "skills": [""],
  "publications": [
    {
      "title": "",
      "venue": "",
      "year": "",
      "authors": []
    }
  ],
  "patents": [
    {
      "title": "",
      "year": "",
      "status": ""
    }
  ],
  "books": [
    {
      "title": "",
      "year": "",
      "publisher": ""
    }
  ]
}

Rules:
1) Return valid JSON only. No markdown, no comments.
2) Use empty string, empty list, or null-like omission behavior conservatively when unknown.
3) Keep extracted facts faithful to the source CV text.
""".strip()


SKILLS_ENRICHMENT_PROMPT = """
You are an expert CV skill extractor.

Task:
You will receive structured candidate JSON that was extracted earlier from a CV.
If the skills list is empty, infer and populate only relevant professional/technical/academic skills
using the provided structured data and source CV text snippet.

Output JSON schema:
{
  "skills": [""]
}

Rules:
1) Return valid JSON only. No markdown, no comments.
2) Include only relevant skills strongly supported by the input.
3) Deduplicate skills and keep concise canonical names.
4) If no reliable skills can be inferred, return an empty list.
""".strip()
