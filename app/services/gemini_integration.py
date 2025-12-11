"""Enhanced Gemini integration for the exploration orchestrator."""
import os
import logging
from typing import Any, Dict, List, Optional
import google.generativeai as genai

from app.models.exploration_session import ActionLog, AgentRole, ActionType


class GeminiExplorationAssistant:
    """Enhanced exploration assistant using Google's Gemini AI."""
    
    def __init__(self, api_key: Optional[str] = None, logger: Optional[logging.Logger] = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.logger = logger or logging.getLogger(__name__)
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.logger.info("Gemini AI initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini AI: {e}")
                self.model = None
        else:
            self.logger.warning("No Gemini API key provided")
    
    def generate_exploration_plan(self, url: str, objectives: str, current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a detailed exploration plan using Gemini AI."""
        if not self.model:
            return {"error": "Gemini AI not available"}
        
        try:
            prompt = f"""
            You are an expert web exploration coordinator. Create a detailed plan for exploring the following webpage:
            
            URL: {url}
            Objectives: {objectives}
            Current Context: {current_context or 'None provided'}
            
            Please provide a structured exploration plan in JSON format with:
            1. A brief strategy summary
            2. Numbered steps with descriptions and purposes
            3. Expected challenges or considerations
            4. Success criteria for the exploration
            
            Format your response as valid JSON only.
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse the AI-generated plan
            import json
            try:
                plan_data = json.loads(response.text)
                return {
                    "strategy": plan_data.get("strategy", f"AI-generated plan for {url}"),
                    "steps": plan_data.get("steps", []),
                    "challenges": plan_data.get("challenges", []),
                    "success_criteria": plan_data.get("success_criteria", []),
                    "ai_generated": True,
                    "confidence": 0.9
                }
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                return {
                    "strategy": "AI-generated exploration plan",
                    "steps": [{"step": 1, "description": "AI-generated step", "purpose": "AI analysis"}],
                    "ai_generated": True,
                    "confidence": 0.7,
                    "raw_response": response.text
                }
                
        except Exception as e:
            self.logger.error(f"Failed to generate AI plan: {e}")
            return {"error": f"AI planning failed: {str(e)}"}
    
    def analyze_content_with_ai(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Use Gemini AI to analyze extracted content."""
        if not self.model:
            return {"error": "Gemini AI not available"}
        
        try:
            if analysis_type == "sensitive_data":
                prompt = f"""
                Analyze the following webpage content for sensitive data, PII, or security concerns:
                
                {content[:2000]}  # Limit content length for API efficiency
                
                Identify:
                1. Any sensitive personal information
                2. Security vulnerabilities or concerns
                3. Data protection recommendations
                
                Respond in JSON format.
                """
            elif analysis_type == "structure":
                prompt = f"""
                Analyze the structure and layout of the following webpage content:
                
                {content[:2000]}
                
                Identify:
                1. Page type and layout
                2. Key structural elements
                3. Navigation patterns
                4. Content organization
                
                Respond in JSON format.
                """
            else:  # general analysis
                prompt = f"""
                Provide a comprehensive analysis of the following webpage content:
                
                {content[:2000]}
                
                Analyze:
                1. Content type and purpose
                2. Key information and insights
                3. Important data points
                4. Recommendations for extraction
                
                Respond in JSON format.
                """
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            import json
            try:
                analysis = json.loads(response.text)
                return {
                    "analysis_type": analysis_type,
                    "insights": analysis.get("insights", []),
                    "recommendations": analysis.get("recommendations", []),
                    "risk_assessment": analysis.get("risk_assessment", "unknown"),
                    "content_summary": analysis.get("summary", ""),
                    "ai_confidence": 0.85,
                    "processed_with_ai": True
                }
            except json.JSONDecodeError:
                return {
                    "analysis_type": analysis_type,
                    "raw_analysis": response.text,
                    "ai_confidence": 0.6,
                    "processed_with_ai": True
                }
                
        except Exception as e:
            self.logger.error(f"AI content analysis failed: {e}")
            return {"error": f"AI analysis failed: {str(e)}"}
    
    def generate_step_reasoning(self, step_description: str, current_state: Dict[str, Any], 
                              agent_context: str) -> str:
        """Generate AI reasoning for why a specific step should be taken."""
        if not self.model:
            return f"Standard reasoning for: {step_description}"
        
        try:
            prompt = f"""
            As an expert exploration coordinator, explain why the following step should be taken:
            
            Step: {step_description}
            Current State: {current_state}
            Agent Context: {agent_context}
            
            Provide a clear, concise explanation in 2-3 sentences of the reasoning and expected outcomes.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"AI reasoning generation failed: {e}")
            return f"Standard reasoning for: {step_description}"
    
    def synthesize_findings_ai(self, all_findings: List[Dict[str, Any]], exploration_goals: str) -> Dict[str, Any]:
        """Use Gemini AI to synthesize all exploration findings into a comprehensive report."""
        if not self.model:
            return {"error": "Gemini AI not available"}
        
        try:
            # Prepare findings summary for AI
            findings_summary = "\n".join([
                f"- {finding.get('type', 'Unknown')}: {finding.get('content', 'No content')}"
                for finding in all_findings[:20]  # Limit for API efficiency
            ])
            
            prompt = f"""
            You are an expert data analyst. Synthesize the following exploration findings into a comprehensive report:
            
            Exploration Goals: {exploration_goals}
            
            Findings Summary:
            {findings_summary}
            
            Provide a structured analysis in JSON format with:
            1. Executive summary
            2. Key findings and insights
            3. Data quality assessment
            4. Recommendations for next steps
            5. Confidence score (0.0-1.0)
            
            Respond in JSON format only.
            """
            
            response = self.model.generate_content(prompt)
            
            import json
            try:
                synthesis = json.loads(response.text)
                return {
                    "executive_summary": synthesis.get("executive_summary", ""),
                    "key_findings": synthesis.get("key_findings", []),
                    "data_quality": synthesis.get("data_quality", "unknown"),
                    "recommendations": synthesis.get("recommendations", []),
                    "confidence_score": synthesis.get("confidence_score", 0.5),
                    "ai_synthesized": True
                }
            except json.JSONDecodeError:
                return {
                    "executive_summary": "AI-generated synthesis",
                    "raw_synthesis": response.text,
                    "ai_synthesized": True,
                    "confidence_score": 0.6
                }
                
        except Exception as e:
            self.logger.error(f"AI synthesis failed: {e}")
            return {"error": f"AI synthesis failed: {str(e)}"}
    
    def improve_agent_reasoning(self, agent_role: str, current_task: str, 
                              available_actions: List[str]) -> Dict[str, Any]:
        """Use Gemini AI to improve agent decision making."""
        if not self.model:
            return {"error": "Gemini AI not available"}
        
        try:
            prompt = f"""
            As an expert AI agent coordinator, help optimize the decision making for a {agent_role} agent:
            
            Current Task: {current_task}
            Available Actions: {', '.join(available_actions)}
            
            Provide guidance in JSON format with:
            1. Recommended action and reasoning
            2. Alternative approaches to consider
            3. Potential risks or considerations
            4. Expected outcomes
            
            Respond in JSON format only.
            """
            
            response = self.model.generate_content(prompt)
            
            import json
            try:
                guidance = json.loads(response.text)
                return {
                    "recommended_action": guidance.get("recommended_action", ""),
                    "reasoning": guidance.get("reasoning", ""),
                    "alternatives": guidance.get("alternatives", []),
                    "risks": guidance.get("risks", []),
                    "ai_optimized": True
                }
            except json.JSONDecodeError:
                return {
                    "raw_guidance": response.text,
                    "ai_optimized": True
                }
                
        except Exception as e:
            self.logger.error(f"AI agent optimization failed: {e}")
            return {"error": f"AI optimization failed: {str(e)}"}


# Integration helper for existing agents
class GeminiEnhancedCoordinator:
    """Enhanced coordinator agent with Gemini AI capabilities."""
    
    def __init__(self, session_id: str, gemini_api_key: Optional[str] = None):
        from app.agents.coordinator_agent import CoordinatorAgent
        self.coordinator = CoordinatorAgent(session_id)
        self.gemini = GeminiExplorationAssistant(gemini_api_key)
    
    def create_ai_enhanced_plan(self, url: str, objectives: str) -> Dict[str, Any]:
        """Create a plan enhanced with AI insights."""
        # Get basic plan
        basic_plan = self.coordinator.create_exploration_plan(url, objectives)
        
        # Enhance with AI
        ai_plan = self.gemini.generate_exploration_plan(url, objectives, basic_plan)
        
        if "error" not in ai_plan:
            # Merge AI insights with basic plan
            basic_plan["ai_strategy"] = ai_plan["strategy"]
            basic_plan["ai_challenges"] = ai_plan["challenges"]
            basic_plan["ai_confidence"] = ai_plan["confidence"]
            basic_plan["steps"].extend(ai_plan["steps"])
        
        return basic_plan


# Integration helper for analyst agent
class GeminiEnhancedAnalyst:
    """Enhanced analyst agent with Gemini AI capabilities."""
    
    def __init__(self, session_id: str, gemini_api_key: Optional[str] = None):
        from app.agents.analyst_agent import AnalystAgent
        self.analyst = AnalystAgent(session_id)
        self.gemini = GeminiExplorationAssistant(gemini_api_key)
    
    def analyze_content_with_ai(self, content: Dict[str, Any], analysis_type: str = "general") -> Dict[str, Any]:
        """Enhanced content analysis with AI."""
        # Get basic analysis
        basic_analysis = self.analyst.analyze_page_content(content)
        
        # Enhance with AI
        ai_analysis = self.gemini.analyze_content_with_ai(str(content), analysis_type)
        
        if "error" not in ai_analysis:
            basic_analysis["ai_insights"] = ai_analysis["insights"]
            basic_analysis["ai_recommendations"] = ai_analysis["recommendations"]
            basic_analysis["ai_confidence"] = ai_analysis["ai_confidence"]
        
        return basic_analysis
    
    def synthesize_findings_with_ai(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced findings synthesis with AI."""
        # Get basic synthesis
        basic_synthesis = self.analyst.synthesize_findings(all_data)
        
        # Enhance with AI
        findings_list = [
            {"type": "content", "content": all_data.get("content_type", "")},
            {"type": "data", "content": str(all_data.get("data_extracted", {}))},
            {"type": "screenshots", "content": f"{all_data.get('screenshots_captured', [])}"}
        ]
        
        ai_synthesis = self.gemini.synthesize_findings_ai(
            findings_list, 
            all_data.get("objectives", "General exploration")
        )
        
        if "error" not in ai_synthesis:
            basic_synthesis["ai_summary"] = ai_synthesis["executive_summary"]
            basic_synthesis["ai_key_findings"] = ai_synthesis["key_findings"]
            basic_synthesis["ai_confidence"] = ai_synthesis["confidence_score"]
        
        return basic_synthesis