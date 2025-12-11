"""Data models for the exploration orchestrator."""
from .exploration_session import (
    ExplorationSession,
    ActionLog,
    ScreenshotMetadata,
    SessionStatus,
    AgentRole,
    ActionType,
)
from .approval_gate import ApprovalGate, ApprovalStatus, ApprovalType
from .scraper_generation import GeneratedScraper, ScraperTestResult, GenerationStatus, TestStatus

__all__ = [
    "ExplorationSession",
    "ActionLog", 
    "ScreenshotMetadata",
    "SessionStatus",
    "AgentRole",
    "ActionType",
    "ApprovalGate",
    "ApprovalStatus",
    "ApprovalType",
    "GeneratedScraper",
    "ScraperTestResult",
    "GenerationStatus",
    "TestStatus",
]