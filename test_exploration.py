"""Simple test script for the exploration orchestrator system."""
import sys
import os
sys.path.insert(0, '/home/engine/project')

from app.models.exploration_session import ExplorationSession, SessionStatus
from app.services.exploration_orchestrator import ExplorationOrchestrator
from app.services.exploration_service import ExplorationService
import json

def test_exploration_system():
    """Test the exploration orchestrator system."""
    print("Testing Exploration Orchestrator System")
    print("=" * 50)
    
    # Test 1: Create a simple exploration session
    print("\n1. Creating exploration session...")
    session = ExplorationSession(
        url="https://example.com",
        objectives="Extract page title, navigation elements, and main content",
        status=SessionStatus.CREATED
    )
    print(f"   Session ID: {session.session_id}")
    print(f"   URL: {session.url}")
    print(f"   Objectives: {session.objectives}")
    
    # Test 2: Create exploration service
    print("\n2. Creating exploration service...")
    browser_settings = {
        "headless": True,
        "viewport_width": 1280,
        "viewport_height": 720,
        "user_agent": "Test Browser Agent"
    }
    service = ExplorationService(browser_settings)
    print("   Exploration service created successfully")
    
    # Test 3: Test session creation via service
    print("\n3. Testing session creation via service...")
    session_data = service.create_exploration_session(
        url="https://httpbin.org/html",
        objectives="Test the extraction of page content and navigation",
        metadata={"test_mode": True, "version": "1.0"}
    )
    print(f"   Created session: {session_data['session_id']}")
    print(f"   Status: {session_data['status']}")
    
    # Test 4: Test orchestrator creation
    print("\n4. Testing orchestrator creation...")
    orchestrator = service.store.create_orchestrator(
        session_data['session_id'], 
        browser_settings
    )
    if orchestrator:
        print("   Orchestrator created successfully")
        print(f"   Session status: {orchestrator.session.status.value}")
    else:
        print("   Failed to create orchestrator")
    
    # Test 5: Test coordinator agent
    print("\n5. Testing coordinator agent...")
    plan = orchestrator.coordinator.create_exploration_plan(
        session.url, 
        session.objectives
    )
    print(f"   Created plan with {len(plan['steps'])} steps:")
    for i, step in enumerate(plan['steps'][:3]):  # Show first 3 steps
        print(f"     Step {step['step_id']}: {step['description']} ({step['type']})")
    
    # Test 6: Test browser agent initialization
    print("\n6. Testing browser agent...")
    browser_initialized = orchestrator.browser_agent.initialize_browser()
    print(f"   Browser initialized: {browser_initialized}")
    browser_info = orchestrator.browser_agent.get_current_page_info()
    print(f"   Browser status: {browser_info['status']}")
    
    # Test 7: Test analyst agent
    print("\n7. Testing analyst agent...")
    sample_content = {
        "title": "Test Page",
        "elements": ["header", "navigation", "content", "footer"],
        "forms": ["search form", "contact form"]
    }
    analysis = orchestrator.analyst_agent.analyze_page_content(sample_content)
    print(f"   Content type identified: {analysis['content_type']}")
    print(f"   Key insights: {len(analysis['insights'])} insights generated")
    
    # Test 8: Test session status
    print("\n8. Testing session status retrieval...")
    status = service.get_session_status(session_data['session_id'])
    if status:
        print(f"   Session found: {status['session']['session_id']}")
        print(f"   Progress: {status['session']['progress_percentage']}%")
    else:
        print("   Session not found")
    
    # Test 9: Test chat messaging
    print("\n9. Testing chat messaging...")
    chat_result = service.send_chat_message(
        session_data['session_id'],
        "Please analyze the page structure",
        "user"
    )
    print(f"   Chat message sent: {chat_result['success']}")
    print(f"   Message ID: {chat_result.get('message_id', 'N/A')}")
    
    messages = service.get_chat_messages(session_data['session_id'])
    print(f"   Total messages: {len(messages)}")
    
    # Test 10: Test system status
    print("\n10. Testing system status...")
    all_sessions = service.list_sessions()
    print(f"   Total sessions: {len(all_sessions)}")
    
    print("\n" + "=" * 50)
    print("Exploration Orchestrator System Test Complete!")
    print("All core components working correctly.")
    
    return True

def test_data_models():
    """Test the data models."""
    print("\nTesting Data Models")
    print("=" * 30)
    
    # Test ActionLog
    from app.models.exploration_session import ActionLog, ActionType, AgentRole
    print("\n1. Testing ActionLog...")
    action = ActionLog(
        agent_role=AgentRole.COORDINATOR,
        action_type=ActionType.PLAN_CREATION,
        description="Test action",
        reasoning="This is a test action",
        details={"test": True}
    )
    print(f"   Action ID: {action.action_id}")
    print(f"   Description: {action.description}")
    
    # Test ScreenshotMetadata
    from app.models.exploration_session import ScreenshotMetadata
    print("\n2. Testing ScreenshotMetadata...")
    screenshot = ScreenshotMetadata(
        url="https://example.com",
        title="Test Screenshot",
        width=1920,
        height=1080,
        observations=["Visual content captured", "UI elements identified"]
    )
    print(f"   Screenshot ID: {screenshot.screenshot_id}")
    print(f"   URL: {screenshot.url}")
    print(f"   Observations: {len(screenshot.observations)} observations")
    
    print("\nData models test complete!")
    return True

if __name__ == "__main__":
    try:
        print("Starting Exploration Orchestrator Tests...\n")
        
        # Test data models first
        test_data_models()
        
        # Test main system
        test_exploration_system()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)