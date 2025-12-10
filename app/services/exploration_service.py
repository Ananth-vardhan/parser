"""Service for managing exploration sessions and orchestrators."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.exploration_session import ExplorationSession, SessionStatus
from app.services.exploration_orchestrator import ExplorationOrchestrator


class ExplorationSessionStore:
    """Thread-safe store for managing exploration sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, ExplorationSession] = {}
        self._orchestrators: Dict[str, ExplorationOrchestrator] = {}
        self._lock = threading.Lock()
        
    def create_session(self, url: str, objectives: str, metadata: Optional[Dict[str, Any]] = None) -> ExplorationSession:
        """Create a new exploration session."""
        with self._lock:
            session = ExplorationSession(
                url=url,
                objectives=objectives,
                status=SessionStatus.CREATED
            )
            
            if metadata:
                # Add metadata to session messages
                session.add_message({
                    "type": "session_created",
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "metadata": metadata
                })
            
            self._sessions[session.session_id] = session
            return session
            
    def get_session(self, session_id: str) -> Optional[ExplorationSession]:
        """Retrieve a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)
            
    def update_session(self, session: ExplorationSession) -> None:
        """Update a session in the store."""
        with self._lock:
            self._sessions[session.session_id] = session
            
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its orchestrator."""
        with self._lock:
            if session_id in self._sessions:
                # Stop any running orchestrator
                if session_id in self._orchestrators:
                    orchestrator = self._orchestrators[session_id]
                    orchestrator.stop_exploration()
                    del self._orchestrators[session_id]
                    
                del self._sessions[session_id]
                return True
            return False
            
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with basic information."""
        with self._lock:
            return [
                {
                    "session_id": session.session_id,
                    "url": session.url,
                    "status": session.status.value,
                    "created_at": session.created_at,
                    "progress": session.progress_percentage
                }
                for session in self._sessions.values()
            ]
            
    def create_orchestrator(self, session_id: str, browser_settings: Dict[str, Any], 
                           logger: Optional[logging.Logger] = None) -> Optional[ExplorationOrchestrator]:
        """Create an orchestrator for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
                
            orchestrator = ExplorationOrchestrator(session, browser_settings, logger)
            self._orchestrators[session_id] = orchestrator
            return orchestrator
            
    def get_orchestrator(self, session_id: str) -> Optional[ExplorationOrchestrator]:
        """Get an existing orchestrator."""
        with self._lock:
            return self._orchestrators.get(session_id)
            
    def remove_orchestrator(self, session_id: str) -> bool:
        """Remove an orchestrator from the store."""
        with self._lock:
            if session_id in self._orchestrators:
                # Stop the orchestrator if running
                orchestrator = self._orchestrators[session_id]
                orchestrator.stop_exploration()
                del self._orchestrators[session_id]
                return True
            return False


class ExplorationService:
    """Service for managing exploration sessions and orchestrators."""
    
    def __init__(self, browser_settings: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.browser_settings = browser_settings
        self.logger = logger or logging.getLogger(__name__)
        self.store = ExplorationSessionStore()
        
    @classmethod
    def from_app_settings(cls, settings: Any, logger: Optional[logging.Logger] = None) -> "ExplorationService":
        """Create service from app settings."""
        browser_settings = {
            "headless": settings.browser_use.headless,
            "viewport_width": settings.browser_use.viewport_width,
            "viewport_height": settings.browser_use.viewport_height,
            "user_agent": settings.browser_use.user_agent,
            "profile_id": settings.browser_use.profile_id,
            "use_cloud_browser": settings.browser_use.use_cloud_browser,
            "extra_env": settings.browser_use.extra_env
        }
        return cls(browser_settings, logger)
        
    def create_exploration_session(self, url: str, objectives: str, 
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new exploration session."""
        session = self.store.create_session(url, objectives, metadata)
        
        self.logger.info(f"Created exploration session {session.session_id} for {url}")
        
        return {
            "session_id": session.session_id,
            "url": session.url,
            "objectives": session.objectives,
            "status": session.status.value,
            "created_at": session.created_at,
            "progress": 0,
            "message": "Exploration session created successfully"
        }
        
    def start_exploration(self, session_id: str) -> Dict[str, Any]:
        """Start an exploration for a session."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
            
        # Check if already running
        orchestrator = self.store.get_orchestrator(session_id)
        if orchestrator and orchestrator.is_running:
            return {"error": "Exploration already running"}
            
        # Create new orchestrator
        orchestrator = self.store.create_orchestrator(session_id, self.browser_settings, self.logger)
        if not orchestrator:
            return {"error": "Failed to create orchestrator"}
            
        try:
            # Start exploration in a separate thread to avoid blocking
            import threading
            
            def run_exploration():
                try:
                    result = orchestrator.start_exploration()
                    self.logger.info(f"Exploration completed for session {session_id}: {result}")
                except Exception as e:
                    self.logger.error(f"Exploration failed for session {session_id}: {e}")
                    
            exploration_thread = threading.Thread(target=run_exploration, daemon=True)
            exploration_thread.start()
            
            return {
                "success": True,
                "session_id": session_id,
                "status": "starting",
                "message": "Exploration started in background"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start exploration: {e}")
            return {"error": f"Failed to start exploration: {str(e)}"}
            
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a session."""
        session = self.store.get_session(session_id)
        if not session:
            return None
            
        orchestrator = self.store.get_orchestrator(session_id)
        if orchestrator:
            return orchestrator.get_current_status()
        else:
            return session.to_dict()
            
    def pause_exploration(self, session_id: str) -> Dict[str, Any]:
        """Pause a running exploration."""
        orchestrator = self.store.get_orchestrator(session_id)
        if not orchestrator:
            return {"error": "No active exploration found"}
            
        return orchestrator.pause_exploration()
        
    def resume_exploration(self, session_id: str) -> Dict[str, Any]:
        """Resume a paused exploration."""
        orchestrator = self.store.get_orchestrator(session_id)
        if not orchestrator:
            return {"error": "No paused exploration found"}
            
        return orchestrator.resume_exploration()
        
    def stop_exploration(self, session_id: str) -> Dict[str, Any]:
        """Stop an exploration."""
        orchestrator = self.store.get_orchestrator(session_id)
        if not orchestrator:
            return {"error": "No active exploration found"}
            
        result = orchestrator.stop_exploration()
        self.store.remove_orchestrator(session_id)
        return result
        
    def send_chat_message(self, session_id: str, message: str, 
                         message_type: str = "user") -> Dict[str, Any]:
        """Send a chat message to an exploration session."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
            
        chat_message = {
            "message_id": str(uuid.uuid4()),
            "type": message_type,
            "content": message,
            "timestamp": datetime.now(tz=timezone.utc).isoformat()
        }
        
        session.add_message(chat_message)
        self.store.update_session(session)
        
        # If it's a user instruction and exploration is running, process it
        if message_type == "user" and session.status == SessionStatus.RUNNING:
            orchestrator = self.store.get_orchestrator(session_id)
            if orchestrator:
                # Add instruction to coordinator context
                instruction_log = f"User instruction: {message}"
                orchestrator.coordinator.state.context["user_instructions"] = \
                    orchestrator.coordinator.state.context.get("user_instructions", []) + [instruction_log]
                    
        return {
            "success": True,
            "message_id": chat_message["message_id"],
            "session_id": session_id
        }
        
    def get_chat_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat messages for a session."""
        session = self.store.get_session(session_id)
        if not session:
            return []
            
        messages = session.messages[-limit:] if limit > 0 else session.messages
        return messages
        
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all exploration sessions."""
        return self.store.list_sessions()
        
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its orchestrator."""
        result = self.store.delete_session(session_id)
        if result:
            self.logger.info(f"Deleted exploration session {session_id}")
        return result