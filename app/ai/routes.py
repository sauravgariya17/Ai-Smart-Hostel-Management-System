"""
app/ai/routes.py
--------------------
API endpoints for every Session 3 AI feature. Reuses the existing RBAC
decorators, validators, and models exactly as the rest of the app does.

    POST /api/ai/complaints/classify   -> AI Complaint Classification + Priority Prediction
    GET  /api/ai/rooms/recommend       -> Smart Room Recommendation
    GET  /api/ai/occupancy/forecast    -> Hostel Occupancy Prediction
    GET  /api/ai/fees/defaulters       -> Fee Defaulter Prediction
    POST /api/ai/chatbot/ask           -> AI Hostel Assistant / FAQ Chatbot
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required

from app.ai import ai_bp
from app.ai.services import complaint_classifier, room_recommender, occupancy_forecaster, fee_defaulter, chatbot
from app.utils.decorators import admin_or_warden_required, get_current_user_id
from app.utils.validators import validate_required_fields


@ai_bp.route("/complaints/classify", methods=["POST"])
@jwt_required()
def classify_complaint():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["title"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    result = complaint_classifier.classify_complaint(
        title=data.get("title", ""),
        description=data.get("description", ""),
    )
    return jsonify({"success": True, "prediction": result}), 200


@ai_bp.route("/rooms/recommend", methods=["GET"])
@jwt_required()
def recommend_rooms():
    preferences = {
        "hostel_id": request.args.get("hostel_id", type=int),
        "room_type": request.args.get("room_type"),
        "max_rent": request.args.get("max_rent", type=float),
        "preferred_floor": request.args.get("preferred_floor", type=int),
    }
    top_n = request.args.get("top_n", default=5, type=int)
    top_n = max(1, min(top_n, 20))

    result = room_recommender.recommend_rooms(preferences, top_n=top_n)
    return jsonify({"success": True, **result}), 200


@ai_bp.route("/occupancy/forecast", methods=["GET"])
@admin_or_warden_required
def forecast_occupancy():
    days = request.args.get("days", default=30, type=int)
    result = occupancy_forecaster.forecast_occupancy(days=days)
    return jsonify({"success": True, **result}), 200


@ai_bp.route("/fees/defaulters", methods=["GET"])
@admin_or_warden_required
def fee_defaulters():
    limit = request.args.get("limit", type=int)
    result = fee_defaulter.predict_defaulters(limit=limit)
    return jsonify({"success": True, **result}), 200


@ai_bp.route("/chatbot/ask", methods=["POST"])
@jwt_required()
def chatbot_ask():
    data = request.get_json(silent=True) or {}
    errors = validate_required_fields(data, ["question"])
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    result = chatbot.ask(question=data["question"], user_id=get_current_user_id())
    return jsonify({"success": True, **result}), 200
