# Provenance Guard — Planning Document

## 1. Detection Signals

This system uses two signals with different strengths and different blind spots, combined into a single confidence score.

**Signal 1: LLM-as-judge (Groq)**
- What it measures: Sends the submitted text to an LLM with a structured prompt asking it to assess the likelihood the text is AI-generated, based on patterns of phrasing, coherence, and stylistic tells the model has learned to associate with AI writing.
- Output format: A float between 0.0 and 1.0 (`llm_score`), where 1.0 = very likely AI-generated.
- Why it differs between human/AI text: LLMs are good at detecting their own characteristic patterns — hedging language, overly balanced "on one hand / on the other hand" structures, generic transitions ("Furthermore," "It is important to note").
- Blind spot: Can be fooled by AI text that has been lightly edited by a human, and can misjudge formal, structured human writing (e.g. academic writing, non-native English speakers) as AI-generated, since both share low stylistic variance.

**Signal 2: Stylometric heuristics (rule-based)**
- What it measures: Computes two statistical properties of the text:
  - Sentence-length variance (AI text tends to have more uniform sentence lengths)
  - Type-token ratio (vocabulary diversity — unique words / total words; AI text tends to reuse a narrower vocabulary)
- Output format: Each metric normalized to 0.0–1.0, then averaged into a single `stylometric_score` between 0.0 and 1.0, where 1.0 = more "AI-like" (low variance, low diversity).
- Why it differs between human/AI text: Human writing naturally varies more in rhythm and word choice; AI writing tends toward consistency and statistically "average" phrasing.
- Blind spot: A human writer with a deliberately repetitive or minimalist style (e.g. a poem, a terse texting style) will score high on this signal despite being human-written.

**Combining into a confidence score:**
confidence = (0.6 * llm_score) + (0.4 * stylometric_score)
The LLM judge is weighted higher because it captures semantic patterns the stylometric signal can't see, but the stylometric signal acts as a check against cases where the LLM judge is overconfident.

## 2. Uncertainty Representation

A confidence score is a float from 0.0 (very likely human) to 1.0 (very likely AI). It is **not** a probability in the statistical sense — it's a weighted heuristic combination, and the system communicates it as such rather than implying mathematical certainty.

**Thresholds:**
- `confidence >= 0.75` → "Likely AI-generated"
- `0.40 <= confidence < 0.75` → "Uncertain"
- `confidence < 0.40` → "Likely human-written"

A score of 0.6, for example, falls in the "Uncertain" band — the system does not claim to know, and the label reflects that hedging rather than rounding up to "likely AI."

## 3. Transparency Label Design

- **High-confidence AI** (`confidence >= 0.75`):
  > "This content shows strong patterns consistent with AI-generated text. Confidence: {confidence}. If you believe this is incorrect, you can appeal this classification."

- **Uncertain** (`0.40 <= confidence < 0.75`):
  > "This content shows mixed signals — some patterns common in both AI-generated and human-written text. We can't confidently classify this submission. Confidence: {confidence}."

- **High-confidence human** (`confidence < 0.40`):
  > "This content shows patterns consistent with human-written text. Confidence: {confidence}."

All three labels include the numeric confidence score so users can see the underlying basis for the label, not just the category.

## 4. Appeals Workflow

- **Who can appeal:** Any creator whose content has received a label (the `creator_id` who submitted it).
- **What they provide:** `content_id` (from the original `/submit` response) and `creator_reasoning` (free-text explanation of why they believe the classification is wrong).
- **What the system does on receipt:**
  1. Looks up the submission by `content_id`.
  2. Updates its status from `classified` to `under_review`.
  3. Logs the appeal as a new audit log entry, including the original classification data, the `creator_reasoning`, and the status change.
  4. Returns a confirmation response with the `content_id` and new status.
- **No automated re-classification** happens — this system flags it for human review only.
- **What a human reviewer would see in the appeal queue:** content_id, original text, original signal scores and confidence, the label that was shown, the creator's reasoning, and timestamp of both the original submission and the appeal.

## 5. Anticipated Edge Cases

1. **Non-native English speaker writing formally.** Formal sentence structure and careful word choice can score high on both the LLM judge (sounds "textbook-like") and the stylometric signal (lower variance than casual writing), pushing a human-written submission into "Uncertain" or even "Likely AI."
2. **Poetry or minimalist prose with intentional repetition.** A poem using repeated phrases or simple vocabulary for effect will score high on the stylometric signal (low type-token ratio, low sentence variance) despite being clearly human-authored and creative.

## Architecture
POST /submit
│
▼
[Signal 1: LLM judge (Groq)] ──llm_score──┐
│                                       ▼
[Signal 2: Stylometric heuristics] ─stylometric_score─► [Combine: 0.6llm + 0.4stylometric → confidence]
│
▼
[Map confidence → label]
│
▼
[Write entry to audit log] ──► [Response: content_id, attribution, confidence, label]
POST /appeal
│
▼
[Look up content_id] → [Set status = under_review] → [Log appeal + creator_reasoning] → [Response: confirmation, new status]

**Submission flow narrative:** A submitted text is run through both detection signals independently; their outputs are combined into a single weighted confidence score, which is mapped to one of three transparency labels and recorded in the audit log alongside both individual signal scores before being returned to the user.

**Appeal flow narrative:** A creator submits a content_id and their reasoning; the system updates that submission's status to under_review, appends the appeal and reasoning to the audit log next to the original classification, and confirms receipt — no automatic re-scoring occurs.

## AI Tool Plan

**Milestone 3 (submission endpoint + first signal):**
- Spec sections provided to AI tool: Detection Signals (Signal 1 description) + Architecture diagram.
- What I'll ask for: A Flask app skeleton with a `POST /submit` route stub, and a standalone `get_llm_score(text)` function that calls the Groq API and returns a float 0.0–1.0.
- Verification: Call `get_llm_score()` directly with 2-3 sample texts (one clearly AI, one clearly human) before wiring it into the endpoint. Confirm output is a float in range, not a string or unbounded number.

**Milestone 4 (second signal + confidence scoring):**
- Spec sections provided: Detection Signals (Signal 2 description) + Uncertainty Representation + Architecture diagram.
- What I'll ask for: A `get_stylometric_score(text)` function implementing sentence-length variance + type-token ratio, and a `compute_confidence(llm_score, stylometric_score)` function implementing the 0.6/0.4 weighted combination.
- Verification: Run both functions on the 4 test inputs from Milestone 4 instructions; confirm the weighting matches 0.6/0.4 exactly (print intermediate values) and that scores vary meaningfully between clearly-AI and clearly-human text.

**Milestone 5 (production layer):**
- Spec sections provided: Transparency Label Design + Appeals Workflow + Architecture diagram.
- What I'll ask for: A `get_label(confidence)` function returning the exact three label strings at the thresholds defined above, and a `POST /appeal` endpoint implementing the workflow described above.
- Verification: Call `get_label()` with values like 0.2, 0.5, 0.9 and confirm exact wording matches planning.md. Test `/appeal` with a real content_id from a prior `/submit` call and confirm via `/log` that status shows `under_review` and `creator_reasoning` is populated.