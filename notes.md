User submits text + creator_id to POST /submit.
Text is sent to Signal 1 (your first detector), which returns a score.
Text is sent to Signal 2 (your second detector), which returns a score.
Both scores are combined into one confidence score.
Confidence score is mapped to a label ("Likely AI," "Uncertain," "Likely human").
The submission, scores, and label get written to the audit log.
The response (content_id, attribution, confidence, label) is returned to the user.



Then do the same for appeals: POST /appeal → look up content_id → status changes to "under_review" → appeal reasoning + status logged → confirmation returned.
This becomes your "architecture narrative" — you'll reuse it almost verbatim in planning.md later.