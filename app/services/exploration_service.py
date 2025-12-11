"""Service for managing exploration sessions and orchestrators."""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.exploration_session import ExplorationSession, SessionStatus
from app.models import (
    ApprovalGate,
    ApprovalStatus,
    ApprovalType,
    GeneratedScraper,
)
from app.services.exploration_orchestrator import ExplorationOrchestrator
from app.services.scraper_generator import ScraperGenerator
from app.services.scraper_tester import ScraperTester
from app.services.approval_pipeline import ApprovalPipeline


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
    
    def __init__(
        self,
        browser_settings: Dict[str, Any],
        logger: Optional[logging.Logger] = None,
        openai_api_key: Optional[str] = None
    ):
        self.browser_settings = browser_settings
        self.logger = logger or logging.getLogger(__name__)
        self.store = ExplorationSessionStore()
        
        # Initialize approval pipeline components
        self.openai_api_key = openai_api_key
        if openai_api_key:
            self.scraper_generator = ScraperGenerator(openai_api_key, logger=logger)
            self.approval_pipeline = ApprovalPipeline(self.scraper_generator, logger=logger)
        else:
            self.scraper_generator = None
            self.approval_pipeline = None
        
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
        return cls(browser_settings, logger, openai_api_key=settings.openai_api_key)
        
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
    
    # Approval Pipeline Methods
    
    def generate_specification(self, session_id: str) -> Dict[str, Any]:
        """Generate scraper specification from exploration logs."""
        if not self.scraper_generator:
            return {"error": "Code generation not configured. OpenAI API key required."}
        
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        try:
            specification = self.scraper_generator.generate_specification(session)
            
            # Create exploration approval gate
            approval = self.approval_pipeline.create_exploration_approval(session)
            
            # Add approval gate to session
            session.approval_gates.append(approval.to_dict())
            self.store.update_session(session)
            
            return {
                "success": True,
                "session_id": session_id,
                "specification": specification,
                "approval": approval.to_dict()
            }
        except Exception as e:
            self.logger.error(f"Failed to generate specification: {e}", exc_info=True)
            return {"error": f"Failed to generate specification: {str(e)}"}
    
    def approve_exploration(
        self,
        session_id: str,
        action: str,
        actor: str,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Approve or reject exploration summary."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Find exploration approval gate
        exploration_approval = None
        for gate_dict in session.approval_gates:
            if gate_dict["approval_type"] == "exploration_summary":
                exploration_approval = gate_dict
                break
        
        if not exploration_approval:
            return {"error": "No exploration approval gate found. Generate specification first."}
        
        # Update approval status
        if action == "approve":
            exploration_approval["status"] = "approved"
            exploration_approval["approved_by"] = actor
            exploration_approval["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
            if feedback:
                exploration_approval["feedback"] = feedback
        else:
            exploration_approval["status"] = "rejected"
            exploration_approval["approved_by"] = actor
            exploration_approval["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
            exploration_approval["feedback"] = feedback
        
        exploration_approval["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        
        self.store.update_session(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "action": action,
            "approval": exploration_approval
        }
    
    def generate_scraper(
        self,
        session_id: str,
        assertions: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """Generate scraper code from exploration."""
        if not self.approval_pipeline:
            return {"error": "Code generation not configured. OpenAI API key required."}
        
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check approval sequencing
        valid, message = self.approval_pipeline.check_approval_sequencing(
            session,
            ApprovalType.SCRAPER_GENERATION
        )
        if not valid:
            return {"error": message}
        
        try:
            # Start generation in background thread
            def run_generation():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    scraper = loop.run_until_complete(
                        self.approval_pipeline.generate_and_test_scraper(
                            session,
                            assertions,
                            max_iterations
                        )
                    )
                    
                    loop.close()
                    
                    # Save scraper to session
                    scraper_dict = scraper.to_dict()
                    session.generated_scrapers.append(scraper_dict)
                    session.current_scraper = scraper_dict
                    
                    # Create scraper approval gate
                    approval = self.approval_pipeline.create_scraper_approval(session, scraper)
                    session.approval_gates.append(approval.to_dict())
                    
                    self.store.update_session(session)
                    
                    self.logger.info(f"Scraper generation completed for session {session_id}")
                except Exception as e:
                    self.logger.error(f"Scraper generation failed: {e}", exc_info=True)
            
            generation_thread = threading.Thread(target=run_generation, daemon=True)
            generation_thread.start()
            
            return {
                "success": True,
                "session_id": session_id,
                "status": "generating",
                "message": "Scraper generation started in background"
            }
        except Exception as e:
            self.logger.error(f"Failed to start scraper generation: {e}", exc_info=True)
            return {"error": f"Failed to start scraper generation: {str(e)}"}
    
    def test_scraper(
        self,
        session_id: str,
        assertions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Test the generated scraper."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if not session.current_scraper:
            return {"error": "No scraper generated yet"}
        
        try:
            # Start testing in background
            def run_test():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Reconstruct scraper from dict
                    from app.models import GeneratedScraper, ScraperTestResult, GenerationStatus, TestStatus
                    scraper_dict = session.current_scraper
                    scraper = GeneratedScraper(
                        scraper_id=scraper_dict["scraper_id"],
                        session_id=scraper_dict["session_id"],
                        version=scraper_dict["version"],
                        specification=scraper_dict["specification"],
                        code=scraper_dict["code"]
                    )
                    scraper.status = GenerationStatus(scraper_dict["status"])
                    
                    tester = ScraperTester(session.url, self.logger)
                    test_assertions = assertions or tester.get_default_assertions()
                    
                    test_result = loop.run_until_complete(
                        tester.test_scraper(scraper, test_assertions)
                    )
                    
                    loop.close()
                    
                    # Update scraper with test results
                    scraper.add_test_result(test_result)
                    session.current_scraper = scraper.to_dict()
                    self.store.update_session(session)
                    
                    self.logger.info(f"Scraper test completed for session {session_id}")
                except Exception as e:
                    self.logger.error(f"Scraper test failed: {e}", exc_info=True)
            
            test_thread = threading.Thread(target=run_test, daemon=True)
            test_thread.start()
            
            return {
                "success": True,
                "session_id": session_id,
                "status": "testing",
                "message": "Scraper testing started in background"
            }
        except Exception as e:
            self.logger.error(f"Failed to start scraper test: {e}", exc_info=True)
            return {"error": f"Failed to start scraper test: {str(e)}"}
    
    def approve_scraper(
        self,
        session_id: str,
        action: str,
        actor: str,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Approve or reject generated scraper."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check approval sequencing
        valid, message = self.approval_pipeline.check_approval_sequencing(
            session,
            ApprovalType.FINAL_DELIVERY
        )
        if not valid:
            return {"error": message}
        
        # Find scraper approval gate
        scraper_approval = None
        for gate_dict in session.approval_gates:
            if gate_dict["approval_type"] == "scraper_generation":
                scraper_approval = gate_dict
                break
        
        if not scraper_approval:
            return {"error": "No scraper approval gate found"}
        
        # Update approval status
        if action == "approve":
            scraper_approval["status"] = "approved"
            scraper_approval["approved_by"] = actor
            scraper_approval["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
            if feedback:
                scraper_approval["feedback"] = feedback
            
            # Create delivery approval gate
            from app.models import GeneratedScraper
            scraper_dict = session.current_scraper
            if scraper_dict:
                scraper = GeneratedScraper(
                    scraper_id=scraper_dict["scraper_id"],
                    session_id=scraper_dict["session_id"],
                    version=scraper_dict["version"],
                    specification=scraper_dict["specification"],
                    code=scraper_dict["code"]
                )
                delivery_approval = self.approval_pipeline.create_delivery_approval(session, scraper)
                session.approval_gates.append(delivery_approval.to_dict())
        else:
            scraper_approval["status"] = "rejected"
            scraper_approval["approved_by"] = actor
            scraper_approval["approved_at"] = datetime.now(tz=timezone.utc).isoformat()
            scraper_approval["feedback"] = feedback
        
        scraper_approval["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        
        self.store.update_session(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "action": action,
            "approval": scraper_approval
        }
    
    def get_scraper_details(self, session_id: str) -> Dict[str, Any]:
        """Get current scraper details."""
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if not session.current_scraper:
            return {"error": "No scraper generated yet"}
        
        return {
            "success": True,
            "session_id": session_id,
            "scraper": session.current_scraper,
            "approval_gates": session.approval_gates
        }
    
    def download_scraper_package(self, session_id: str) -> Dict[str, Any]:
        """Download finalized scraper package."""
        if not self.approval_pipeline:
            return {"error": "Code generation not configured"}
        
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check that final delivery is approved
        delivery_approved = False
        for gate_dict in session.approval_gates:
            if gate_dict["approval_type"] == "final_delivery" and gate_dict["status"] == "approved":
                delivery_approved = True
                break
        
        if not delivery_approved:
            return {"error": "Final delivery must be approved before download"}
        
        if not session.current_scraper:
            return {"error": "No scraper available"}
        
        try:
            # Reconstruct scraper from dict
            from app.models import GeneratedScraper
            scraper_dict = session.current_scraper
            scraper = GeneratedScraper(
                scraper_id=scraper_dict["scraper_id"],
                session_id=scraper_dict["session_id"],
                version=scraper_dict["version"],
                specification=scraper_dict["specification"],
                code=scraper_dict["code"],
                language=scraper_dict["language"],
                framework=scraper_dict["framework"]
            )
            scraper.dependencies = scraper_dict.get("dependencies", [])
            scraper.readme = scraper_dict.get("readme", "")
            
            # Reconstruct test results
            for test_dict in scraper_dict.get("test_results", []):
                from app.models import ScraperTestResult, TestStatus
                test_result = ScraperTestResult()
                test_result.test_id = test_dict["test_id"]
                test_result.timestamp = test_dict["timestamp"]
                test_result.status = TestStatus(test_dict["status"])
                test_result.execution_time_ms = test_dict.get("execution_time_ms")
                test_result.error_message = test_dict.get("error_message")
                test_result.assertions_passed = test_dict.get("assertions_passed", 0)
                test_result.assertions_failed = test_dict.get("assertions_failed", 0)
                scraper.test_results.append(test_result)
            
            # Generate package
            package_bytes = self.approval_pipeline.generate_scraper_package(session, scraper)
            
            return {
                "success": True,
                "session_id": session_id,
                "package": package_bytes
            }
        except Exception as e:
            self.logger.error(f"Failed to generate package: {e}", exc_info=True)
            return {"error": f"Failed to generate package: {str(e)}"}
    
    def get_scraper_diffs(self, session_id: str) -> Dict[str, Any]:
        """Get diffs between scraper iterations."""
        if not self.approval_pipeline:
            return {"error": "Code generation not configured"}
        
        session = self.store.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        if not session.current_scraper:
            return {"error": "No scraper generated yet"}
        
        try:
            # Reconstruct scraper
            from app.models import GeneratedScraper, ScraperTestResult, TestStatus
            scraper_dict = session.current_scraper
            scraper = GeneratedScraper(
                scraper_id=scraper_dict["scraper_id"],
                version=scraper_dict["version"]
            )
            
            # Reconstruct test results for diffs
            for test_dict in scraper_dict.get("test_results", []):
                test_result = ScraperTestResult()
                test_result.test_id = test_dict["test_id"]
                test_result.timestamp = test_dict["timestamp"]
                test_result.status = TestStatus(test_dict["status"])
                test_result.error_message = test_dict.get("error_message")
                test_result.assertions_passed = test_dict.get("assertions_passed", 0)
                test_result.assertions_failed = test_dict.get("assertions_failed", 0)
                scraper.test_results.append(test_result)
            
            diffs = self.approval_pipeline.get_scraper_diffs(scraper)
            
            return {
                "success": True,
                "session_id": session_id,
                "diffs": diffs
            }
        except Exception as e:
            self.logger.error(f"Failed to get diffs: {e}", exc_info=True)
            return {"error": f"Failed to get diffs: {str(e)}"}