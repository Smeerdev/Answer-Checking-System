"""
Shared grading logic for MCQ Answer Sheet Checking (no GUI dependency).
Used by both the desktop app and the web API.
"""
import os
import json
import csv
import io
import cv2
import numpy as np

# Lazy-load model to avoid import-time TensorFlow when not needed
_cnn_model = None
CLASS_LABELS = ["confirmed", "crossedout", "empty"]

# Question option coordinates (same as main.py)
QUESTION_METADATA = [
    {"options": [(209, 720, 63, 45), (550, 719, 63, 45), (929, 718, 62, 44)]},
    {"options": [(209, 1235, 63, 44), (548, 1237, 64, 44), (929, 1235, 62, 45)]},
    {"options": [(209, 1490, 63, 44), (550, 1490, 63, 45), (929, 1490, 63, 45)]},
    {"options": [(209, 1870, 63, 44), (548, 1869, 63, 45), (929, 1870, 63, 45)]},
]


def get_model(model_path="cnn_model.h5"):
    """Load CNN model once and cache."""
    global _cnn_model
    if _cnn_model is None:
        import tensorflow as tf
        _cnn_model = tf.keras.models.load_model(model_path)
    return _cnn_model


def preprocess_image(image):
    """Preprocess an image for CNN prediction."""
    img_size = (128, 128)
    image = cv2.resize(image, img_size)
    image = image / 255.0
    return image.reshape(1, img_size[0], img_size[1], 3)


def classify_box(image, model):
    """Classify a single box using the CNN model."""
    import tensorflow as tf
    preprocessed = preprocess_image(image)
    prediction = model.predict(preprocessed)
    class_index = tf.argmax(prediction[0]).numpy()
    return CLASS_LABELS[class_index]


def generate_model_metadata_from_image(image, model):
    """Generate metadata dict from a model answer image (numpy array)."""
    if image is None or image.size == 0:
        raise ValueError("Image is empty or None.")
    metadata = {"questions": []}
    for question in QUESTION_METADATA:
        options = question["options"]
        question_data = {"options": options, "confirmed": None}
        for option in options:
            x, y, w, h = option
            box = image[y : y + h, x : x + w]
            prediction = classify_box(box, model)
            if prediction == "confirmed":
                question_data["confirmed"] = option
        if question_data["confirmed"] is None:
            question_data["confirmed"] = options[0]
        metadata["questions"].append(question_data)
    return metadata


def generate_model_metadata_from_path(image_path, model):
    """Generate metadata from model answer image file path."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to load image from {image_path}")
    return generate_model_metadata_from_image(image, model)


def grade_single_sheet(image_path, model_metadata, model):
    """Grade one student answer sheet. Returns (score, total, percentage)."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to load image from {image_path}")
    return grade_single_sheet_image(image, model_metadata, model)


def grade_single_sheet_image(image, model_metadata, model):
    """Grade one student sheet from image array. Returns (score, total, percentage)."""
    questions = model_metadata["questions"]
    model_confirmed = [q["confirmed"] for q in questions]
    score = 0
    for idx, question in enumerate(questions):
        options = question["options"]
        confirmed = None
        for option in options:
            x, y, w, h = option
            box = image[y : y + h, x : x + w]
            pred = classify_box(box, model)
            if pred == "confirmed":
                confirmed = option
                break
        if model_confirmed[idx] == confirmed:
            score += 1
    total = len(questions)
    pct = (score / total) * 100 if total else 0
    return score, total, round(pct, 2)


def grade_student_images(image_paths, model_metadata, model):
    """
    Grade multiple student sheets. Returns list of dicts:
    [{"filename": str, "score": int, "total": int, "percentage": float}, ...]
    """
    results = []
    for path in image_paths:
        name = os.path.basename(path)
        try:
            score, total, pct = grade_single_sheet(path, model_metadata, model)
            results.append({
                "filename": name,
                "score": score,
                "total": total,
                "percentage": pct,
            })
        except Exception as e:
            results.append({
                "filename": name,
                "error": str(e),
                "score": None,
                "total": None,
                "percentage": None,
            })
    return results


def results_to_csv(results):
    """Convert results list to CSV string."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Student", "Score", "Out of", "Percentage"])
    for r in results:
        if "error" in r:
            writer.writerow([r["filename"], "Error", "", r.get("error", "")])
        else:
            writer.writerow([r["filename"], r["score"], r["total"], r["percentage"]])
    return out.getvalue()
