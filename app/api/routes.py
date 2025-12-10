"""REST API routes for the parser backend."""
from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from app.services import SessionService

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
