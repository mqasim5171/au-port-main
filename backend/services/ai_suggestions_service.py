import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_ai_suggestions(context: dict) -> list[str]:
    """
    Uses LLM to generate intelligent QA suggestions
    """

    if not OPENROUTER_API_KEY:
        return ["AI suggestions not available (missing API key)"]

    prompt = f"""
You are an academic quality assurance expert.

Analyze the following course QA data and give clear, actionable suggestions.

DATA:
{context}

RULES:
- Be specific (mention weeks, CLOs, assessments)
- Be concise (max 4 suggestions)
- Use professional tone
"""

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )

        data = res.json()
        text = data["choices"][0]["message"]["content"]

        return [line.strip("- ").strip() for line in text.split("\n") if line.strip()]

    except Exception as e:
        return [f"AI suggestion generation failed: {str(e)}"]