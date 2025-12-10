"""Minimal agent stub that simulates planning work for browser-use sessions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AgentPlan:
    provider: str
    instructions: str
    steps: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "provider": self.provider,
            "instructions": self.instructions,
            "steps": self.steps,
        }


class DataExtractionAgent:
    """Placeholder agent that builds a deterministic plan for scraping."""

    def __init__(self, *, provider: str, instructions: str) -> None:
        self.provider = provider
        self.instructions = instructions.strip() or "Extract the requested fields from the target page."

    def build_plan(self, url: str) -> Dict[str, object]:
        steps = [
            f"Launch a Chromium instance and navigate to {url}.",
            "Wait for dynamic content to settle (network idle).",
            "Locate elements that match the instructions (tables, cards, or key DOM nodes).",
            "Normalize and structure the extracted records before returning them.",
        ]
        return AgentPlan(provider=self.provider, instructions=self.instructions, steps=steps).to_dict()
