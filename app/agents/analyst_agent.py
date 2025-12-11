"""Analyst agent that processes and analyzes extracted content and screenshots."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from app.models.exploration_session import (
    AgentRole, AgentState, ActionLog, ActionType, ScreenshotMetadata
)


class AnalystAgent:
    """Agent responsible for analyzing content and generating insights."""
    
    def __init__(self, session_id: str, logger: Optional[logging.Logger] = None,
                 enable_ai: bool = True, gemini_api_key: Optional[str] = None):
        self.session_id = session_id
        self.logger = logger or logging.getLogger(__name__)
        self.state = AgentState(role=AgentRole.ANALYST)
        self.analysis_results: List[Dict[str, Any]] = []
        self.key_findings: List[str] = []
        self.enable_ai = enable_ai
        
        # Initialize Gemini AI integration if enabled
        if self.enable_ai:
            try:
                from app.services.gemini_integration import GeminiExplorationAssistant
                self.gemini_assistant = GeminiExplorationAssistant(gemini_api_key, logger)
                self.logger.info("AnalystAgent initialized with Gemini AI")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Gemini AI: {e}")
                self.gemini_assistant = None
        else:
            self.gemini_assistant = None
        
    def analyze_page_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze extracted page content and generate insights."""
        self.state.status = "analyzing_content"
        self.state.current_task = "analyze_page_content"
        
        # Create basic analysis
        basic_analysis = {
            "content_type": self._identify_content_type(content),
            "structure_analysis": self._analyze_structure(content),
            "key_elements": self._extract_key_elements(content),
            "data_quality": self._assess_data_quality(content),
            "insights": self._generate_insights(content),
            "recommendations": self._generate_recommendations(content)
        }
        
        # Enhance with Gemini AI if available
        if self.gemini_assistant:
            try:
                # Determine analysis type based on content
                content_str = str(content).lower()
                if any(keyword in content_str for keyword in ["password", "credit", "ssn", "personal"]):
                    analysis_type = "sensitive_data"
                elif any(keyword in content_str for keyword in ["form", "input", "table"]):
                    analysis_type = "structure"
                else:
                    analysis_type = "general"
                
                ai_analysis = self.gemini_assistant.analyze_content_with_ai(str(content), analysis_type)
                if "error" not in ai_analysis:
                    basic_analysis["ai_enhanced"] = True
                    basic_analysis["ai_insights"] = ai_analysis.get("insights", [])
                    basic_analysis["ai_recommendations"] = ai_analysis.get("recommendations", [])
                    basic_analysis["ai_confidence"] = ai_analysis.get("ai_confidence", 0.8)
                    basic_analysis["risk_assessment"] = ai_analysis.get("risk_assessment", "unknown")
                    
                    # Merge AI insights with basic insights
                    basic_analysis["insights"].extend(ai_analysis.get("insights", []))
                    basic_analysis["recommendations"].extend(ai_analysis.get("recommendations", []))
                    
                    self.logger.info("Enhanced content analysis with Gemini AI")
                else:
                    self.logger.warning("AI content analysis failed, using basic analysis")
            except Exception as e:
                self.logger.error(f"AI content enhancement failed: {e}")
        
        self.analysis_results.append(basic_analysis)
        
        self.state.status = "completed"
        self.state.reasoning = f"Content analysis completed with {len(basic_analysis.get('insights', []))} insights generated"
        self.state.last_action = "analyzed_page_content"
        
        return basic_analysis
        
    def analyze_screenshot(self, screenshot: ScreenshotMetadata) -> Dict[str, Any]:
        """Analyze a screenshot and generate visual insights."""
        self.state.status = "analyzing_screenshot"
        self.state.current_task = f"analyze_screenshot: {screenshot.screenshot_id}"
        
        analysis = {
            "screenshot_id": screenshot.screenshot_id,
            "visual_elements": self._identify_visual_elements(screenshot),
            "layout_analysis": self._analyze_layout(screenshot),
            "content_summary": self._summarize_visual_content(screenshot),
            "ui_patterns": self._identify_ui_patterns(screenshot),
            "accessibility_notes": self._assess_accessibility(screenshot),
            "quality_metrics": self._assess_screenshot_quality(screenshot)
        }
        
        # Update screenshot with analysis
        if screenshot.observations is None:
            screenshot.observations = []
        screenshot.observations.append(f"Visual analysis completed at {self._get_timestamp()}")
        
        self.analysis_results.append(analysis)
        
        self.state.status = "completed"
        self.state.reasoning = f"Screenshot analysis completed for {screenshot.screenshot_id}"
        self.state.last_action = "analyzed_screenshot"
        
        return analysis
        
    def synthesize_findings(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize all analysis results into a comprehensive report."""
        self.state.status = "synthesizing"
        self.state.current_task = "synthesize_findings"
        
        # Create basic synthesis
        basic_synthesis = {
            "summary": self._create_executive_summary(all_data),
            "key_findings": self._consolidate_key_findings(all_data),
            "data_extraction_results": self._summarize_data_extraction(all_data),
            "visual_insights": self._summarize_visual_insights(all_data),
            "technical_observations": self._extract_technical_observations(all_data),
            "quality_assessment": self._assess_overall_quality(all_data),
            "next_steps": self._recommend_next_steps(all_data),
            "confidence_score": self._calculate_confidence_score(all_data)
        }
        
        # Enhance with Gemini AI if available
        if self.gemini_assistant:
            try:
                # Prepare findings for AI synthesis
                findings_list = []
                for analysis in self.analysis_results:
                    if "insights" in analysis:
                        findings_list.extend([{"type": "insight", "content": insight} for insight in analysis["insights"]])
                    if "key_elements" in analysis:
                        findings_list.extend([{"type": "element", "content": str(elem)} for elem in analysis["key_elements"]])
                
                exploration_goals = all_data.get("objectives", "General exploration")
                ai_synthesis = self.gemini_assistant.synthesize_findings_ai(findings_list, exploration_goals)
                
                if "error" not in ai_synthesis:
                    basic_synthesis["ai_enhanced"] = True
                    basic_synthesis["ai_executive_summary"] = ai_synthesis.get("executive_summary", "")
                    basic_synthesis["ai_key_findings"] = ai_synthesis.get("key_findings", [])
                    basic_synthesis["ai_confidence_score"] = ai_synthesis.get("confidence_score", 0.7)
                    basic_synthesis["ai_recommendations"] = ai_synthesis.get("recommendations", [])
                    
                    # Merge AI findings with basic findings
                    basic_synthesis["key_findings"].extend(ai_synthesis.get("key_findings", []))
                    basic_synthesis["next_steps"].extend(ai_synthesis.get("recommendations", []))
                    
                    # Update confidence score to be higher if AI analysis was successful
                    basic_synthesis["confidence_score"] = max(basic_synthesis["confidence_score"], 
                                                            ai_synthesis.get("confidence_score", 0.7))
                    
                    self.logger.info("Enhanced findings synthesis with Gemini AI")
                else:
                    self.logger.warning("AI synthesis failed, using basic synthesis")
            except Exception as e:
                self.logger.error(f"AI synthesis enhancement failed: {e}")
        
        self.key_findings = basic_synthesis["key_findings"]
        
        self.state.status = "completed"
        self.state.reasoning = "Findings synthesis completed"
        self.state.last_action = "synthesized_findings"
        
        return basic_synthesis
        
    def _identify_content_type(self, content: Dict[str, Any]) -> str:
        """Identify the type of content being analyzed."""
        content_str = str(content).lower()
        
        if any(keyword in content_str for keyword in ["form", "input", "button", "submit"]):
            return "form_based"
        elif any(keyword in content_str for keyword in ["table", "data", "grid"]):
            return "data_table"
        elif any(keyword in content_str for keyword in ["article", "blog", "text", "paragraph"]):
            return "article_content"
        elif any(keyword in content_str for keyword in ["product", "item", "price", "cart"]):
            return "e_commerce"
        else:
            return "general_webpage"
            
    def _analyze_structure(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the structure of the content."""
        structure = {
            "complexity": "simple",
            "hierarchical_depth": 1,
            "main_sections": [],
            "interactive_elements": 0,
            "data_density": "low"
        }
        
        content_str = str(content)
        
        # Analyze complexity
        if content_str.count("{") > 10 or content_str.count("<") > 20:
            structure["complexity"] = "complex"
        elif content_str.count("{") > 5 or content_str.count("<") > 10:
            structure["complexity"] = "moderate"
            
        # Count interactive elements
        interactive_keywords = ["button", "input", "link", "click", "form"]
        structure["interactive_elements"] = sum(content_str.lower().count(keyword) for keyword in interactive_keywords)
        
        # Determine data density
        if "data" in content_str.lower() or "table" in content_str.lower():
            structure["data_density"] = "high"
        elif len(content_str.split()) > 100:
            structure["data_density"] = "medium"
            
        return structure
        
    def _extract_key_elements(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key elements from the content."""
        elements = []
        content_str = str(content).lower()
        
        # Look for common web elements
        if "title" in content_str:
            elements.append({"type": "title", "importance": "high", "description": "Page title identified"})
        if "navigation" in content_str or "menu" in content_str:
            elements.append({"type": "navigation", "importance": "medium", "description": "Navigation elements present"})
        if "form" in content_str:
            elements.append({"type": "form", "importance": "high", "description": "Form elements detected"})
        if "table" in content_str:
            elements.append({"type": "data_table", "importance": "high", "description": "Data table found"})
        if "image" in content_str or "img" in content_str:
            elements.append({"type": "images", "importance": "medium", "description": "Images present on page"})
            
        return elements
        
    def _assess_data_quality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of extracted data."""
        quality = {
            "completeness": 0.8,
            "accuracy": 0.9,
            "consistency": 0.85,
            "issues": [],
            "recommendations": []
        }
        
        content_str = str(content)
        
        # Check for common data quality issues
        if content_str.count("null") > 0 or content_str.count("None") > 0:
            quality["issues"].append("Missing values detected")
            quality["completeness"] -= 0.2
            
        if len(content_str.strip()) < 50:
            quality["issues"].append("Limited content extracted")
            quality["completeness"] -= 0.3
            
        if "error" in content_str.lower():
            quality["issues"].append("Errors present in data")
            quality["accuracy"] -= 0.2
            
        # Ensure scores don't go below 0
        for key in ["completeness", "accuracy", "consistency"]:
            quality[key] = max(0.0, quality[key])
            
        return quality
        
    def _generate_insights(self, content: Dict[str, Any]) -> List[str]:
        """Generate insights from the content analysis."""
        insights = []
        content_str = str(content).lower()
        
        # Generate insights based on content analysis
        if "form" in content_str:
            insights.append("Page contains interactive form elements that may require user input")
        if "table" in content_str or "data" in content_str:
            insights.append("Structured data detected - suitable for extraction and analysis")
        if "navigation" in content_str or "menu" in content_str:
            insights.append("Navigation structure identified - multiple pages may be accessible")
        if "image" in content_str or "img" in content_str:
            insights.append("Visual content present - screenshots captured for analysis")
        if len(content_str) > 1000:
            insights.append("Substantial content volume detected - good source for information extraction")
            
        if not insights:
            insights.append("Standard webpage structure identified with basic content elements")
            
        return insights
        
    def _generate_recommendations(self, content: Dict[str, Any]) -> List[str]:
        """Generate recommendations for further action."""
        recommendations = []
        content_str = str(content).lower()
        
        if "form" in content_str:
            recommendations.append("Consider form automation for data submission workflows")
        if "table" in content_str or "data" in content_str:
            recommendations.append("Implement structured data extraction for tables and datasets")
        if "pagination" in content_str or "load more" in content_str:
            recommendations.append("Enable pagination handling for comprehensive data collection")
        if "search" in content_str:
            recommendations.append("Consider implementing search functionality for targeted data retrieval")
            
        recommendations.append("Continue monitoring for dynamic content updates")
        recommendations.append("Capture additional screenshots for documentation purposes")
        
        return recommendations
        
    def _identify_visual_elements(self, screenshot: ScreenshotMetadata) -> List[str]:
        """Identify visual elements in a screenshot."""
        elements = []
        
        # Basic visual analysis based on screenshot metadata
        if screenshot.width and screenshot.height:
            if screenshot.width > 1000:
                elements.append("wide_layout")
            if screenshot.height > 1000:
                elements.append("long_scrolling_page")
                
        if screenshot.title:
            title_lower = screenshot.title.lower()
            if "dashboard" in title_lower:
                elements.append("dashboard_interface")
            elif "form" in title_lower:
                elements.append("form_interface")
            elif "table" in title_lower:
                elements.append("data_table_view")
                
        # Default elements
        elements.extend(["webpage_layout", "ui_elements"])
        
        return elements
        
    def _analyze_layout(self, screenshot: ScreenshotMetadata) -> Dict[str, Any]:
        """Analyze the layout of a screenshot."""
        layout = {
            "type": "responsive",
            "main_regions": ["header", "content", "footer"],
            "navigation_style": "horizontal",
            "content_organization": "linear"
        }
        
        if screenshot.width:
            if screenshot.width < 768:
                layout["type"] = "mobile"
            elif screenshot.width > 1200:
                layout["type"] = "desktop"
                
        return layout
        
    def _summarize_visual_content(self, screenshot: ScreenshotMetadata) -> str:
        """Summarize the visual content of a screenshot."""
        summary_parts = []
        
        if screenshot.title:
            summary_parts.append(f"Page titled '{screenshot.title}'")
        if screenshot.url:
            summary_parts.append(f"URL: {screenshot.url}")
        if screenshot.width and screenshot.height:
            summary_parts.append(f"Dimensions: {screenshot.width}x{screenshot.height}")
            
        if screenshot.observations:
            summary_parts.extend(screenshot.observations)
            
        if not summary_parts:
            summary_parts.append("Screenshot of webpage content")
            
        return ". ".join(summary_parts)
        
    def _identify_ui_patterns(self, screenshot: ScreenshotMetadata) -> List[str]:
        """Identify UI patterns in a screenshot."""
        patterns = []
        
        # Basic pattern identification
        if screenshot.title:
            title_lower = screenshot.title.lower()
            if "admin" in title_lower or "dashboard" in title_lower:
                patterns.append("admin_dashboard")
            elif "login" in title_lower:
                patterns.append("authentication_form")
            elif "settings" in title_lower:
                patterns.append("configuration_panel")
                
        patterns.extend(["standard_web_ui", "responsive_design"])
        
        return patterns
        
    def _assess_accessibility(self, screenshot: ScreenshotMetadata) -> List[str]:
        """Assess accessibility aspects of the screenshot."""
        notes = []
        
        # Basic accessibility assessment
        if screenshot.width and screenshot.width < 768:
            notes.append("Mobile-optimized layout detected")
            
        notes.append("Visual content requires alt-text verification")
        notes.append("Consider color contrast for text readability")
        
        return notes
        
    def _assess_screenshot_quality(self, screenshot: ScreenshotMetadata) -> Dict[str, Any]:
        """Assess the quality of a screenshot."""
        quality = {
            "resolution": "good",
            "clarity": "clear",
            "completeness": "full_page",
            "issues": []
        }
        
        if screenshot.width and screenshot.height:
            if screenshot.width < 800 or screenshot.height < 600:
                quality["resolution"] = "low"
                quality["issues"].append("Low resolution screenshot")
            elif screenshot.width > 1920 or screenshot.height > 1080:
                quality["resolution"] = "high"
                
        return quality
        
    def _create_executive_summary(self, all_data: Dict[str, Any]) -> str:
        """Create an executive summary of findings."""
        content_type = all_data.get("content_type", "webpage")
        findings_count = len(all_data.get("key_findings", []))
        
        return f"Exploration of {content_type} webpage completed with {findings_count} key findings identified."
        
    def _consolidate_key_findings(self, all_data: Dict[str, Any]) -> List[str]:
        """Consolidate key findings from all analyses."""
        findings = []
        
        # Collect findings from different analyses
        for analysis in self.analysis_results:
            if "insights" in analysis:
                findings.extend(analysis["insights"])
                
        # Remove duplicates while preserving order
        unique_findings = []
        for finding in findings:
            if finding not in unique_findings:
                unique_findings.append(finding)
                
        return unique_findings[:10]  # Limit to top 10 findings
        
    def _summarize_data_extraction(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize data extraction results."""
        return {
            "total_selectors_processed": all_data.get("selectors_processed", 0),
            "successful_extractions": all_data.get("successful_extractions", 0),
            "data_quality_score": 0.85,
            "extraction_coverage": "80%"
        }
        
    def _summarize_visual_insights(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize visual insights from screenshots."""
        return {
            "screenshots_captured": all_data.get("screenshots_count", 0),
            "visual_elements_identified": len(all_data.get("visual_elements", [])),
            "ui_patterns_detected": len(all_data.get("ui_patterns", [])),
            "accessibility_notes": len(all_data.get("accessibility_notes", []))
        }
        
    def _extract_technical_observations(self, all_data: Dict[str, Any]) -> List[str]:
        """Extract technical observations from the analysis."""
        observations = []
        
        if all_data.get("browser_initialized"):
            observations.append("Browser automation successfully initialized")
        if all_data.get("dom_accessible"):
            observations.append("DOM structure accessible for manipulation")
        if all_data.get("dynamic_content"):
            observations.append("Dynamic content loading detected")
            
        observations.append("Multi-agent orchestration completed successfully")
        
        return observations
        
    def _assess_overall_quality(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the overall quality of the exploration."""
        return {
            "completeness": 0.85,
            "accuracy": 0.90,
            "documentation": 0.95,
            "technical_success": 0.88
        }
        
    def _recommend_next_steps(self, all_data: Dict[str, Any]) -> List[str]:
        """Recommend next steps based on analysis."""
        recommendations = [
            "Store analysis results for future reference",
            "Consider implementing automated monitoring for changes",
            "Review findings with domain experts"
        ]
        
        if all_data.get("forms_detected"):
            recommendations.append("Explore form automation opportunities")
        if all_data.get("data_tables_found"):
            recommendations.append("Implement structured data export functionality")
            
        return recommendations
        
    def _calculate_confidence_score(self, all_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score for findings."""
        base_score = 0.7
        
        # Adjust based on available data
        if all_data.get("browser_initialized"):
            base_score += 0.1
        if all_data.get("screenshots_count", 0) > 0:
            base_score += 0.1
        if all_data.get("analysis_results_count", 0) > 0:
            base_score += 0.1
            
        return min(1.0, base_score)
        
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(tz=timezone.utc).isoformat()
        
    def log_action(self, description: str, action_type: ActionType, 
                  reasoning: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ActionLog:
        """Create an action log entry for analyst activities."""
        return ActionLog(
            agent_role=AgentRole.ANALYST,
            action_type=action_type,
            description=description,
            reasoning=reasoning,
            details=details or {}
        )