# TALASH Prompt Design (Milestone 1)

## Extraction Prompt Objective

The CV extraction prompt is designed to convert unstructured CV text into strict JSON with the fields required by the project rubric:

- personal_info
- education
- experience
- skills
- publications
- patents
- books

## Prompt Design Rules Used

1. Explicit schema definition to reduce hallucinations.
2. "JSON only" response rule to simplify backend parsing.
3. Fallback behavior for missing information (empty values/lists).
4. Faithfulness instruction to avoid fabricating CV details.

## Prompt Location in Code

- `backend/app/core/prompts.py`

## LLM Fallback Behavior

If Groq API key is unavailable, API fails, or the model returns invalid JSON after configured retries, the system runs a heuristic parser that extracts basic personal info and common skills. This guarantees a working demo during class even without external API connectivity.
