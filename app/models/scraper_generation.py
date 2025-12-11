"""Models for generated scrapers and test results."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class GenerationStatus(Enum):
    """Status of scraper generation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TESTING = "testing"


class TestStatus(Enum):
    """Status of scraper testing."""
    NOT_RUN = "not_run"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class ScraperTestResult:
    """Results from testing a generated scraper."""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    status: TestStatus = TestStatus.NOT_RUN
    
    # Test execution details
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Test results
    assertions_passed: int = 0
    assertions_failed: int = 0
    assertion_details: List[Dict[str, Any]] = field(default_factory=list)
    
    # Captured data
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    console_logs: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "test_id": self.test_id,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "assertion_details": self.assertion_details,
            "extracted_data": self.extracted_data,
            "screenshots": self.screenshots,
            "console_logs": self.console_logs,
            "metadata": self.metadata,
        }


@dataclass
class GeneratedScraper:
    """Represents a generated scraper with code and metadata."""
    scraper_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    version: int = 1
    status: GenerationStatus = GenerationStatus.NOT_STARTED
    
    # Code and specification
    specification: str = ""
    code: str = ""
    language: str = "python"
    framework: str = "playwright"
    
    # Generation metadata
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    generation_prompt: str = ""
    model_used: str = ""
    
    # Testing results
    test_results: List[ScraperTestResult] = field(default_factory=list)
    last_test_status: TestStatus = TestStatus.NOT_RUN
    
    # Iteration tracking
    iteration_count: int = 0
    max_iterations: int = 5
    generation_errors: List[str] = field(default_factory=list)
    
    # Package metadata
    dependencies: List[str] = field(default_factory=list)
    readme: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_test_result(self, result: ScraperTestResult) -> None:
        """Add a test result to this scraper."""
        self.test_results.append(result)
        self.last_test_status = result.status
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
    
    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1
        self.iteration_count += 1
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
    
    def update_status(self, status: GenerationStatus) -> None:
        """Update generation status."""
        self.status = status
        self.updated_at = datetime.now(tz=timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "scraper_id": self.scraper_id,
            "session_id": self.session_id,
            "version": self.version,
            "status": self.status.value,
            "specification": self.specification,
            "code": self.code,
            "language": self.language,
            "framework": self.framework,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "generation_prompt": self.generation_prompt,
            "model_used": self.model_used,
            "test_results": [result.to_dict() for result in self.test_results],
            "last_test_status": self.last_test_status.value,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "generation_errors": self.generation_errors,
            "dependencies": self.dependencies,
            "readme": self.readme,
            "metadata": self.metadata,
        }
