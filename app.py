import uuid
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from signals import get_llm_score
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

    # Placeholders for now — real values come in Milestone 4/5
    confidence = llm_score
    label = "placeholder"

    entry = add_entry({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": "likely_ai" if llm_score >= 0.5 else "likely_human",
        "confidence": confidence,
        "llm_score": llm_score,
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)