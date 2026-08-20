import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

# Look for your custom OpenRouter key instead of the OpenAI key
openrouter_key = os.getenv("OPENROUTER_API_KEY")

# Add a safety fallback so your server doesn't crash if the key is missing
if not openrouter_key:
    print("❌ CONFIG WARNING: 'OPENROUTER_API_KEY' is missing from your .env file!")
    openrouter_key = "MISSING_KEY"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,  # Uses your OpenRouter token safely
)

# Pull the model name from your .env file, or use "openrouter/free" as a backup
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")


def generate_answer(
    system_prompt: str,
    user_prompt: str,
    history: list[dict[str, str]] | None = None,
) -> str:

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    if history:
        messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": user_prompt,
        }
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=4000,
        tools=[
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": "auto",
                    "max_results": 8,
                    "search_context_size": "high",
                },
            },
            {
                "type": "openrouter:web_fetch",
            },
        ],
    )

    return response.choices[0].message.content or ""
