# =============================================================================
# TALASH - LLM Connection Test (Groq)
# test_llm.py
#
# Run from backend/ folder:
#   python test_llm.py
# =============================================================================

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.llm_client import ask_llm, ask_llm_text, check_groq_health


# =============================================================================
# TEST 1 — Health check
# =============================================================================

async def test_health():
    print("\n--- TEST 1: Groq Health Check ---")
    result = await check_groq_health()
    print(result)
    return result["status"] == "ok"


# =============================================================================
# TEST 2 — JSON extraction
# =============================================================================

async def test_json_extraction():
    print("\n--- TEST 2: JSON Extraction ---")

    system_prompt = """
You are a CV parser. Extract information and return ONLY valid JSON.
No explanation, no markdown, no extra text. Just the JSON object.
"""

    user_prompt = """
Extract the name and email from this text:

"My name is Dr. Ahmed Khan and you can reach me at ahmed.khan@uet.edu.pk"

Return exactly this structure:
{
  "name": "",
  "email": ""
}
"""

    result = await ask_llm(system_prompt, user_prompt)
    print("Extracted JSON:", result)
    return True


# =============================================================================
# TEST 3 — Plain text output
# =============================================================================

async def test_text_output():
    print("\n--- TEST 3: Plain Text Summary ---")

    system_prompt = "You are an HR assistant. Write brief professional summaries."
    user_prompt   = "Write one sentence about a candidate with a PhD in CS from NUST with 10 publications."

    result = await ask_llm_text(system_prompt, user_prompt)
    print("Summary:", result)
    return True


# =============================================================================
# RUN ALL TESTS
# =============================================================================

async def main():
    print("=" * 50)
    print("TALASH - Groq LLM Connection Test")
    print("=" * 50)

    try:
        health_ok = await test_health()
        if not health_ok:
            print("\nGroq is not reachable.")
            print("Check your GROQ_API_KEY in .env")
            return

        await test_json_extraction()
        await test_text_output()

        print("\n" + "=" * 50)
        print("All tests passed! LLM is ready.")
        print("=" * 50)

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())