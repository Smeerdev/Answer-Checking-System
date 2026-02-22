"""
Flask API for MCQ Answer Sheet Checking (web deployment).
"""
import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# Load model: prefer project root (parent of webapp/), then current dir (e.g. when Render uses Root Directory = webapp)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "cnn_model.h5")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cnn_model.h5")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# Import after setting path so get_model finds cnn_model.h5
from grading_logic import (
    get_model,
    generate_model_metadata_from_path,
    grade_student_images,
    results_to_csv,
)


@app.route("/")
def index():
    return send_file(os.path.join(app.static_folder, "index.html"))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model_loaded": os.path.exists(MODEL_PATH)})


@app.route("/api/metadata", methods=["POST"])
def generate_metadata():
    """Upload model answer image; returns metadata JSON."""
    if "model_answer" not in request.files:
        return jsonify({"error": "Missing file: model_answer"}), 400
    file = request.files["model_answer"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return jsonify({"error": "File must be PNG or JPG"}), 400
    if not os.path.exists(MODEL_PATH):
        return jsonify({"error": "Server missing cnn_model.h5"}), 503
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            model = get_model(MODEL_PATH)
            metadata = generate_model_metadata_from_path(tmp.name, model)
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/grade", methods=["POST"])
def grade():
    """
    Grade student sheets.
    Form: metadata (JSON string), sheet files (multiple, key "sheets" or "sheets[]").
    Query: format=csv to download CSV instead of JSON.
    """
    metadata_str = request.form.get("metadata")
    if not metadata_str:
        return jsonify({"error": "Missing form field: metadata (JSON string)"}), 400
    try:
        metadata = json.loads(metadata_str)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid metadata JSON: {e}"}), 400
    # Collect all uploaded sheet files
    sheets = request.files.getlist("sheets") or request.files.getlist("sheets[]")
    if not sheets:
        return jsonify({"error": "No sheet files uploaded (use key 'sheets')"}), 400
    if not os.path.exists(MODEL_PATH):
        return jsonify({"error": "Server missing cnn_model.h5"}), 503
    tmp_paths = []
    try:
        for f in sheets:
            if f.filename == "":
                continue
            if not f.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1])
            f.save(tmp.name)
            tmp_paths.append(tmp.name)
        if not tmp_paths:
            return jsonify({"error": "No valid image files (PNG/JPG)"}), 400
        model = get_model(MODEL_PATH)
        results = grade_student_images(tmp_paths, metadata, model)
    finally:
        for p in tmp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass
    if request.args.get("format") == "csv":
        csv_str = results_to_csv(results)
        from io import BytesIO
        buf = BytesIO(csv_str.encode("utf-8"))
        return send_file(
            buf,
            mimetype="text/csv",
            as_attachment=True,
            download_name="grades.csv",
        )
    return jsonify({"results": results})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
