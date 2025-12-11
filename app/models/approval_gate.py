"""Approval gate models for exploration and scraper delivery pipeline."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ApprovalStatus(Enum):
    """Status of an approval gate."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class ApprovalType(Enum):
    """Types of approval gates."""
    EXPLORATION_SUMMARY = "exploration_summary"
    SCRAPER_GENERATION = "scraper_generation"
    FINAL_DELIVERY = "final_delivery"


@dataclass
class ApprovalGate:
    """Represents an approval gate in the pipeline."""
    approval_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approval_type: ApprovalType = ApprovalType.EXPLORATION_SUMMARY
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Approval metadata
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    
    # Content and feedback
    summary: str = ""
    feedback: str = ""
    notes: Dict[str, Any] = field(default_factory=dict)
    
    def approve(self, actor: str, feedback: str = "") -> None:
        """Approve this gate."""
        self.status = ApprovalStatus.APPROVED
        self.approved_by = actor
        self.approved_at = datetime.now(tz=timezone.utc).isoformat()
        self.updated_at = self.approved_at
        if feedback:
            self.feedback = feedback
    
    def reject(self, actor: str, feedback: str = "") -> None:
        """Reject this gate."""
        self.status = ApprovalStatus.REJECTED
        self.approved_by = actor
        self.approved_at = datetime.now(tz=timezone.utc).isoformat()
        self.updated_at = self.approved_at
        if feedback:
            self.feedback = feedback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "approval_id": self.approval_id,
            "approval_type": self.approval_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "summary": self.summary,
            "feedback": self.feedback,
            "notes": self.notes,
        }
