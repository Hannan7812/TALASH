

import json
import re
import os
from pathlib import Path
from groq import AsyncGroq
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =============================================================================
# CONFIG — Primary client (CV parsing, education, experience, general)
# =============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set in your .env file.\n"
        "Get a free key at https://console.groq.com"
    )

# =============================================================================
# CONFIG — Publication client (dedicated second key for publication analysis)
# =============================================================================

GROQ_PUBLICATION_API_KEY = os.getenv("GROQ_PUBLICATION_API_KEY")
GROQ_PUBLICATION_MODEL   = os.getenv("GROQ_PUBLICATION_MODEL", "llama-3.3-70b-versatile")

# =============================================================================
# GROQ CLIENT INSTANCES
# =============================================================================

# Primary client — used for CV parsing, education, experience, general analysis
client = AsyncGroq(api_key=GROQ_API_KEY)

# Publication client — uses the second API key exclusively for deep publication analysis
# Falls back to primary client if second key is not configured
if GROQ_PUBLICATION_API_KEY:
    publication_client = AsyncGroq(api_key=GROQ_PUBLICATION_API_KEY)
else:
    publication_client = client
    GROQ_PUBLICATION_MODEL = GROQ_MODEL


# =============================================================================
# HELPER — Strip markdown fences from LLM response
# LLMs sometimes wrap JSON in ```json ... ``` even when told not to
# =============================================================================

def clean_llm_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# =============================================================================
# HELPER — Parse JSON safely
# =============================================================================

def parse_json_response(text: str) -> dict:
    cleaned = clean_llm_response(text)
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON response must be an object.")
        return parsed
    except json.JSONDecodeError:
        # Some model responses contain extra text or multiple JSON objects.
        # Recover by decoding the first JSON value from the first brace/bracket.
        first_object_start = min(
            [idx for idx in [cleaned.find("{"), cleaned.find("[")] if idx != -1],
            default=-1,
        )
        if first_object_start != -1:
            decoder = json.JSONDecoder()
            try:
                parsed, _ = decoder.raw_decode(cleaned[first_object_start:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"LLM returned invalid JSON.\n"
            f"Raw response (first 500 chars):\n{cleaned[:500]}"
        )


# =============================================================================
# CORE FUNCTION — Send prompt to PRIMARY client, get JSON back
# Used by CV parsing, education, experience, general analysis
# =============================================================================

async def ask_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 512
) -> dict:
    """
    Sends a prompt to Groq (primary key) and returns parsed JSON.
    """
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        raw_text = response.choices[0].message.content
        return parse_json_response(raw_text)

    except ValueError:
        raise

    except Exception as e:
        error_text = str(e)
        if "Request too large" in error_text or "rate_limit_exceeded" in error_text or "tokens per minute" in error_text:
            raise Exception(
                "Groq request exceeded token limits (TPM/context). "
                "Reduce input size, lower max_tokens, or use chunked analysis. "
                f"Original error: {error_text}"
            )
        raise Exception(
            f"Groq API call failed.\n"
            f"Error: {error_text}"
        )


# =============================================================================
# CORE FUNCTION — Send prompt to PRIMARY client, get plain text back
# =============================================================================

async def ask_llm_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.5,
    max_tokens: int = 512
) -> str:
    """
    Same as ask_llm() but returns plain text.
    Use for candidate summaries and email drafting.
    """
    try:
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        error_text = str(e)
        if "Request too large" in error_text or "rate_limit_exceeded" in error_text or "tokens per minute" in error_text:
            raise Exception(
                "Groq request exceeded token limits (TPM/context). "
                "Reduce input size, lower max_tokens, or use chunked analysis. "
                f"Original error: {error_text}"
            )
        raise Exception(
            f"Groq API call failed.\n"
            f"Error: {error_text}"
        )


# =============================================================================
# PUBLICATION FUNCTION — Send prompt to PUBLICATION client, get JSON back
# Uses the dedicated second Groq API key for deep publication analysis
# =============================================================================

async def ask_publication_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 6000
) -> dict:
    """
    Sends a prompt to Groq using the PUBLICATION API key and returns parsed JSON.
    This keeps publication analysis quota completely separate from general analysis.
    Uses a more capable model (llama-3.3-70b-versatile) for deeper understanding.
    """
    try:
        response = await publication_client.chat.completions.create(
            model=GROQ_PUBLICATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        raw_text = response.choices[0].message.content
        return parse_json_response(raw_text)

    except ValueError:
        raise

    except Exception as e:
        error_text = str(e)
        if "Request too large" in error_text or "rate_limit_exceeded" in error_text or "tokens per minute" in error_text:
            raise Exception(
                "Publication Groq request exceeded token limits. "
                "The publications section may be too long. "
                f"Original error: {error_text}"
            )
        raise Exception(
            f"Publication Groq API call failed.\n"
            f"Error: {error_text}"
        )


# =============================================================================
# HEALTH CHECK — Verify primary API key and connection
# =============================================================================

async def check_groq_health() -> dict:
    try:
        await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "Reply with just the word: ok"}],
            max_tokens=5
        )
        return {"groq": "connected", "model": GROQ_MODEL, "status": "ok"}
    except Exception as e:
        return {"groq": "unreachable", "model": GROQ_MODEL, "status": "error", "detail": str(e)}


# =============================================================================
# HEALTH CHECK — Verify publication API key and connection
# =============================================================================

async def check_publication_groq_health() -> dict:
    try:
        await publication_client.chat.completions.create(
            model=GROQ_PUBLICATION_MODEL,
            messages=[{"role": "user", "content": "Reply with just the word: ok"}],
            max_tokens=5
        )
        return {"groq": "connected", "model": GROQ_PUBLICATION_MODEL, "status": "ok", "purpose": "publication_analysis"}
    except Exception as e:
        return {"groq": "unreachable", "model": GROQ_PUBLICATION_MODEL, "status": "error", "detail": str(e)}