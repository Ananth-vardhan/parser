"""Exploration session data model with persistent state and action logging."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(Enum):
    """Status of an exploration session."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(Enum):
    """Roles in the multi-agent system."""
    COORDINATOR = "coordinator"
    BROWSER = "browser"
    ANALYST = "analyst"


class ActionType(Enum):
    """Types of actions that can be logged."""
    PLAN_CREATION = "plan_creation"
    NAVIGATION = "navigation"
    DOM_QUERY = "dom_query"
    SCREENSHOT = "screenshot"
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    ERROR = "error"
    USER_INPUT = "user_input"


@dataclass
class AgentState:
    """State of a specific agent in the system."""
    role: AgentRole
    status: str = "idle"
    current_task: Optional[str] = None
    reasoning: Optional[str] = None
    last_action: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


@dataclass
class ActionLog:
    """Structured log entry for actions and decisions."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    agent_role: Optional[AgentRole] = None
    action_type: Optional[ActionType] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "agent_role": self.agent_role.value if self.agent_role else None,
            "action_type": self.action_type.value if self.action_type else None,
            "description": self.description,
            "details": self.details,
            "reasoning": self.reasoning,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ScreenshotMetadata:
    """Metadata for captured screenshots."""
    screenshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    url: str = ""
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    observations: List[str] = field(default_factory=list)
    dom_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screenshot_id": self.screenshot_id,
            "timestamp": self.timestamp,
            "url": self.url,
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "observations": self.observations,
            "dom_summary": self.dom_summary,
            "metadata": self.metadata,
        }


@dataclass
class ExplorationSession:
    """Complete exploration session with persistent state."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    objectives: str = ""
    status: SessionStatus = SessionStatus.CREATED
    
    # Agent states
    coordinator_state: AgentState = field(default_factory=lambda: AgentState(AgentRole.COORDINATOR))
    browser_state: AgentState = field(default_factory=lambda: AgentState(AgentRole.BROWSER))
    analyst_state: AgentState = field(default_factory=lambda: AgentState(AgentRole.ANALYST))
    
    # Logs and data
    action_logs: List[ActionLog] = field(default_factory=list)
    screenshots: List[ScreenshotMetadata] = field(default_factory=list)
    
    # Session metadata
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Progress tracking
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    
    # Configuration
    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_screenshots: bool = True
    
    # Chat/messaging
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Approval gates and scraper generation
    approval_gates: List[Dict[str, Any]] = field(default_factory=list)
    generated_scrapers: List[Dict[str, Any]] = field(default_factory=list)
    current_scraper: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "url": self.url,
            "objectives": self.objectives,
            "status": self.status.value,
            "coordinator_state": {
                "role": self.coordinator_state.role.value,
                "status": self.coordinator_state.status,
                "current_task": self.coordinator_state.current_task,
                "reasoning": self.coordinator_state.reasoning,
                "last_action": self.coordinator_state.last_action,
                "context": self.coordinator_state.context,
                "created_at": self.coordinator_state.created_at,
                "updated_at": self.coordinator_state.updated_at,
            },
            "browser_state": {
                "role": self.browser_state.role.value,
                "status": self.browser_state.status,
                "current_task": self.browser_state.current_task,
                "reasoning": self.browser_state.reasoning,
                "last_action": self.browser_state.last_action,
                "context": self.browser_state.context,
                "created_at": self.browser_state.created_at,
                "updated_at": self.browser_state.updated_at,
            },
            "analyst_state": {
                "role": self.analyst_state.role.value,
                "status": self.analyst_state.status,
                "current_task": self.analyst_state.current_task,
                "reasoning": self.analyst_state.reasoning,
                "last_action": self.analyst_state.last_action,
                "context": self.analyst_state.context,
                "created_at": self.analyst_state.created_at,
                "updated_at": self.analyst_state.updated_at,
            },
            "action_logs": [log.to_dict() for log in self.action_logs],
            "screenshots": [screenshot.to_dict() for screenshot in self.screenshots],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percentage": self.progress_percentage,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "enable_screenshots": self.enable_screenshots,
            "messages": self.messages,
            "approval_gates": self.approval_gates,
            "generated_scrapers": self.generated_scrapers,
            "current_scraper": self.current_scraper,
        }

    def add_action_log(self, log: ActionLog) -> None:
        """Add an action log entry and update session timestamp."""
        self.action_logs.append(log)
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        
    def add_screenshot(self, screenshot: ScreenshotMetadata) -> None:
        """Add a screenshot and update session timestamp."""
        self.screenshots.append(screenshot)
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        
    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a chat message and update session timestamp."""
        self.messages.append(message)
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        
    def update_status(self, status: SessionStatus) -> None:
        """Update session status and timestamps."""
        self.status = status
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
        
        if status == SessionStatus.RUNNING and not self.started_at:
            self.started_at = datetime.now(tz=timezone.utc).isoformat()
        elif status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
            self.completed_at = datetime.now(tz=timezone.utc).isoformat()
            
    def update_progress(self, current_step: int, total_steps: int) -> None:
        """Update progress tracking."""
        self.current_step = current_step
        self.total_steps = total_steps
        self.progress_percentage = (current_step / total_steps * 100) if total_steps > 0 else 0.0
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()