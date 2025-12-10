"""Session service that mediates API requests and browser-use interactions."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:  # pragma: no cover - import guard makes code resilient when browser-use is optional.
    from browser_use import BrowserSession
except Exception:  # ImportError or runtime errors during optional dependency load
    BrowserSession = None  # type: ignore[assignment]

from flask import Flask

from app.agents import DataExtractionAgent
from app.config import AppSettings, BrowserUseSettings


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class _SessionStore:
    """Simple in-memory session registry for placeholder responses."""

    _sessions: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def save(cls, payload: Dict[str, Any]) -> None:
        with cls._lock:
            cls._sessions[payload["session_id"]] = payload

    @classmethod
    def get(cls, session_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            return cls._sessions.get(session_id)


class BrowserUseClient:
    """Lazily instantiates a BrowserSession based on configuration."""

    def __init__(self, settings: BrowserUseSettings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self._session: Optional[BrowserSession] = None

    def ensure_session(self) -> Optional[BrowserSession]:
        if BrowserSession is None:
            self.logger.debug("browser-use is not installed; skipping BrowserSession initialization")
            return None

        if self._session is not None:
            return self._session

        try:
            viewport = {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            }
            self._session = BrowserSession(
                headless=self.settings.headless,
                viewport=viewport,
                user_agent=self.settings.user_agent,
                env=self.settings.extra_env or None,
                profile_id=self.settings.profile_id,
                cloud_browser=self.settings.use_cloud_browser or None,
            )
            self.logger.info("BrowserSession instantiated (headless=%s)", self.settings.headless)
        except Exception as exc:  # pragma: no cover - depends on local browser-install state
            self.logger.warning("Unable to initialise BrowserSession: %s", exc)
            self._session = None
        return self._session


class SessionService:
    """Business logic for creating and retrieving scraping sessions."""

    def __init__(self, settings: AppSettings, logger: Optional[logging.Logger] = None):
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.browser_client = BrowserUseClient(settings.browser_use, self.logger)

    @classmethod
    def from_app(cls, app: Flask) -> "SessionService":
        settings = app.config["SETTINGS"]
        return cls(settings=settings, logger=app.logger)

    def create_session(self, *, url: str, instructions: Optional[str], metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        metadata = dict(metadata or {})
        session_id = str(uuid.uuid4())
        timestamp = _utc_now()

        agent = DataExtractionAgent(
            provider=self.settings.default_llm_provider,
            instructions=instructions or ""
        )
        plan = agent.build_plan(url)

        browser_session = self.browser_client.ensure_session()
        session_payload: Dict[str, Any] = {
            "session_id": session_id,
            "status": "queued",
            "url": url,
            "instructions": instructions,
            "metadata": metadata,
            "created_at": timestamp,
            "updated_at": timestamp,
            "plan": plan,
            "browser": {
                "client_initialized": browser_session is not None,
                "headless": self.settings.browser_use.headless,
            },
        }

        _SessionStore.save(session_payload)
        self.logger.info("Session queued", extra={"session_id": session_id, "url": url})
        return session_payload

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = _SessionStore.get(session_id)
        if session:
            session = {**session, "updated_at": _utc_now()}
            _SessionStore.save(session)
        return session
