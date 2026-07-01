import uuid
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from signals import get_llm_score, get_stylometric_score, compute_confidence, get_label
from audit_log import add_entry, get_log

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    if not data or "text" not in data or "creator_id" not in data:
        return jsonify({"error": "text and creator_id are required"}), 400

    text = data["text"]
    creator_id = data["creator_id"]

    content_id = str(uuid.uuid4())

    llm_score = get_llm_score(text)
    stylometric_score = get_stylometric_score(text)
    confidence = compute_confidence(llm_score, stylometric_score)

    # Label still placeholder — comes in Milestone 5
    label = get_label(confidence)

    entry = add_entry({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": "likely_ai" if confidence >= 0.5 else "likely_human",
        "confidence": confidence,
        "llm_score": llm_score,
        "stylometric_score": stylometric_score,
        "label": label,
        "status": "classified",
    })

    return jsonify({
        "content_id": content_id,
        "attribution": entry["attribution"],
        "confidence": confidence,
        "label": label,
    })

@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()})
from audit_log import add_entry, get_log, find_entry, update_entry

@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json()

    if not data or "content_id" not in data or "creator_reasoning" not in data:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    content_id = data["content_id"]
    creator_reasoning = data["creator_reasoning"]

    original_entry = find_entry(content_id)
    if original_entry is None:
        return jsonify({"error": "content_id not found"}), 404

    update_entry(content_id, {
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
    })

    add_entry({
        "content_id": content_id,
        "creator_id": original_entry.get("creator_id"),
        "event": "appeal_submitted",
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
    })

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Appeal received and logged for review.",
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)