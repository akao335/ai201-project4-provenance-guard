import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_llm_score(text: str) -> float:
    """
    Sends text to Groq and asks it to assess likelihood of AI authorship.
    Returns a float between 0.0 (likely human) and 1.0 (likely AI).
    """
    prompt = f"""You are an expert at detecting AI-generated text. Analyze the text below
for specific indicators of AI authorship, such as:
- Generic transition phrases ("Furthermore," "It is important to note," "In conclusion")
- Overly balanced, hedge-everything structure ("On one hand... on the other hand...")
- Unnaturally uniform sentence lengths and rhythm
- Vague, abstract language rather than concrete specific detail
- Lack of typos, slang, contractions, or personal voice

Also consider indicators of human authorship:
- Casual tone, contractions, slang, or informal punctuation
- Specific, idiosyncratic personal details
- Irregular sentence lengths and natural imperfections

Text to analyze:
\"\"\"{text}\"\"\"

First, briefly reason through which indicators apply (2-3 sentences).
Then, on the FINAL line of your response, output ONLY a JSON object in this exact format:
{{"ai_probability": 0.0}}

The ai_probability must be a float between 0.0 (clearly human-written) and 1.0 (clearly AI-generated).
Use the full range — most text is not at the extremes, and you should differentiate confidently
based on the indicators above rather than defaulting to a middle or low value.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()

    last_line = raw.strip().splitlines()[-1].strip()

    try:
        parsed = json.loads(last_line)
        score = float(parsed["ai_probability"])
        return max(0.0, min(1.0, score))
    except (json.JSONDecodeError, KeyError, ValueError, IndexError):
        print(f"Warning: could not parse LLM response: {raw}")
        return 0.5