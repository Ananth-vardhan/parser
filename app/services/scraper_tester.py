"""Testing harness for generated scrapers with configurable assertions."""
from __future__ import annotations

import asyncio
import logging
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models import GeneratedScraper, ScraperTestResult, TestStatus


class ScraperTester:
    """Test generated scrapers with assertions and snapshot capture."""
    
    def __init__(
        self,
        target_url: str,
        logger: Optional[logging.Logger] = None,
        timeout_seconds: int = 60
    ):
        self.target_url = target_url
        self.logger = logger or logging.getLogger(__name__)
        self.timeout_seconds = timeout_seconds
    
    async def test_scraper(
        self,
        scraper: GeneratedScraper,
        assertions: Optional[List[Dict[str, Any]]] = None
    ) -> ScraperTestResult:
        """Run the generated scraper and validate with assertions."""
        self.logger.info(f"Testing scraper {scraper.scraper_id} version {scraper.version}")
        
        result = ScraperTestResult()
        result.status = TestStatus.RUNNING
        
        start_time = time.time()
        
        try:
            # Create temporary file for the scraper
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                scraper_path = Path(f.name)
                f.write(scraper.code)
            
            try:
                # Run the scraper in a subprocess
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(scraper_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout_seconds
                    )
                    
                    execution_time = int((time.time() - start_time) * 1000)
                    result.execution_time_ms = execution_time
                    
                    # Capture console logs
                    if stderr:
                        result.console_logs = stderr.decode('utf-8').split('\n')
                    
                    # Parse output as JSON
                    if stdout:
                        try:
                            output_text = stdout.decode('utf-8')
                            result.extracted_data = json.loads(output_text)
                        except json.JSONDecodeError as e:
                            result.error_message = f"Failed to parse scraper output as JSON: {e}"
                            result.console_logs.append(f"Raw output: {output_text[:1000]}")
                    
                    # Check exit code
                    if process.returncode != 0:
                        result.error_message = f"Scraper exited with code {process.returncode}"
                        if stderr:
                            result.stack_trace = stderr.decode('utf-8')
                        result.status = TestStatus.ERROR
                    else:
                        # Run assertions if provided
                        if assertions:
                            self._run_assertions(result, assertions)
                        
                        # Determine overall status
                        if result.error_message:
                            result.status = TestStatus.ERROR
                        elif result.assertions_failed > 0:
                            result.status = TestStatus.FAILED
                        else:
                            result.status = TestStatus.PASSED
                
                except asyncio.TimeoutError:
                    result.error_message = f"Scraper execution timed out after {self.timeout_seconds} seconds"
                    result.status = TestStatus.ERROR
                    process.kill()
                    await process.wait()
            
            finally:
                # Clean up temporary file
                try:
                    scraper_path.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete temp file: {e}")
        
        except Exception as e:
            self.logger.error(f"Error testing scraper: {e}", exc_info=True)
            result.error_message = str(e)
            result.status = TestStatus.ERROR
        
        self.logger.info(f"Test completed with status: {result.status.value}")
        return result
    
    def _run_assertions(self, result: ScraperTestResult, assertions: List[Dict[str, Any]]) -> None:
        """Run assertions against extracted data."""
        for assertion in assertions:
            assertion_type = assertion.get("type", "")
            description = assertion.get("description", "")
            
            assertion_result = {
                "type": assertion_type,
                "description": description,
                "passed": False,
                "message": ""
            }
            
            try:
                if assertion_type == "not_empty":
                    # Check that data is not empty
                    passed = bool(result.extracted_data)
                    assertion_result["passed"] = passed
                    assertion_result["message"] = "Data is not empty" if passed else "Data is empty"
                
                elif assertion_type == "has_field":
                    # Check that a specific field exists
                    field = assertion.get("field", "")
                    passed = field in result.extracted_data
                    assertion_result["passed"] = passed
                    assertion_result["message"] = f"Field '{field}' exists" if passed else f"Field '{field}' not found"
                
                elif assertion_type == "field_not_empty":
                    # Check that a field is not empty
                    field = assertion.get("field", "")
                    value = result.extracted_data.get(field)
                    passed = bool(value)
                    assertion_result["passed"] = passed
                    assertion_result["message"] = f"Field '{field}' is not empty" if passed else f"Field '{field}' is empty"
                
                elif assertion_type == "min_items":
                    # Check minimum number of items in a list field
                    field = assertion.get("field", "")
                    min_count = assertion.get("min_count", 1)
                    value = result.extracted_data.get(field, [])
                    if isinstance(value, list):
                        passed = len(value) >= min_count
                        assertion_result["passed"] = passed
                        assertion_result["message"] = f"Field '{field}' has {len(value)} items (min: {min_count})"
                    else:
                        assertion_result["message"] = f"Field '{field}' is not a list"
                
                elif assertion_type == "field_type":
                    # Check field data type
                    field = assertion.get("field", "")
                    expected_type = assertion.get("expected_type", "")
                    value = result.extracted_data.get(field)
                    
                    type_map = {
                        "string": str,
                        "number": (int, float),
                        "list": list,
                        "dict": dict,
                        "boolean": bool
                    }
                    
                    expected_python_type = type_map.get(expected_type)
                    if expected_python_type:
                        passed = isinstance(value, expected_python_type)
                        assertion_result["passed"] = passed
                        actual_type = type(value).__name__
                        assertion_result["message"] = f"Field '{field}' type: {actual_type} (expected: {expected_type})"
                    else:
                        assertion_result["message"] = f"Unknown type: {expected_type}"
                
                elif assertion_type == "custom":
                    # Custom assertion with expression
                    expression = assertion.get("expression", "")
                    try:
                        # Evaluate expression with data context
                        passed = eval(expression, {"__builtins__": {}}, {"data": result.extracted_data})
                        assertion_result["passed"] = bool(passed)
                        assertion_result["message"] = f"Custom assertion: {expression}"
                    except Exception as e:
                        assertion_result["message"] = f"Failed to evaluate custom assertion: {e}"
                
                else:
                    assertion_result["message"] = f"Unknown assertion type: {assertion_type}"
            
            except Exception as e:
                self.logger.error(f"Error running assertion: {e}")
                assertion_result["message"] = f"Error: {e}"
            
            result.assertion_details.append(assertion_result)
            
            if assertion_result["passed"]:
                result.assertions_passed += 1
            else:
                result.assertions_failed += 1
    
    def get_default_assertions(self) -> List[Dict[str, Any]]:
        """Get default assertions for basic scraper validation."""
        return [
            {
                "type": "not_empty",
                "description": "Extracted data should not be empty"
            },
            {
                "type": "has_field",
                "field": "url",
                "description": "Data should include the source URL"
            }
        ]
