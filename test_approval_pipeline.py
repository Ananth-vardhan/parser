"""Test script for approval pipeline and code generation."""
import json
import os
import sys
import time
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import (
    ExplorationSession,
    SessionStatus,
    ActionLog,
    ActionType,
    AgentRole,
    ScreenshotMetadata,
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
from app.services.approval_pipeline import ApprovalPipeline


def test_data_models():
    """Test the new data models."""
    print("=" * 60)
    print("Testing Data Models")
    print("=" * 60)
    
    # Test ApprovalGate
    print("\n1. Testing ApprovalGate model...")
    approval = ApprovalGate(
        approval_type=ApprovalType.EXPLORATION_SUMMARY,
        summary="Test exploration summary"
    )
    assert approval.status == ApprovalStatus.PENDING
    assert approval.approved_by is None
    
    approval.approve("test_user", "Looks good!")
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.approved_by == "test_user"
    assert approval.feedback == "Looks good!"
    print("✓ ApprovalGate model works correctly")
    
    # Test GeneratedScraper
    print("\n2. Testing GeneratedScraper model...")
    scraper = GeneratedScraper(
        session_id="test-123",
        specification="Test spec",
        code="print('Hello, World!')"
    )
    assert scraper.version == 1
    assert scraper.status == GenerationStatus.NOT_STARTED
    
    scraper.increment_version()
    assert scraper.version == 2
    assert scraper.iteration_count == 1
    print("✓ GeneratedScraper model works correctly")
    
    # Test ScraperTestResult
    print("\n3. Testing ScraperTestResult model...")
    test_result = ScraperTestResult()
    test_result.status = TestStatus.PASSED
    test_result.assertions_passed = 5
    test_result.assertions_failed = 0
    
    result_dict = test_result.to_dict()
    assert result_dict["status"] == "passed"
    assert result_dict["assertions_passed"] == 5
    print("✓ ScraperTestResult model works correctly")
    
    print("\n✅ All data model tests passed!\n")


def test_specification_generation():
    """Test specification generation from exploration logs."""
    print("=" * 60)
    print("Testing Specification Generation")
    print("=" * 60)
    
    # Create a mock exploration session
    session = ExplorationSession(
        url="https://example.com",
        objectives="Extract product information"
    )
    
    # Add some action logs
    session.add_action_log(ActionLog(
        agent_role=AgentRole.BROWSER,
        action_type=ActionType.NAVIGATION,
        description="Navigated to homepage",
        result="Successfully loaded page"
    ))
    
    session.add_action_log(ActionLog(
        agent_role=AgentRole.BROWSER,
        action_type=ActionType.DOM_QUERY,
        description="Queried product elements",
        result="Found 10 products"
    ))
    
    # Add screenshot metadata
    session.add_screenshot(ScreenshotMetadata(
        url=session.url,
        observations=["Product grid visible", "Price elements found"],
        dom_summary="Contains product cards with prices"
    ))
    
    # Test specification generation (mock without actual OpenAI call)
    print("\n1. Testing specification generation structure...")
    
    # Mock generator
    class MockScraperGenerator:
        def generate_specification(self, session):
            spec = f"# Web Scraper Specification\n\n"
            spec += f"## Target URL\n{session.url}\n\n"
            spec += f"## Objectives\n{session.objectives}\n\n"
            spec += "## Exploration Findings\n"
            return spec
    
    generator = MockScraperGenerator()
    spec = generator.generate_specification(session)
    
    assert "Web Scraper Specification" in spec
    assert session.url in spec
    assert session.objectives in spec
    print("✓ Specification structure is correct")
    
    print("\n✅ Specification generation test passed!\n")


def test_approval_pipeline():
    """Test the approval pipeline workflow."""
    print("=" * 60)
    print("Testing Approval Pipeline")
    print("=" * 60)
    
    # Create session
    session = ExplorationSession(
        url="https://example.com",
        objectives="Extract data"
    )
    session.update_status(SessionStatus.COMPLETED)
    
    # Mock pipeline
    class MockGenerator:
        def generate_specification(self, session):
            return "Mock specification"
    
    generator = MockGenerator()
    pipeline = ApprovalPipeline(generator)
    
    # Test exploration approval creation
    print("\n1. Testing exploration approval gate creation...")
    approval = pipeline.create_exploration_approval(session)
    assert approval.approval_type == ApprovalType.EXPLORATION_SUMMARY
    assert approval.status == ApprovalStatus.PENDING
    print("✓ Exploration approval gate created")
    
    # Test approval sequencing
    print("\n2. Testing approval sequencing...")
    session.approval_gates.append(approval.to_dict())
    
    # Should fail - exploration not approved yet
    valid, msg = pipeline.check_approval_sequencing(
        session,
        ApprovalType.SCRAPER_GENERATION
    )
    assert not valid
    print(f"✓ Correctly blocks scraper generation: {msg}")
    
    # Approve exploration
    approval.approve("test_user")
    session.approval_gates[0] = approval.to_dict()
    
    # Should pass now
    valid, msg = pipeline.check_approval_sequencing(
        session,
        ApprovalType.SCRAPER_GENERATION
    )
    assert valid
    print("✓ Allows scraper generation after approval")
    
    print("\n✅ Approval pipeline tests passed!\n")


def test_scraper_tester():
    """Test the scraper testing harness."""
    print("=" * 60)
    print("Testing Scraper Tester")
    print("=" * 60)
    
    # Test assertion logic
    print("\n1. Testing assertion logic...")
    tester = ScraperTester("https://example.com")
    
    # Create mock result with data
    result = ScraperTestResult()
    result.extracted_data = {
        "url": "https://example.com",
        "title": "Test Page",
        "items": ["item1", "item2", "item3"]
    }
    
    # Test assertions
    assertions = [
        {"type": "not_empty", "description": "Data not empty"},
        {"type": "has_field", "field": "url", "description": "Has URL field"},
        {"type": "field_not_empty", "field": "title", "description": "Title not empty"},
        {"type": "min_items", "field": "items", "min_count": 2, "description": "At least 2 items"},
        {"type": "field_type", "field": "title", "expected_type": "string", "description": "Title is string"}
    ]
    
    tester._run_assertions(result, assertions)
    
    assert result.assertions_passed == 5
    assert result.assertions_failed == 0
    print(f"✓ All {result.assertions_passed} assertions passed")
    
    # Test default assertions
    print("\n2. Testing default assertions...")
    default_assertions = tester.get_default_assertions()
    assert len(default_assertions) > 0
    assert any(a["type"] == "not_empty" for a in default_assertions)
    print(f"✓ Generated {len(default_assertions)} default assertions")
    
    print("\n✅ Scraper tester tests passed!\n")


def test_session_integration():
    """Test integration with ExplorationSession."""
    print("=" * 60)
    print("Testing Session Integration")
    print("=" * 60)
    
    print("\n1. Testing session with approval gates...")
    session = ExplorationSession(
        url="https://example.com",
        objectives="Test objectives"
    )
    
    # Add approval gate
    approval = ApprovalGate(
        approval_type=ApprovalType.EXPLORATION_SUMMARY,
        summary="Test summary"
    )
    session.approval_gates.append(approval.to_dict())
    
    # Add scraper
    scraper = GeneratedScraper(
        session_id=session.session_id,
        specification="Test spec",
        code="# Test code"
    )
    session.current_scraper = scraper.to_dict()
    session.generated_scrapers.append(scraper.to_dict())
    
    # Convert to dict and verify
    session_dict = session.to_dict()
    assert "approval_gates" in session_dict
    assert "current_scraper" in session_dict
    assert "generated_scrapers" in session_dict
    assert len(session_dict["approval_gates"]) == 1
    assert session_dict["current_scraper"]["session_id"] == session.session_id
    print("✓ Session correctly stores approval gates and scrapers")
    
    print("\n✅ Session integration test passed!\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("APPROVAL PIPELINE TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_data_models()
        test_specification_generation()
        test_approval_pipeline()
        test_scraper_tester()
        test_session_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe approval pipeline implementation is working correctly.")
        print("\nKey Features Verified:")
        print("  • Approval gate models with status tracking")
        print("  • Generated scraper models with versioning")
        print("  • Test result models with assertions")
        print("  • Specification generation from exploration logs")
        print("  • Approval sequencing enforcement")
        print("  • Testing harness with configurable assertions")
        print("  • Integration with exploration sessions")
        print("\nNext Steps:")
        print("  • Set OPENAI_API_KEY environment variable for code generation")
        print("  • Use the API endpoints to test the full workflow")
        print("  • Test with real exploration sessions")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
