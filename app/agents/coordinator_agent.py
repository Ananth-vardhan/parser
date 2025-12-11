"""Coordinator agent that plans and orchestrates exploration steps."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from app.models.exploration_session import (
    AgentRole, AgentState, ActionLog, ActionType, SessionStatus
)


class CoordinatorAgent:
    """Agent responsible for planning and coordinating exploration activities."""
    
    def __init__(self, session_id: str, logger: Optional[logging.Logger] = None, 
                 enable_ai: bool = True, gemini_api_key: Optional[str] = None):
        self.session_id = session_id
        self.logger = logger or logging.getLogger(__name__)
        self.state = AgentState(role=AgentRole.COORDINATOR)
        self.enable_ai = enable_ai
        
        # Initialize Gemini AI integration if enabled
        if self.enable_ai:
            try:
                from app.services.gemini_integration import GeminiExplorationAssistant
                self.gemini_assistant = GeminiExplorationAssistant(gemini_api_key, logger)
                self.logger.info("CoordinatorAgent initialized with Gemini AI")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Gemini AI: {e}")
                self.gemini_assistant = None
        else:
            self.gemini_assistant = None
        
    def create_exploration_plan(self, url: str, objectives: str) -> Dict[str, Any]:
        """Create a structured plan for exploring the target URL."""
        self.state.status = "planning"
        self.state.current_task = "create_exploration_plan"
        
        # Create basic structured plan
        basic_plan = {
            "url": url,
            "objectives": objectives,
            "steps": self._break_down_objectives(objectives),
            "estimated_duration": self._estimate_duration(objectives),
            "required_capabilities": ["navigation", "dom_extraction", "screenshot_analysis"],
            "success_criteria": self._define_success_criteria(objectives)
        }
        
        # Enhance with Gemini AI if available
        if self.gemini_assistant:
            try:
                ai_plan = self.gemini_assistant.generate_exploration_plan(url, objectives, basic_plan)
                if "error" not in ai_plan:
                    # Merge AI insights with basic plan
                    basic_plan["ai_enhanced"] = True
                    basic_plan["ai_strategy"] = ai_plan.get("strategy", "")
                    basic_plan["ai_challenges"] = ai_plan.get("challenges", [])
                    basic_plan["ai_confidence"] = ai_plan.get("confidence", 0.8)
                    basic_plan["ai_steps"] = ai_plan.get("steps", [])
                    
                    # Merge AI-generated steps with basic steps
                    if ai_plan.get("steps"):
                        basic_plan["steps"].extend(ai_plan["steps"])
                    
                    self.state.reasoning = f"Created AI-enhanced exploration plan for {url} with {len(basic_plan['steps'])} steps"
                    self.logger.info("Enhanced plan with Gemini AI insights")
                else:
                    self.state.reasoning = f"Created basic exploration plan for {url} with {len(basic_plan['steps'])} steps (AI unavailable)"
                    self.logger.warning("AI planning failed, using basic plan")
            except Exception as e:
                self.state.reasoning = f"Created basic exploration plan for {url} with {len(basic_plan['steps'])} steps (AI error: {str(e)})"
                self.logger.error(f"AI enhancement failed: {e}")
        else:
            self.state.reasoning = f"Created exploration plan for {url} with {len(basic_plan['steps'])} steps"
        
        self.state.status = "ready"
        self.state.current_task = None
        
        return basic_plan
        
    def _break_down_objectives(self, objectives: str) -> List[Dict[str, Any]]:
        """Break down high-level objectives into actionable steps."""
        steps = []
        
        # Always start with navigation and initial analysis
        steps.extend([
            {
                "step_id": 1,
                "type": "navigation",
                "description": "Navigate to target URL",
                "priority": "high",
                "dependencies": []
            },
            {
                "step_id": 2,
                "type": "analysis",
                "description": "Analyze page structure and content",
                "priority": "high", 
                "dependencies": [1]
            }
        ])
        
        # Add objective-specific steps based on keywords
        objectives_lower = objectives.lower()
        step_counter = 3
        
        if any(keyword in objectives_lower for keyword in ["extract", "scrape", "collect"]):
            steps.append({
                "step_id": step_counter,
                "type": "extraction",
                "description": "Extract relevant data from page elements",
                "priority": "high",
                "dependencies": [2]
            })
            step_counter += 1
            
        if any(keyword in objectives_lower for keyword in ["form", "input", "submit"]):
            steps.append({
                "step_id": step_counter,
                "type": "interaction",
                "description": "Handle form interactions and submissions",
                "priority": "medium",
                "dependencies": [2]
            })
            step_counter += 1
            
        if any(keyword in objectives_lower for keyword in ["scroll", "paginate", "load more"]):
            steps.append({
                "step_id": step_counter,
                "type": "navigation",
                "description": "Navigate through content (scroll/paginate)",
                "priority": "medium",
                "dependencies": [2]
            })
            step_counter += 1
            
        # Always end with analysis and summary
        steps.append({
            "step_id": step_counter,
            "type": "analysis",
            "description": "Analyze findings and create summary",
            "priority": "high",
            "dependencies": [s["step_id"] for s in steps if s["type"] in ["extraction", "interaction", "navigation"] and s["step_id"] != step_counter]
        })
        
        return steps
        
    def _estimate_duration(self, objectives: str) -> str:
        """Estimate how long the exploration might take."""
        complexity_keywords = {
            "simple": ["view", "check", "look"],
            "moderate": ["extract", "scrape", "form"],
            "complex": ["navigate", "paginate", "interact", "analyze"]
        }
        
        objectives_lower = objectives.lower()
        
        if any(word in objectives_lower for word in complexity_keywords["complex"]):
            return "15-30 minutes"
        elif any(word in objectives_lower for word in complexity_keywords["moderate"]):
            return "5-15 minutes"
        else:
            return "2-5 minutes"
            
    def _define_success_criteria(self, objectives: str) -> List[str]:
        """Define what constitutes successful completion."""
        criteria = []
        objectives_lower = objectives.lower()
        
        if any(word in objectives_lower for word in ["extract", "scrape", "collect"]):
            criteria.append("Successfully extracted relevant data from target elements")
            
        if any(word in objectives_lower for word in ["navigate", "browse", "explore"]):
            criteria.append("Successfully navigated to target URL and explored content")
            
        if any(word in objectives_lower for word in ["form", "submit"]):
            criteria.append("Successfully handled form interactions if present")
            
        criteria.append("Captured screenshots for documentation")
        criteria.append("Generated comprehensive analysis report")
        
        return criteria
        
    def select_next_action(self, current_state: Dict[str, Any], available_actions: List[str]) -> Optional[Dict[str, Any]]:
        """Select the next action based on current state and available options."""
        self.state.status = "decision_making"
        self.state.current_task = "select_next_action"
        
        # Simple decision logic - can be enhanced with more sophisticated AI
        completed_steps = current_state.get("completed_steps", [])
        current_step = current_state.get("current_step", 1)
        
        # Check if we have pending steps
        pending_steps = [s for s in current_state.get("plan", {}).get("steps", []) 
                        if s["step_id"] not in completed_steps]
        
        if not pending_steps:
            self.state.reasoning = "All planned steps completed"
            self.state.status = "completed"
            return None
            
        # Select the next step based on dependencies
        next_step = None
        for step in pending_steps:
            if all(dep in completed_steps for dep in step.get("dependencies", [])):
                next_step = step
                break
                
        if next_step:
            self.state.reasoning = f"Selected step {next_step['step_id']}: {next_step['description']}"
            self.state.status = "ready"
            
            return {
                "action": "execute_step",
                "step": next_step,
                "agent": self._determine_agent_for_step(next_step),
                "priority": next_step.get("priority", "medium")
            }
        else:
            self.state.reasoning = "No executable steps available (waiting for dependencies)"
            self.state.status = "waiting"
            return None
            
    def _determine_agent_for_step(self, step: Dict[str, Any]) -> str:
        """Determine which agent should execute a given step."""
        step_type = step.get("type", "").lower()
        
        if step_type in ["navigation", "interaction"]:
            return "browser"
        elif step_type in ["extraction", "analysis"]:
            return "analyst"
        else:
            return "browser"  # Default to browser for unknown types
            
    def update_agent_context(self, agent_role: str, context: Dict[str, Any]) -> None:
        """Update coordination context based on other agent reports."""
        if agent_role == "browser":
            self.state.context["browser_status"] = context.get("status")
            self.state.context["current_url"] = context.get("current_url")
            self.state.context["page_title"] = context.get("page_title")
        elif agent_role == "analyst":
            self.state.context["analysis_results"] = context.get("results", [])
            self.state.context["findings"] = context.get("findings", [])
            
        self.state.updated_at = self._get_timestamp()
        
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(tz=timezone.utc).isoformat()
        
    def log_action(self, description: str, action_type: ActionType, 
                  reasoning: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ActionLog:
        """Create an action log entry for coordinator activities."""
        return ActionLog(
            agent_role=AgentRole.COORDINATOR,
            action_type=action_type,
            description=description,
            reasoning=reasoning,
            details=details or {}
        )