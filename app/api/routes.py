"""REST API routes for the parser backend and exploration orchestrator."""
from __future__ import annotations

import logging
from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from app.services import SessionService
from app.services.exploration_service import ExplorationService
from app.models.exploration_session import SessionStatus

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.route("/health", methods=["GET"], strict_slashes=False)
def health() -> tuple[Response, int]:
    settings = current_app.config["SETTINGS"]
    return (
        jsonify(
            {
                "status": "ok",
                "environment": settings.env,
                "queue": settings.queue.broker_url,
            }
        ),
        200,
    )


# Original data extraction session routes
@api_bp.route("/sessions", methods=["POST"], strict_slashes=False)
def create_session() -> tuple[Response, int]:
    payload = request.get_json(silent=True) or {}
    url = payload.get("url")
    if not url:
        raise BadRequest("'url' is a required field")

    if payload.get("metadata") is not None and not isinstance(payload["metadata"], dict):
        raise BadRequest("'metadata' must be an object when provided")

    instructions = payload.get("instructions")
    if instructions is not None and not isinstance(instructions, str):
        raise BadRequest("'instructions' must be a string when provided")

    metadata = payload.get("metadata") or {}

    service = SessionService.from_app(current_app)
    session = service.create_session(url=url, instructions=instructions, metadata=metadata)
    return jsonify(session), 202


@api_bp.route("/sessions/<session_id>", methods=["GET"], strict_slashes=False)
def get_session(session_id: str) -> tuple[Response, int]:
    service = SessionService.from_app(current_app)
    session = service.get_session(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
    return jsonify(session), 200


# New exploration orchestrator routes
@api_bp.route("/exploration/sessions", methods=["POST"], strict_slashes=False)
def create_exploration_session() -> tuple[Response, int]:
    """Create a new exploration session."""
    payload = request.get_json(silent=True) or {}
    url = payload.get("url")
    objectives = payload.get("objectives")
    
    if not url:
        raise BadRequest("'url' is a required field")
    if not objectives:
        raise BadRequest("'objectives' is a required field")
    
    if payload.get("metadata") is not None and not isinstance(payload["metadata"], dict):
        raise BadRequest("'metadata' must be an object when provided")
        
    metadata = payload.get("metadata") or {}
    
    # Get exploration service
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    # Create exploration session
    session = exploration_service.create_exploration_session(url, objectives, metadata)
    
    return jsonify(session), 201


@api_bp.route("/exploration/sessions/<session_id>", methods=["GET"], strict_slashes=False)
def get_exploration_session(session_id: str) -> tuple[Response, int]:
    """Get the status of an exploration session."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    status = exploration_service.get_session_status(session_id)
    if not status:
        return jsonify({"error": "exploration session not found"}), 404
        
    return jsonify(status), 200


@api_bp.route("/exploration/sessions/<session_id>/start", methods=["POST"], strict_slashes=False)
def start_exploration(session_id: str) -> tuple[Response, int]:
    """Start an exploration for a session."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.start_exploration(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result), 202


@api_bp.route("/exploration/sessions/<session_id>/pause", methods=["POST"], strict_slashes=False)
def pause_exploration(session_id: str) -> tuple[Response, int]:
    """Pause a running exploration."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.pause_exploration(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result), 200


@api_bp.route("/exploration/sessions/<session_id>/resume", methods=["POST"], strict_slashes=False)
def resume_exploration(session_id: str) -> tuple[Response, int]:
    """Resume a paused exploration."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.resume_exploration(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result), 202


@api_bp.route("/exploration/sessions/<session_id>/stop", methods=["POST"], strict_slashes=False)
def stop_exploration(session_id: str) -> tuple[Response, int]:
    """Stop an exploration."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.stop_exploration(session_id)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result), 200


@api_bp.route("/exploration/sessions/<session_id>/chat", methods=["POST"], strict_slashes=False)
def send_chat_message(session_id: str) -> tuple[Response, int]:
    """Send a chat message to an exploration session."""
    payload = request.get_json(silent=True) or {}
    message = payload.get("message")
    message_type = payload.get("type", "user")
    
    if not message:
        raise BadRequest("'message' is a required field")
    
    if message_type not in ["user", "system", "agent"]:
        raise BadRequest("'type' must be 'user', 'system', or 'agent'")
    
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.send_chat_message(session_id, message, message_type)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify(result), 200


@api_bp.route("/exploration/sessions/<session_id>/chat", methods=["GET"], strict_slashes=False)
def get_chat_messages(session_id: str) -> tuple[Response, int]:
    """Get chat messages for a session."""
    limit = request.args.get("limit", default=50, type=int)
    
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    messages = exploration_service.get_chat_messages(session_id, limit)
    
    return jsonify({"session_id": session_id, "messages": messages, "count": len(messages)}), 200


@api_bp.route("/exploration/sessions", methods=["GET"], strict_slashes=False)
def list_exploration_sessions() -> tuple[Response, int]:
    """List all exploration sessions."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    sessions = exploration_service.list_sessions()
    
    return jsonify({"sessions": sessions, "count": len(sessions)}), 200


@api_bp.route("/exploration/sessions/<session_id>", methods=["DELETE"], strict_slashes=False)
def delete_exploration_session(session_id: str) -> tuple[Response, int]:
    """Delete an exploration session."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    result = exploration_service.delete_session(session_id)
    
    if not result:
        return jsonify({"error": "exploration session not found"}), 404
    
    return jsonify({"success": True, "message": "Exploration session deleted"}), 200


@api_bp.route("/exploration/sessions/<session_id>/actions", methods=["GET"], strict_slashes=False)
def get_session_actions(session_id: str) -> tuple[Response, int]:
    """Get action logs for a session."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    status = exploration_service.get_session_status(session_id)
    if not status:
        return jsonify({"error": "exploration session not found"}), 404
    
    # Extract action logs from session data
    session_data = status.get("session", {})
    action_logs = session_data.get("action_logs", [])
    
    return jsonify({
        "session_id": session_id,
        "action_logs": action_logs,
        "count": len(action_logs)
    }), 200


@api_bp.route("/exploration/sessions/<session_id>/screenshots", methods=["GET"], strict_slashes=False)
def get_session_screenshots(session_id: str) -> tuple[Response, int]:
    """Get screenshots for a session."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    status = exploration_service.get_session_status(session_id)
    if not status:
        return jsonify({"error": "exploration session not found"}), 404
    
    # Extract screenshots from session data
    session_data = status.get("session", {})
    screenshots = session_data.get("screenshots", [])
    
    return jsonify({
        "session_id": session_id,
        "screenshots": screenshots,
        "count": len(screenshots)
    }), 200


@api_bp.route("/exploration/status", methods=["GET"], strict_slashes=False)
def get_exploration_system_status() -> tuple[Response, int]:
    """Get overall exploration system status."""
    settings = current_app.config["SETTINGS"]
    exploration_service = ExplorationService.from_app_settings(settings, current_app.logger)
    
    sessions = exploration_service.list_sessions()
    
    # Count sessions by status
    status_counts = {}
    for session in sessions:
        status = session.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return jsonify({
        "system_status": "operational",
        "total_sessions": len(sessions),
        "status_breakdown": status_counts,
        "capabilities": [
            "multi_agent_exploration",
            "screenshot_capture",
            "dom_analysis", 
            "chat_orchestration",
            "structured_logging"
        ]
    }), 200