"""Scraper generation service with LLM-powered code generation and iterative refinement."""
from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.models import (
    GeneratedScraper,
    ScraperTestResult,
    GenerationStatus,
    TestStatus,
    ExplorationSession,
)


class ScraperGenerator:
    """Generates scraper code from exploration logs using LLMs."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", logger: Optional[logging.Logger] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger = logger or logging.getLogger(__name__)
    
    def generate_specification(self, session: ExplorationSession) -> str:
        """Transform exploration logs into a promptable specification."""
        self.logger.info(f"Generating specification for session {session.session_id}")
        
        spec_parts = [
            "# Web Scraper Specification",
            "",
            f"## Target URL",
            f"{session.url}",
            "",
            f"## Objectives",
            f"{session.objectives}",
            "",
            "## Exploration Findings",
            ""
        ]
        
        # Summarize action logs
        if session.action_logs:
            spec_parts.append("### Actions Performed")
            for log in session.action_logs[-20:]:  # Last 20 actions
                if log.action_type:
                    spec_parts.append(f"- {log.action_type.value}: {log.description}")
                    if log.result:
                        spec_parts.append(f"  Result: {log.result}")
            spec_parts.append("")
        
        # Summarize screenshots
        if session.screenshots:
            spec_parts.append("### Page Structure Observations")
            for screenshot in session.screenshots[-5:]:  # Last 5 screenshots
                if screenshot.observations:
                    spec_parts.extend([f"- {obs}" for obs in screenshot.observations])
                if screenshot.dom_summary:
                    spec_parts.append(f"- DOM: {screenshot.dom_summary}")
            spec_parts.append("")
        
        # Extract agent insights
        if session.analyst_state and session.analyst_state.reasoning:
            spec_parts.append("### Analysis")
            spec_parts.append(session.analyst_state.reasoning)
            spec_parts.append("")
        
        specification = "\n".join(spec_parts)
        self.logger.debug(f"Generated specification:\n{specification}")
        
        return specification
    
    def generate_scraper_code(
        self,
        specification: str,
        session: ExplorationSession,
        feedback: Optional[str] = None,
        previous_code: Optional[str] = None,
        previous_errors: Optional[List[str]] = None
    ) -> GeneratedScraper:
        """Generate scraper code using LLM with optional refinement."""
        self.logger.info(f"Generating scraper code for session {session.session_id}")
        
        scraper = GeneratedScraper(
            session_id=session.session_id,
            specification=specification,
            framework="playwright",
            language="python"
        )
        
        scraper.update_status(GenerationStatus.IN_PROGRESS)
        
        # Build generation prompt
        prompt = self._build_generation_prompt(
            specification,
            session,
            feedback,
            previous_code,
            previous_errors
        )
        
        scraper.generation_prompt = prompt
        scraper.model_used = self.model
        
        try:
            # Call LLM for code generation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert web scraping engineer. Generate production-ready Playwright Python scraper code based on specifications."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            generated_code = response.choices[0].message.content
            
            # Extract code from markdown if present
            if "```python" in generated_code:
                code_start = generated_code.find("```python") + 9
                code_end = generated_code.find("```", code_start)
                generated_code = generated_code[code_start:code_end].strip()
            elif "```" in generated_code:
                code_start = generated_code.find("```") + 3
                code_end = generated_code.find("```", code_start)
                generated_code = generated_code[code_start:code_end].strip()
            
            scraper.code = generated_code
            scraper.update_status(GenerationStatus.COMPLETED)
            
            # Extract dependencies
            scraper.dependencies = self._extract_dependencies(generated_code)
            
            # Generate README
            scraper.readme = self._generate_readme(specification, session)
            
            self.logger.info(f"Successfully generated scraper code (version {scraper.version})")
            
        except Exception as e:
            self.logger.error(f"Failed to generate scraper code: {e}")
            scraper.update_status(GenerationStatus.FAILED)
            scraper.generation_errors.append(str(e))
        
        return scraper
    
    def _build_generation_prompt(
        self,
        specification: str,
        session: ExplorationSession,
        feedback: Optional[str],
        previous_code: Optional[str],
        previous_errors: Optional[List[str]]
    ) -> str:
        """Build the LLM prompt for code generation."""
        prompt_parts = [
            "Generate a complete, production-ready web scraper using Playwright (Python) based on the following specification:",
            "",
            specification,
            "",
            "Requirements:",
            "- Use async Playwright with proper context management",
            "- Include comprehensive error handling",
            "- Add logging for debugging",
            "- Return structured data as JSON",
            "- Include docstrings and type hints",
            "- Handle dynamic content loading with appropriate waits",
            "- Make the scraper configurable via command-line arguments",
            "",
            "The scraper should be a complete, runnable Python script that can be executed standalone.",
        ]
        
        if previous_code and previous_errors:
            prompt_parts.extend([
                "",
                "IMPORTANT: This is a refinement iteration. The previous version had issues:",
                ""
            ])
            for error in previous_errors[-3:]:  # Last 3 errors
                prompt_parts.append(f"- {error}")
            
            prompt_parts.extend([
                "",
                "Previous code:",
                "```python",
                previous_code,
                "```",
                "",
                "Please fix the issues identified above.",
            ])
        
        if feedback:
            prompt_parts.extend([
                "",
                "User feedback:",
                feedback,
                "",
                "Please incorporate this feedback into the scraper.",
            ])
        
        return "\n".join(prompt_parts)
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """Extract Python dependencies from generated code."""
        dependencies = ["playwright"]
        
        # Common imports to dependency mapping
        import_to_dep = {
            "import requests": "requests",
            "from requests": "requests",
            "import beautifulsoup4": "beautifulsoup4",
            "from bs4": "beautifulsoup4",
            "import pandas": "pandas",
            "import numpy": "numpy",
            "import selenium": "selenium",
        }
        
        for import_stmt, dep in import_to_dep.items():
            if import_stmt in code and dep not in dependencies:
                dependencies.append(dep)
        
        return dependencies
    
    def _generate_readme(self, specification: str, session: ExplorationSession) -> str:
        """Generate README documentation for the scraper."""
        readme_parts = [
            "# Web Scraper",
            "",
            f"Generated for: {session.url}",
            "",
            "## Description",
            "",
            session.objectives,
            "",
            "## Installation",
            "",
            "```bash",
            "pip install playwright",
            "playwright install chromium",
            "```",
            "",
            "## Usage",
            "",
            "```bash",
            "python scraper.py",
            "```",
            "",
            "## Output",
            "",
            "The scraper will output structured JSON data to stdout.",
            "",
            "## Specification",
            "",
            specification,
        ]
        
        return "\n".join(readme_parts)
    
    def refine_scraper(
        self,
        scraper: GeneratedScraper,
        session: ExplorationSession,
        test_result: ScraperTestResult,
        feedback: Optional[str] = None
    ) -> GeneratedScraper:
        """Refine scraper based on test results and feedback."""
        self.logger.info(f"Refining scraper {scraper.scraper_id} (version {scraper.version})")
        
        if scraper.iteration_count >= scraper.max_iterations:
            self.logger.warning(f"Max iterations reached for scraper {scraper.scraper_id}")
            scraper.generation_errors.append("Maximum iteration limit reached")
            scraper.update_status(GenerationStatus.FAILED)
            return scraper
        
        # Collect errors from test result
        errors = []
        if test_result.error_message:
            errors.append(test_result.error_message)
        if test_result.stack_trace:
            errors.append(f"Stack trace: {test_result.stack_trace}")
        for assertion in test_result.assertion_details:
            if not assertion.get("passed", False):
                errors.append(f"Assertion failed: {assertion.get('description', 'unknown')}")
        
        scraper.generation_errors.extend(errors)
        
        # Generate refined version
        refined_scraper = self.generate_scraper_code(
            scraper.specification,
            session,
            feedback=feedback,
            previous_code=scraper.code,
            previous_errors=errors
        )
        
        # Update version tracking
        refined_scraper.version = scraper.version + 1
        refined_scraper.iteration_count = scraper.iteration_count + 1
        refined_scraper.scraper_id = scraper.scraper_id  # Keep same ID
        refined_scraper.test_results = scraper.test_results  # Preserve history
        
        return refined_scraper
