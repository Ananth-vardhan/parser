"""Exploration orchestrator service that coordinates multi-agent exploration."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.coordinator_agent import CoordinatorAgent
from app.agents.browser_agent import BrowserAgent
from app.agents.analyst_agent import AnalystAgent
from app.models.exploration_session import (
    ExplorationSession, ActionLog, ScreenshotMetadata, ActionType, SessionStatus
)


class ExplorationOrchestrator:
    """Orchestrates multi-agent exploration sessions."""
    
    def __init__(self, session: ExplorationSession, browser_settings: Dict[str, Any], 
                 logger: Optional[logging.Logger] = None, gemini_api_key: Optional[str] = None,
                 enable_ai: bool = True):
        self.session = session
        self.browser_settings = browser_settings
        self.logger = logger or logging.getLogger(__name__)
        
        # Get API key from browser settings if not provided
        self.gemini_api_key = gemini_api_key or browser_settings.get("gemini_api_key")
        
        # Initialize agents with AI capabilities
        self.coordinator = CoordinatorAgent(session.session_id, logger, enable_ai, self.gemini_api_key)
        self.browser_agent = BrowserAgent(session.session_id, browser_settings, logger)
        self.analyst_agent = AnalystAgent(session.session_id, logger, enable_ai, self.gemini_api_key)
        
        # State management
        self.is_running = False
        self.current_loop = 0
        self.completed_steps = []
        self.lock = threading.Lock()
        
    def start_exploration(self) -> Dict[str, Any]:
        """Start the exploration process."""
        with self.lock:
            if self.is_running:
                return {"error": "Exploration already running"}
                
            self.is_running = True
            self.session.update_status(SessionStatus.RUNNING)
            
            # Log session start
            start_log = ActionLog(
                agent_role=None,
                action_type=ActionType.PLAN_CREATION,
                description="Exploration session started",
                details={
                    "session_id": self.session.session_id,
                    "url": self.session.url,
                    "objectives": self.session.objectives
                }
            )
            self.session.add_action_log(start_log)
            
            self.logger.info(f"Starting exploration for session {self.session.session_id}")
            
            try:
                # Initialize browser
                browser_initialized = self.browser_agent.initialize_browser()
                if not browser_initialized:
                    self.logger.warning("Browser initialization failed, continuing in stub mode")
                    
                # Create exploration plan
                plan = self.coordinator.create_exploration_plan(
                    self.session.url, 
                    self.session.objectives
                )
                
                plan_log = self.coordinator.log_action(
                    "Exploration plan created",
                    ActionType.PLAN_CREATION,
                    f"Created plan with {len(plan['steps'])} steps",
                    {"plan": plan}
                )
                self.session.add_action_log(plan_log)
                
                # Update session with plan
                self.session.total_steps = len(plan["steps"])
                self.session.update_progress(0, len(plan["steps"]))
                
                # Start the main exploration loop
                result = self._run_exploration_loop(plan)
                
                # Complete the session
                self.session.update_status(SessionStatus.COMPLETED)
                self.session.update_progress(self.session.total_steps, self.session.total_steps)
                
                completion_log = ActionLog(
                    agent_role=None,
                    action_type=ActionType.ANALYSIS,
                    description="Exploration session completed",
                    details={"final_result": result}
                )
                self.session.add_action_log(completion_log)
                
                return {
                    "success": True,
                    "session_id": self.session.session_id,
                    "status": "completed",
                    "final_result": result
                }
                
            except Exception as e:
                self.logger.error(f"Exploration failed: {e}")
                self.session.update_status(SessionStatus.FAILED)
                
                error_log = ActionLog(
                    agent_role=None,
                    action_type=ActionType.ERROR,
                    description="Exploration session failed",
                    error=str(e)
                )
                self.session.add_action_log(error_log)
                
                return {
                    "success": False,
                    "session_id": self.session.session_id,
                    "status": "failed",
                    "error": str(e)
                }
                
            finally:
                self.is_running = False
                self.browser_agent.close()
                
    def _run_exploration_loop(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Run the main exploration loop with multi-agent coordination."""
        self.current_loop = 0
        exploration_results = {
            "pages_visited": [],
            "data_extracted": {},
            "screenshots_captured": [],
            "analyses_completed": [],
            "total_iterations": 0
        }
        
        while (self.current_loop < self.session.max_iterations and 
               self.is_running and 
               self.current_loop < len(plan["steps"])):
            
            self.current_loop += 1
            iteration_start = time.time()
            
            self.logger.info(f"Starting exploration iteration {self.current_loop}")
            
            # Update coordinator with current state
            current_state = {
                "session_id": self.session.session_id,
                "current_loop": self.current_loop,
                "completed_steps": self.completed_steps,
                "current_step": self.current_loop,
                "plan": plan,
                "browser_status": self.browser_agent.get_current_page_info()
            }
            
            # Coordinator selects next action
            next_action = self.coordinator.select_next_action(current_state, plan["steps"])
            
            if not next_action:
                self.logger.info("No more actions to execute")
                break
                
            step = next_action["step"]
            target_agent = next_action["agent"]
            
            self.logger.info(f"Executing step {step['step_id']}: {step['description']} via {target_agent}")
            
            # Execute action based on selected agent
            iteration_result = self._execute_step(step, target_agent, exploration_results)
            
            # Record iteration completion
            self.completed_steps.append(step["step_id"])
            self.session.update_progress(len(self.completed_steps), len(plan["steps"]))
            
            iteration_time = time.time() - iteration_start
            self.logger.info(f"Iteration {self.current_loop} completed in {iteration_time:.2f}s")
            
            # Add iteration log
            iteration_log = ActionLog(
                agent_role=None,
                action_type=ActionType.ANALYSIS,
                description=f"Iteration {self.current_loop} completed",
                details={
                    "step": step,
                    "agent": target_agent,
                    "result": iteration_result,
                    "duration": iteration_time,
                    "completed_steps": self.completed_steps.copy()
                }
            )
            self.session.add_action_log(iteration_log)
            
            # Brief pause between iterations
            time.sleep(1)
            
        # Final synthesis by analyst
        synthesis_result = self.analyst_agent.synthesize_findings(exploration_results)
        
        # Add synthesis log
        synthesis_log = self.analyst_agent.log_action(
            "Final findings synthesis completed",
            ActionType.ANALYSIS,
            "All exploration results synthesized into final report",
            {"synthesis": synthesis_result}
        )
        self.session.add_action_log(synthesis_log)
        
        exploration_results["total_iterations"] = self.current_loop
        exploration_results["final_synthesis"] = synthesis_result
        
        return exploration_results
        
    def _execute_step(self, step: Dict[str, Any], agent: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific step using the designated agent."""
        step_type = step.get("type", "").lower()
        
        if agent == "browser" or step_type in ["navigation", "interaction"]:
            return self._execute_browser_step(step, results)
        elif agent == "analyst" or step_type in ["extraction", "analysis"]:
            return self._execute_analyst_step(step, results)
        else:
            return self._execute_generic_step(step, results)
            
    def _execute_browser_step(self, step: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a browser-related step."""
        step_type = step.get("type", "").lower()
        
        if step_type == "navigation":
            # Navigate to URL
            nav_result = self.browser_agent.navigate_to_url(self.session.url)
            
            if nav_result.get("success") and self.session.enable_screenshots:
                # Capture screenshot
                screenshot = self.browser_agent.capture_screenshot(f"step_{step['step_id']}")
                if screenshot:
                    self.session.add_screenshot(screenshot)
                    results["screenshots_captured"].append(screenshot.to_dict())
                    
                    # Analyze screenshot
                    analysis = self.analyst_agent.analyze_screenshot(screenshot)
                    results["analyses_completed"].append(analysis)
                    
            return nav_result
            
        elif step_type == "analysis":
            # Query DOM for analysis
            dom_result = self.browser_agent.query_dom("body")
            if dom_result.get("success"):
                # Analyze extracted content
                content_analysis = self.analyst_agent.analyze_page_content(dom_result)
                results["analyses_completed"].append(content_analysis)
                
            return dom_result
            
        elif step_type == "interaction":
            # Handle interactions (forms, buttons, etc.)
            interaction_result = self.browser_agent.query_dom("form, button, input[type='submit']")
            
            if interaction_result.get("success"):
                # Analyze interaction elements
                interaction_analysis = self.analyst_agent.analyze_page_content(interaction_result)
                results["analyses_completed"].append(interaction_analysis)
                
            return interaction_result
            
        elif step_type == "extraction":
            # Extract data from common selectors
            common_selectors = [
                "table", "tr", "td", "div[class*='data']", 
                "div[class*='content']", "p", "h1, h2, h3"
            ]
            
            extraction_result = self.browser_agent.extract_data(common_selectors)
            if extraction_result.get("success"):
                results["data_extracted"].update(extraction_result.get("extracted_data", {}))
                
            return extraction_result
            
        else:
            # Generic browser action
            return self.browser_agent.query_dom("*")
            
    def _execute_analyst_step(self, step: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an analysis-related step."""
        # Analyze existing data
        analysis_result = self.analyst_agent.analyze_page_content(results)
        results["analyses_completed"].append(analysis_result)
        
        # Add analyst log
        analyst_log = self.analyst_agent.log_action(
            f"Analysis step completed: {step['description']}",
            ActionType.ANALYSIS,
            "Comprehensive analysis of current exploration state",
            {"step": step, "analysis": analysis_result}
        )
        self.session.add_action_log(analyst_log)
        
        return analysis_result
        
    def _execute_generic_step(self, step: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a generic step."""
        result = {
            "success": True,
            "step_id": step["step_id"],
            "description": step["description"],
            "type": step.get("type", "generic"),
            "completed_at": datetime.now(tz=timezone.utc).isoformat()
        }
        
        # Add generic log
        generic_log = ActionLog(
            agent_role=None,
            action_type=ActionType.EXTRACTION,
            description=f"Generic step completed: {step['description']}",
            details={"step": step, "result": result}
        )
        self.session.add_action_log(generic_log)
        
        return result
        
    def pause_exploration(self) -> Dict[str, Any]:
        """Pause the exploration process."""
        with self.lock:
            self.is_running = False
            self.session.update_status(SessionStatus.PAUSED)
            
            pause_log = ActionLog(
                agent_role=None,
                action_type=ActionType.PLAN_CREATION,
                description="Exploration session paused"
            )
            self.session.add_action_log(pause_log)
            
            return {"success": True, "status": "paused"}
            
    def resume_exploration(self) -> Dict[str, Any]:
        """Resume a paused exploration."""
        with self.lock:
            if self.session.status != SessionStatus.PAUSED:
                return {"error": "Session is not paused"}
                
            self.is_running = True
            self.session.update_status(SessionStatus.RUNNING)
            
            resume_log = ActionLog(
                agent_role=None,
                action_type=ActionType.PLAN_CREATION,
                description="Exploration session resumed"
            )
            self.session.add_action_log(resume_log)
            
            # Continue with exploration
            return self.start_exploration()
            
    def stop_exploration(self) -> Dict[str, Any]:
        """Stop the exploration process."""
        with self.lock:
            self.is_running = False
            self.session.update_status(SessionStatus.CANCELLED)
            
            self.browser_agent.close()
            
            stop_log = ActionLog(
                agent_role=None,
                action_type=ActionType.ERROR,
                description="Exploration session stopped by user"
            )
            self.session.add_action_log(stop_log)
            
            return {"success": True, "status": "cancelled"}
            
    def get_current_status(self) -> Dict[str, Any]:
        """Get the current status of the exploration."""
        return {
            "session_id": self.session.session_id,
            "is_running": self.is_running,
            "current_loop": self.current_loop,
            "completed_steps": self.completed_steps.copy(),
            "progress": {
                "current_step": self.session.current_step,
                "total_steps": self.session.total_steps,
                "percentage": self.session.progress_percentage
            },
            "agent_states": {
                "coordinator": {
                    "status": self.coordinator.state.status,
                    "current_task": self.coordinator.state.current_task,
                    "reasoning": self.coordinator.state.reasoning
                },
                "browser": {
                    "status": self.browser_agent.state.status,
                    "current_task": self.browser_agent.state.current_task,
                    "current_url": self.browser_agent.current_url
                },
                "analyst": {
                    "status": self.analyst_agent.state.status,
                    "current_task": self.analyst_agent.state.current_task,
                    "analyses_count": len(self.analyst_agent.analysis_results)
                }
            },
            "session": self.session.to_dict()
        }