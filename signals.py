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
    
import statistics
import re
def get_stylometric_score(text: str) -> float:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]

    words = re.findall(r"\b[a-zA-Z']+\b", text.lower())

    if len(sentences) < 2 or len(words) < 5:
        return 0.5

    sentence_lengths = [len(re.findall(r"\b[a-zA-Z']+\b", s)) for s in sentences]
    length_stdev = statistics.pstdev(sentence_lengths)
    mean_length = statistics.mean(sentence_lengths) or 1

    coeff_of_variation = length_stdev / mean_length
    variance_score = max(0.0, min(1.0, 1 - (coeff_of_variation / 0.6)))
    unique_words = set(words)
    ttr = len(unique_words) / len(words)

    # Recalibrated for short texts (40-60 words), where TTR naturally sits in ~0.75-0.95
    # Lower end of that range (more word repetition) -> more AI-like
    ttr_score = max(0.0, min(1.0, 1 - ((ttr - 0.75) / 0.20)))
   

    stylometric_score = (variance_score + ttr_score) / 2
    return round(stylometric_score, 3)

def compute_confidence(llm_score: float, stylometric_score: float) -> float:
    """
    Combines the LLM judge score and stylometric score into a single
    confidence value using a weighted average, per planning.md:
    0.6 * llm_score + 0.4 * stylometric_score
    """
    confidence = (0.6 * llm_score) + (0.4 * stylometric_score)
    return round(max(0.0, min(1.0, confidence)), 3)

def get_label(confidence: float) -> str:
    """
    Maps a confidence score to one of three transparency label variants,
    per planning.md thresholds:
    - >= 0.75: Likely AI-generated
    - 0.40 - 0.75: Uncertain
    - < 0.40: Likely human-written
    """
    if confidence >= 0.75:
        return (
            f"This content shows strong patterns consistent with AI-generated text. "
            f"Confidence: {confidence}. If you believe this is incorrect, you can appeal this classification."
        )
    elif confidence >= 0.40:
        return (
            f"This content shows mixed signals — some patterns common in both AI-generated "
            f"and human-written text. We can't confidently classify this submission. Confidence: {confidence}."
        )
    else:
        return (
            f"This content shows patterns consistent with human-written text. Confidence: {confidence}."
        )