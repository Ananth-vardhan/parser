"""Browser agent that handles navigation and DOM interactions using browser-use."""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional, Any

try:
    from browser_use import BrowserSession
except ImportError:
    BrowserSession = None

from app.models.exploration_session import (
    AgentRole, AgentState, ActionLog, ActionType, ScreenshotMetadata
)


class BrowserAgent:
    """Agent responsible for browser navigation and DOM interactions."""
    
    def __init__(self, session_id: str, browser_settings: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.session_id = session_id
        self.browser_settings = browser_settings
        self.logger = logger or logging.getLogger(__name__)
        self.state = AgentState(role=AgentRole.BROWSER)
        self.browser_session: Optional[BrowserSession] = None
        self.current_url = None
        self.page_title = None
        
    def initialize_browser(self) -> bool:
        """Initialize the browser session."""
        if BrowserSession is None:
            self.logger.warning("browser-use not available, running in stub mode")
            self.state.status = "stub_mode"
            return False
            
        try:
            viewport = {
                "width": self.browser_settings.get("viewport_width", 1280),
                "height": self.browser_settings.get("viewport_height", 720),
            }
            
            self.browser_session = BrowserSession(
                headless=self.browser_settings.get("headless", True),
                viewport=viewport,
                user_agent=self.browser_settings.get("user_agent"),
                env=self.browser_settings.get("extra_env"),
                profile_id=self.browser_settings.get("profile_id"),
                cloud_browser=self.browser_settings.get("use_cloud_browser"),
            )
            
            self.state.status = "initialized"
            self.state.reasoning = "Browser session initialized successfully"
            self.logger.info("Browser session initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            self.state.status = "error"
            self.state.reasoning = f"Failed to initialize browser: {str(e)}"
            return False
            
    def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a specific URL."""
        self.state.status = "navigating"
        self.state.current_task = f"navigate_to: {url}"
        
        if not self.browser_session:
            # Stub behavior for testing
            self.current_url = url
            self.page_title = f"Stub Page for {url}"
            self.state.reasoning = f"Stub navigation to {url}"
            self.logger.info(f"Stub navigation to {url}")
            
            return {
                "success": True,
                "url": url,
                "title": self.page_title,
                "stub_mode": True
            }
            
        try:
            # Use browser-use to navigate
            result = self.browser_session.navigate(url)
            self.current_url = url
            self.page_title = getattr(result, 'title', 'Unknown Title')
            
            self.state.status = "ready"
            self.state.reasoning = f"Successfully navigated to {url}"
            self.state.last_action = f"navigated_to:{url}"
            
            self.logger.info(f"Navigated to {url}")
            return {
                "success": True,
                "url": url,
                "title": self.page_title,
                "result": result
            }
            
        except Exception as e:
            self.state.status = "error"
            self.state.reasoning = f"Failed to navigate to {url}: {str(e)}"
            self.logger.error(f"Failed to navigate to {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
            
    def capture_screenshot(self, name: Optional[str] = None) -> Optional[ScreenshotMetadata]:
        """Capture a screenshot of the current page."""
        if not self.browser_session:
            # Stub screenshot
            return ScreenshotMetadata(
                url=self.current_url or "unknown",
                title=self.page_title,
                file_path=f"/tmp/stub_screenshot_{int(time.time())}.png",
                observations=["Stub screenshot captured"],
                dom_summary="Stub DOM summary"
            )
            
        try:
            # Capture screenshot using browser-use
            screenshot_result = self.browser_session.take_screenshot(
                full_page=True,
                path=f"/tmp/screenshot_{self.session_id}_{int(time.time())}.png"
            )
            
            screenshot = ScreenshotMetadata(
                url=self.current_url or "unknown",
                title=self.page_title,
                file_path=screenshot_result.get("path") if isinstance(screenshot_result, dict) else None,
                observations=["Screenshot captured successfully"],
                dom_summary="DOM analysis placeholder"  # Could be enhanced with actual DOM analysis
            )
            
            self.state.last_action = "captured_screenshot"
            self.logger.info("Screenshot captured successfully")
            return screenshot
            
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            self.state.status = "error"
            self.state.reasoning = f"Screenshot capture failed: {str(e)}"
            return None
            
    def query_dom(self, query: str) -> Dict[str, Any]:
        """Query the DOM for specific elements."""
        self.state.status = "querying_dom"
        self.state.current_task = f"dom_query: {query}"
        
        if not self.browser_session:
            # Stub DOM query
            return {
                "success": True,
                "query": query,
                "results": [
                    {"tag": "div", "text": "Stub element 1", "count": 1},
                    {"tag": "p", "text": "Stub element 2", "count": 2}
                ],
                "stub_mode": True
            }
            
        try:
            # Use browser-use to query DOM
            elements = self.browser_session.query_selector_all(query)
            
            results = []
            for element in elements:
                results.append({
                    "tag": getattr(element, 'tag_name', 'unknown'),
                    "text": getattr(element, 'text_content', ''),
                    "attributes": getattr(element, 'attributes', {}),
                    "visible": getattr(element, 'is_visible', False)
                })
                
            self.state.status = "ready"
            self.state.reasoning = f"DOM query '{query}' completed with {len(results)} results"
            self.state.last_action = f"dom_query:{query}"
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            self.state.status = "error"
            self.state.reasoning = f"DOM query '{query}' failed: {str(e)}"
            self.logger.error(f"DOM query failed: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
            
    def extract_data(self, selectors: List[str]) -> Dict[str, Any]:
        """Extract data from specified DOM selectors."""
        self.state.status = "extracting_data"
        self.state.current_task = f"extract_data: {selectors}"
        
        extracted_data = {}
        
        for selector in selectors:
            try:
                query_result = self.query_dom(selector)
                if query_result.get("success"):
                    extracted_data[selector] = query_result.get("results", [])
            except Exception as e:
                self.logger.error(f"Failed to extract data for selector {selector}: {e}")
                extracted_data[selector] = {"error": str(e)}
                
        self.state.status = "ready"
        self.state.reasoning = f"Data extraction completed for {len(selectors)} selectors"
        
        return {
            "success": True,
            "extracted_data": extracted_data,
            "selectors_processed": len(selectors)
        }
        
    def scroll_page(self, direction: str = "down", pixels: int = 500) -> Dict[str, Any]:
        """Scroll the page in a specified direction."""
        self.state.status = "scrolling"
        self.state.current_task = f"scroll_{direction}"
        
        if not self.browser_session:
            # Stub scroll
            return {
                "success": True,
                "direction": direction,
                "pixels": pixels,
                "stub_mode": True
            }
            
        try:
            # Use browser-use to scroll
            if direction.lower() == "down":
                self.browser_session.scroll_down(pixels)
            else:
                self.browser_session.scroll_up(pixels)
                
            self.state.status = "ready"
            self.state.reasoning = f"Page scrolled {direction} by {pixels} pixels"
            self.state.last_action = f"scrolled_{direction}"
            
            return {
                "success": True,
                "direction": direction,
                "pixels": pixels
            }
            
        except Exception as e:
            self.state.status = "error"
            self.state.reasoning = f"Scroll failed: {str(e)}"
            self.logger.error(f"Scroll failed: {e}")
            return {
                "success": False,
                "direction": direction,
                "error": str(e)
            }
            
    def get_current_page_info(self) -> Dict[str, Any]:
        """Get information about the current page state."""
        return {
            "url": self.current_url,
            "title": self.page_title,
            "browser_initialized": self.browser_session is not None,
            "status": self.state.status,
            "current_task": self.state.current_task
        }
        
    def close(self) -> None:
        """Clean up browser resources."""
        if self.browser_session:
            try:
                self.browser_session.close()
                self.logger.info("Browser session closed")
            except Exception as e:
                self.logger.error(f"Error closing browser session: {e}")
                
        self.state.status = "closed"
        
    def log_action(self, description: str, action_type: ActionType, 
                  reasoning: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ActionLog:
        """Create an action log entry for browser activities."""
        return ActionLog(
            agent_role=AgentRole.BROWSER,
            action_type=action_type,
            description=description,
            reasoning=reasoning,
            details=details or {}
        )