"""Approval pipeline service coordinating exploration to scraper delivery."""
from __future__ import annotations

import logging
import zipfile
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.models import (
    ExplorationSession,
    ApprovalGate,
    ApprovalStatus,
    ApprovalType,
    GeneratedScraper,
    ScraperTestResult,
    GenerationStatus,
    TestStatus,
)
from app.services.scraper_generator import ScraperGenerator
from app.services.scraper_tester import ScraperTester


class ApprovalPipeline:
    """Manages the approval pipeline from exploration to scraper delivery."""
    
    def __init__(
        self,
        scraper_generator: ScraperGenerator,
        logger: Optional[logging.Logger] = None
    ):
        self.generator = scraper_generator
        self.logger = logger or logging.getLogger(__name__)
    
    def create_exploration_approval(self, session: ExplorationSession) -> ApprovalGate:
        """Create an approval gate for exploration summary."""
        self.logger.info(f"Creating exploration approval gate for session {session.session_id}")
        
        # Generate summary
        summary = self._generate_exploration_summary(session)
        
        approval = ApprovalGate(
            approval_type=ApprovalType.EXPLORATION_SUMMARY,
            summary=summary,
            status=ApprovalStatus.PENDING
        )
        
        return approval
    
    def create_scraper_approval(
        self,
        session: ExplorationSession,
        scraper: GeneratedScraper
    ) -> ApprovalGate:
        """Create an approval gate for generated scraper."""
        self.logger.info(f"Creating scraper approval gate for session {session.session_id}")
        
        # Generate summary with test results
        summary = self._generate_scraper_summary(scraper)
        
        approval = ApprovalGate(
            approval_type=ApprovalType.SCRAPER_GENERATION,
            summary=summary,
            status=ApprovalStatus.PENDING
        )
        
        return approval
    
    def create_delivery_approval(
        self,
        session: ExplorationSession,
        scraper: GeneratedScraper
    ) -> ApprovalGate:
        """Create an approval gate for final delivery."""
        self.logger.info(f"Creating delivery approval gate for session {session.session_id}")
        
        summary = self._generate_delivery_summary(scraper)
        
        approval = ApprovalGate(
            approval_type=ApprovalType.FINAL_DELIVERY,
            summary=summary,
            status=ApprovalStatus.PENDING
        )
        
        return approval
    
    def check_approval_sequencing(
        self,
        session: ExplorationSession,
        required_approval: ApprovalType
    ) -> tuple[bool, str]:
        """Check if approval sequencing is valid."""
        # Build approval sequence map
        approval_map = {gate["approval_type"]: gate for gate in session.approval_gates}
        
        if required_approval == ApprovalType.SCRAPER_GENERATION:
            # Need exploration approval first
            exploration_approval = approval_map.get("exploration_summary")
            if not exploration_approval:
                return False, "Exploration summary must be created first"
            if exploration_approval["status"] != "approved":
                return False, "Exploration summary must be approved before scraper generation"
        
        elif required_approval == ApprovalType.FINAL_DELIVERY:
            # Need both previous approvals
            exploration_approval = approval_map.get("exploration_summary")
            scraper_approval = approval_map.get("scraper_generation")
            
            if not exploration_approval or exploration_approval["status"] != "approved":
                return False, "Exploration summary must be approved first"
            if not scraper_approval or scraper_approval["status"] != "approved":
                return False, "Scraper generation must be approved before final delivery"
        
        return True, "Approval sequencing valid"
    
    async def generate_and_test_scraper(
        self,
        session: ExplorationSession,
        assertions: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 5
    ) -> GeneratedScraper:
        """Generate scraper with iterative testing and refinement."""
        self.logger.info(f"Starting scraper generation for session {session.session_id}")
        
        # Generate specification
        specification = self.generator.generate_specification(session)
        
        # Generate initial scraper
        scraper = self.generator.generate_scraper_code(specification, session)
        
        if scraper.status == GenerationStatus.FAILED:
            return scraper
        
        # Iterative testing and refinement
        tester = ScraperTester(session.url, self.logger)
        
        if not assertions:
            assertions = tester.get_default_assertions()
        
        for iteration in range(max_iterations):
            self.logger.info(f"Testing iteration {iteration + 1}/{max_iterations}")
            
            # Test the scraper
            test_result = await tester.test_scraper(scraper, assertions)
            scraper.add_test_result(test_result)
            
            # Check if tests passed
            if test_result.status == TestStatus.PASSED:
                self.logger.info(f"Scraper tests passed on iteration {iteration + 1}")
                scraper.update_status(GenerationStatus.COMPLETED)
                break
            
            # If not last iteration, refine the scraper
            if iteration < max_iterations - 1:
                self.logger.info(f"Tests failed, refining scraper...")
                scraper = self.generator.refine_scraper(scraper, session, test_result)
                
                if scraper.status == GenerationStatus.FAILED:
                    break
            else:
                self.logger.warning(f"Max iterations reached without passing tests")
                scraper.update_status(GenerationStatus.FAILED)
        
        return scraper
    
    def generate_scraper_package(
        self,
        session: ExplorationSession,
        scraper: GeneratedScraper
    ) -> bytes:
        """Generate a downloadable package with scraper and metadata."""
        self.logger.info(f"Generating scraper package for session {session.session_id}")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            package_dir = Path(tmpdir) / "scraper_package"
            package_dir.mkdir()
            
            # Write scraper code
            scraper_file = package_dir / "scraper.py"
            scraper_file.write_text(scraper.code, encoding='utf-8')
            
            # Write requirements.txt
            requirements_file = package_dir / "requirements.txt"
            requirements_file.write_text("\n".join(scraper.dependencies), encoding='utf-8')
            
            # Write README
            readme_file = package_dir / "README.md"
            readme_file.write_text(scraper.readme, encoding='utf-8')
            
            # Write metadata
            metadata = {
                "scraper_id": scraper.scraper_id,
                "session_id": scraper.session_id,
                "version": scraper.version,
                "generated_at": scraper.created_at,
                "url": session.url,
                "objectives": session.objectives,
                "framework": scraper.framework,
                "language": scraper.language,
                "model_used": scraper.model_used,
                "test_summary": {
                    "total_tests": len(scraper.test_results),
                    "last_status": scraper.last_test_status.value,
                    "iterations": scraper.iteration_count
                }
            }
            
            metadata_file = package_dir / "metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            
            # Write test results
            if scraper.test_results:
                test_results_file = package_dir / "test_results.json"
                test_results_data = [result.to_dict() for result in scraper.test_results]
                test_results_file.write_text(
                    json.dumps(test_results_data, indent=2),
                    encoding='utf-8'
                )
            
            # Create zip file
            zip_path = Path(tmpdir) / "scraper_package.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(package_dir)
                        zipf.write(file_path, arcname)
            
            # Read zip file
            package_bytes = zip_path.read_bytes()
            
            return package_bytes
    
    def get_scraper_diffs(
        self,
        scraper: GeneratedScraper,
        previous_version: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get differences between scraper iterations."""
        diffs = []
        
        # For now, provide summary of changes per iteration
        for i, test_result in enumerate(scraper.test_results):
            diff_entry = {
                "iteration": i + 1,
                "version": i + 1,
                "timestamp": test_result.timestamp,
                "status": test_result.status.value,
                "changes": f"Iteration {i + 1}",
                "test_summary": {
                    "passed": test_result.assertions_passed,
                    "failed": test_result.assertions_failed,
                    "errors": bool(test_result.error_message)
                }
            }
            
            if test_result.error_message:
                diff_entry["error"] = test_result.error_message
            
            diffs.append(diff_entry)
        
        return diffs
    
    def _generate_exploration_summary(self, session: ExplorationSession) -> str:
        """Generate a human-readable summary of exploration findings."""
        parts = [
            f"# Exploration Summary for {session.url}",
            "",
            f"**Objectives:** {session.objectives}",
            f"**Status:** {session.status.value}",
            f"**Duration:** {self._calculate_duration(session)}",
            "",
            "## Key Findings",
            ""
        ]
        
        # Summarize actions
        action_types = {}
        for log in session.action_logs:
            if log.action_type:
                action_types[log.action_type.value] = action_types.get(log.action_type.value, 0) + 1
        
        if action_types:
            parts.append("### Actions Performed")
            for action_type, count in action_types.items():
                parts.append(f"- {action_type}: {count}")
            parts.append("")
        
        # Screenshots captured
        if session.screenshots:
            parts.append(f"### Screenshots: {len(session.screenshots)} captured")
            parts.append("")
        
        # Analyst insights
        if session.analyst_state and session.analyst_state.reasoning:
            parts.append("### Analysis")
            parts.append(session.analyst_state.reasoning)
            parts.append("")
        
        return "\n".join(parts)
    
    def _generate_scraper_summary(self, scraper: GeneratedScraper) -> str:
        """Generate summary of scraper generation and test results."""
        parts = [
            f"# Scraper Generation Summary",
            "",
            f"**Version:** {scraper.version}",
            f"**Status:** {scraper.status.value}",
            f"**Framework:** {scraper.framework}",
            f"**Iterations:** {scraper.iteration_count}",
            "",
            "## Test Results",
            ""
        ]
        
        if scraper.test_results:
            last_test = scraper.test_results[-1]
            parts.append(f"**Last Test Status:** {last_test.status.value}")
            parts.append(f"**Assertions Passed:** {last_test.assertions_passed}")
            parts.append(f"**Assertions Failed:** {last_test.assertions_failed}")
            
            if last_test.error_message:
                parts.append("")
                parts.append("### Error")
                parts.append(f"```\n{last_test.error_message}\n```")
        else:
            parts.append("No tests run yet")
        
        parts.append("")
        parts.append("## Code Preview")
        parts.append("```python")
        # Show first 20 lines
        code_lines = scraper.code.split('\n')[:20]
        parts.extend(code_lines)
        if len(scraper.code.split('\n')) > 20:
            parts.append("... (truncated)")
        parts.append("```")
        
        return "\n".join(parts)
    
    def _generate_delivery_summary(self, scraper: GeneratedScraper) -> str:
        """Generate summary for final delivery approval."""
        parts = [
            f"# Final Delivery Package",
            "",
            f"**Scraper Version:** {scraper.version}",
            f"**Framework:** {scraper.framework} ({scraper.language})",
            f"**Test Status:** {scraper.last_test_status.value}",
            "",
            "## Package Contents",
            "- scraper.py - Main scraper script",
            "- requirements.txt - Python dependencies",
            "- README.md - Documentation",
            "- metadata.json - Generation metadata",
            "- test_results.json - Test execution results",
            "",
            "## Validation",
            ""
        ]
        
        if scraper.test_results:
            last_test = scraper.test_results[-1]
            parts.append(f"✓ Tested successfully")
            parts.append(f"✓ {last_test.assertions_passed} assertions passed")
            
            if last_test.execution_time_ms:
                parts.append(f"✓ Execution time: {last_test.execution_time_ms}ms")
        
        return "\n".join(parts)
    
    def _calculate_duration(self, session: ExplorationSession) -> str:
        """Calculate session duration."""
        if not session.started_at:
            return "Not started"
        
        start = datetime.fromisoformat(session.started_at.replace('Z', '+00:00'))
        
        if session.completed_at:
            end = datetime.fromisoformat(session.completed_at.replace('Z', '+00:00'))
        else:
            end = datetime.now(tz=timezone.utc)
        
        duration = end - start
        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)
        
        return f"{minutes}m {seconds}s"
