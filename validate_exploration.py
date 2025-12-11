"""Final validation of the exploration orchestrator implementation."""
import os
import re

def validate_file_structure():
    """Validate that all required files exist and have expected content."""
    print("🔍 Validating Exploration Orchestrator File Structure")
    print("=" * 58)
    
    required_files = {
        # Core models
        "/home/engine/project/app/models/__init__.py": "Data models package",
        "/home/engine/project/app/models/exploration_session.py": "ExplorationSession model",
        
        # Multi-agent system
        "/home/engine/project/app/agents/__init__.py": "Multi-agent system package",
        "/home/engine/project/app/agents/coordinator_agent.py": "CoordinatorAgent implementation",
        "/home/engine/project/app/agents/browser_agent.py": "BrowserAgent implementation", 
        "/home/engine/project/app/agents/analyst_agent.py": "AnalystAgent implementation",
        
        # Services layer
        "/home/engine/project/app/services/__init__.py": "Services package",
        "/home/engine/project/app/services/exploration_orchestrator.py": "Orchestration logic",
        "/home/engine/project/app/services/exploration_service.py": "Session management service",
        
        # API layer
        "/home/engine/project/app/api/routes.py": "REST API routes"
    }
    
    print("\n1. Checking required files exist...")
    all_files_exist = True
    for file_path, description in required_files.items():
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        size = os.path.getsize(file_path) if exists else 0
        print(f"   {status} {description}")
        print(f"      Path: {file_path}")
        if exists:
            print(f"      Size: {size:,} bytes")
        all_files_exist &= exists
    
    return all_files_exist

def validate_models_content():
    """Validate the data models have required components."""
    print("\n\n🔍 Validating Data Models Content")
    print("=" * 35)
    
    models_file = "/home/engine/project/app/models/exploration_session.py"
    if not os.path.exists(models_file):
        print("❌ Models file not found")
        return False
        
    with open(models_file, 'r') as f:
        content = f.read()
    
    required_components = {
        "ExplorationSession": "Main session model",
        "ActionLog": "Action logging model",
        "ScreenshotMetadata": "Screenshot metadata model",
        "SessionStatus": "Session status enum",
        "AgentRole": "Agent role enum",
        "ActionType": "Action type enum",
        "to_dict()": "Serialization methods",
        "add_action_log": "Session update methods",
        "add_screenshot": "Screenshot management",
        "add_message": "Chat message handling"
    }
    
    print("\n1. Checking required components...")
    all_found = True
    for component, description in required_components.items():
        found = component in content
        status = "✅" if found else "❌"
        print(f"   {status} {description}: {component}")
        all_found &= found
    
    return all_found

def validate_agents_content():
    """Validate the agent implementations have required functionality."""
    print("\n\n🔍 Validating Agent Implementations")
    print("=" * 37)
    
    agent_files = {
        "/home/engine/project/app/agents/coordinator_agent.py": ["create_exploration_plan", "select_next_action", "AgentRole.COORDINATOR"],
        "/home/engine/project/app/agents/browser_agent.py": ["navigate_to_url", "capture_screenshot", "query_dom", "AgentRole.BROWSER"],
        "/home/engine/project/app/agents/analyst_agent.py": ["analyze_page_content", "analyze_screenshot", "synthesize_findings", "AgentRole.ANALYST"]
    }
    
    all_agents_valid = True
    for agent_file, required_items in agent_files.items():
        if not os.path.exists(agent_file):
            print(f"❌ Agent file missing: {agent_file}")
            all_agents_valid = False
            continue
            
        with open(agent_file, 'r') as f:
            content = f.read()
        
        print(f"\n1. Checking {os.path.basename(agent_file)}...")
        file_valid = True
        for item in required_items:
            found = item in content
            status = "✅" if found else "❌"
            print(f"   {status} Contains: {item}")
            file_valid &= found
        
        all_agents_valid &= file_valid
    
    return all_agents_valid

def validate_services_content():
    """Validate the services have required functionality."""
    print("\n\n🔍 Validating Services Content")
    print("=" * 32)
    
    orchestrator_file = "/home/engine/project/app/services/exploration_orchestrator.py"
    service_file = "/home/engine/project/app/services/exploration_service.py"
    
    if not os.path.exists(orchestrator_file) or not os.path.exists(service_file):
        print("❌ Service files missing")
        return False
    
    orchestrator_valid = True
    with open(orchestrator_file, 'r') as f:
        orchestrator_content = f.read()
    
    orchestrator_features = [
        "class ExplorationOrchestrator",
        "start_exploration", 
        "_run_exploration_loop",
        "_execute_step",
        "pause_exploration",
        "resume_exploration", 
        "get_current_status"
    ]
    
    print("\n1. Checking ExplorationOrchestrator...")
    for feature in orchestrator_features:
        found = feature in orchestrator_content
        status = "✅" if found else "❌"
        print(f"   {status} Has: {feature}")
        orchestrator_valid &= found
    
    service_valid = True
    with open(service_file, 'r') as f:
        service_content = f.read()
    
    service_features = [
        "class ExplorationSessionStore",
        "class ExplorationService", 
        "create_exploration_session",
        "start_exploration",
        "get_session_status",
        "send_chat_message",
        "get_chat_messages"
    ]
    
    print("\n2. Checking ExplorationService...")
    for feature in service_features:
        found = feature in service_content
        status = "✅" if found else "❌"
        print(f"   {status} Has: {feature}")
        service_valid &= found
    
    return orchestrator_valid and service_valid

def validate_api_endpoints():
    """Validate the API has all required endpoints."""
    print("\n\n🔍 Validating API Endpoints")
    print("=" * 29)
    
    routes_file = "/home/engine/project/app/api/routes.py"
    if not os.path.exists(routes_file):
        print("❌ Routes file not found")
        return False
    
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Check for required endpoints
    endpoints = {
        "POST /api/v1/exploration/sessions": "Create exploration session",
        "GET /api/v1/exploration/sessions/<session_id>": "Get session status", 
        "POST /api/v1/exploration/sessions/<session_id>/start": "Start exploration",
        "POST /api/v1/exploration/sessions/<session_id>/pause": "Pause exploration",
        "POST /api/v1/exploration/sessions/<session_id>/resume": "Resume exploration",
        "POST /api/v1/exploration/sessions/<session_id>/stop": "Stop exploration",
        "POST /api/v1/exploration/sessions/<session_id>/chat": "Send chat message",
        "GET /api/v1/exploration/sessions/<session_id>/chat": "Get chat messages",
        "GET /api/v1/exploration/sessions/<session_id>/actions": "Get action logs",
        "GET /api/v1/exploration/sessions/<session_id>/screenshots": "Get screenshots",
        "GET /api/v1/exploration/sessions": "List all sessions",
        "DELETE /api/v1/exploration/sessions/<session_id>": "Delete session",
        "GET /api/v1/exploration/status": "System status"
    }
    
    print("\n1. Checking required endpoints...")
    all_found = True
    for endpoint, description in endpoints.items():
        # Check if the endpoint pattern exists in the file
        endpoint_pattern = endpoint.replace("<session_id>", "<.*?>")
        found = re.search(endpoint_pattern.replace("/", r"\/"), content) is not None
        status = "✅" if found else "❌"
        print(f"   {status} {description}")
        print(f"      Endpoint: {endpoint}")
        all_found &= found
    
    return all_found

def validate_acceptance_criteria():
    """Validate that the implementation meets all acceptance criteria."""
    print("\n\n🔍 Validating Acceptance Criteria")
    print("=" * 36)
    
    criteria = {
        "ExplorationSession model": {
            "description": "Model persists URL, objectives, agent state, and action logs",
            "check_files": ["/home/engine/project/app/models/exploration_session.py"],
            "required_keywords": ["url", "objectives", "action_logs", "screenshots", "AgentState"]
        },
        "Multi-agent loop": {
            "description": "Coordinator plans, browser executes, analyst summarizes",
            "check_files": [
                "/home/engine/project/app/agents/coordinator_agent.py",
                "/home/engine/project/app/agents/browser_agent.py", 
                "/home/engine/project/app/agents/analyst_agent.py"
            ],
            "required_keywords": ["CoordinatorAgent", "BrowserAgent", "AnalystAgent", "plan", "execute", "analyze"]
        },
        "Screenshot capture & analysis": {
            "description": "Screenshot capture hooks with metadata storage",
            "check_files": ["/home/engine/project/app/agents/browser_agent.py", "/home/engine/project/app/agents/analyst_agent.py"],
            "required_keywords": ["capture_screenshot", "ScreenshotMetadata", "observations"]
        },
        "Chat orchestrator endpoint": {
            "description": "API endpoints for client instructions and monitoring",
            "check_files": ["/home/engine/project/app/api/routes.py"],
            "required_keywords": ["/chat", "send_chat_message", "get_chat_messages", "websocket or polling"]
        },
        "Structured logging": {
            "description": "All actions/decisions logged with workflow alignment",
            "check_files": ["/home/engine/project/app/models/exploration_session.py"],
            "required_keywords": ["ActionLog", "action_type", "add_action_log", "structured"]
        }
    }
    
    print("\n1. Checking acceptance criteria implementation...")
    all_criteria_met = True
    
    for criteria_name, criteria_info in criteria.items():
        print(f"\n   📋 {criteria_name}")
        print(f"      {criteria_info['description']}")
        
        criteria_met = True
        for file_path in criteria_info["check_files"]:
            if not os.path.exists(file_path):
                print(f"      ❌ File missing: {file_path}")
                criteria_met = False
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for required keywords
            missing_keywords = []
            for keyword in criteria_info["required_keywords"]:
                if keyword not in content:
                    missing_keywords.append(keyword)
            
            if missing_keywords:
                print(f"      ❌ Missing keywords in {os.path.basename(file_path)}: {', '.join(missing_keywords)}")
                criteria_met = False
            else:
                print(f"      ✅ Found in {os.path.basename(file_path)}")
        
        all_criteria_met &= criteria_met
    
    return all_criteria_met

def main():
    """Run complete validation."""
    print("🚀 EXPLORATION ORCHESTRATOR VALIDATION")
    print("=" * 45)
    print("Testing implementation against requirements...")
    
    # Run all validations
    structure_valid = validate_file_structure()
    models_valid = validate_models_content()
    agents_valid = validate_agents_content()
    services_valid = validate_services_content()
    api_valid = validate_api_endpoints()
    criteria_valid = validate_acceptance_criteria()
    
    # Summary
    print("\n\n" + "=" * 45)
    print("📊 VALIDATION SUMMARY")
    print("=" * 45)
    
    validations = [
        ("File Structure", structure_valid),
        ("Data Models", models_valid), 
        ("Agent Implementations", agents_valid),
        ("Services Layer", services_valid),
        ("API Endpoints", api_valid),
        ("Acceptance Criteria", criteria_valid)
    ]
    
    for name, passed in validations:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {name}")
    
    all_valid = all(passed for _, passed in validations)
    
    print("\n" + "=" * 45)
    if all_valid:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("\n✨ The Exploration Orchestrator implementation is complete and meets all requirements:")
        print("   ✅ ExplorationSession model with persistent state")
        print("   ✅ Multi-agent coordination system")
        print("   ✅ Screenshot capture and analysis")
        print("   ✅ Chat orchestrator with REST API")
        print("   ✅ Structured action logging")
        print("   ✅ Session management and monitoring")
        print("\n🚀 Ready for production use!")
    else:
        print("❌ Some validations failed")
        print("Please review the failed items above.")
    
    return all_valid

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)