"""
Example script demonstrating the approval pipeline API usage.

This script shows the complete workflow from exploration to scraper delivery.
"""

import requests
import time
import json
from typing import Dict, Any, Optional


class ApprovalPipelineClient:
    """Client for interacting with the approval pipeline API."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
    
    def create_exploration_session(self, url: str, objectives: str) -> Dict[str, Any]:
        """Create a new exploration session."""
        response = requests.post(
            f"{self.api_base}/exploration/sessions",
            json={"url": url, "objectives": objectives}
        )
        response.raise_for_status()
        return response.json()
    
    def start_exploration(self, session_id: str) -> Dict[str, Any]:
        """Start the exploration."""
        response = requests.post(
            f"{self.api_base}/exploration/sessions/{session_id}/start"
        )
        response.raise_for_status()
        return response.json()
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status."""
        response = requests.get(
            f"{self.api_base}/exploration/sessions/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, session_id: str, timeout: int = 300) -> bool:
        """Wait for exploration to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_session_status(session_id)
            session_status = status.get("status", "")
            
            if session_status in ["completed", "failed", "cancelled"]:
                return session_status == "completed"
            
            time.sleep(5)
        
        return False
    
    def generate_specification(self, session_id: str) -> Dict[str, Any]:
        """Generate scraper specification from exploration."""
        response = requests.post(
            f"{self.api_base}/exploration/sessions/{session_id}/generate-spec"
        )
        response.raise_for_status()
        return response.json()
    
    def approve_exploration(
        self,
        session_id: str,
        actor: str,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Approve the exploration summary."""
        response = requests.post(
            f"{self.api_base}/exploration/sessions/{session_id}/approve-exploration",
            json={
                "action": "approve",
                "actor": actor,
                "feedback": feedback
            }
        )
        response.raise_for_status()
        return response.json()
    
    def generate_scraper(
        self,
        session_id: str,
        assertions: Optional[list] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """Generate scraper code with testing."""
        payload = {"max_iterations": max_iterations}
        if assertions:
            payload["assertions"] = assertions
        
        response = requests.post(
            f"{self.api_base}/exploration/sessions/{session_id}/generate-scraper",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_scraper_details(self, session_id: str) -> Dict[str, Any]:
        """Get current scraper details."""
        response = requests.get(
            f"{self.api_base}/exploration/sessions/{session_id}/scraper"
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_generation(self, session_id: str, timeout: int = 600) -> bool:
        """Wait for scraper generation to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                details = self.get_scraper_details(session_id)
                scraper = details.get("scraper", {})
                status = scraper.get("status", "")
                
                if status in ["completed", "failed"]:
                    return status == "completed"
            except requests.exceptions.HTTPError:
                # Scraper not ready yet
                pass
            
            time.sleep(10)
        
        return False
    
    def approve_scraper(
        self,
        session_id: str,
        actor: str,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Approve the generated scraper."""
        response = requests.post(
            f"{self.api_base}/exploration/sessions/{session_id}/approve-scraper",
            json={
                "action": "approve",
                "actor": actor,
                "feedback": feedback
            }
        )
        response.raise_for_status()
        return response.json()
    
    def download_package(self, session_id: str, output_path: str) -> None:
        """Download the finalized scraper package."""
        response = requests.get(
            f"{self.api_base}/exploration/sessions/{session_id}/download"
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
    
    def get_diffs(self, session_id: str) -> Dict[str, Any]:
        """Get iteration diffs."""
        response = requests.get(
            f"{self.api_base}/exploration/sessions/{session_id}/diffs"
        )
        response.raise_for_status()
        return response.json()


def example_workflow():
    """Demonstrate complete approval pipeline workflow."""
    
    print("=" * 70)
    print("APPROVAL PIPELINE EXAMPLE WORKFLOW")
    print("=" * 70)
    
    # Initialize client
    client = ApprovalPipelineClient()
    actor_email = "developer@example.com"
    
    # Step 1: Create exploration session
    print("\n1. Creating exploration session...")
    session = client.create_exploration_session(
        url="https://example.com/products",
        objectives="Extract product names, prices, descriptions, and availability"
    )
    session_id = session["session_id"]
    print(f"   ✓ Created session: {session_id}")
    
    # Step 2: Start exploration
    print("\n2. Starting exploration...")
    result = client.start_exploration(session_id)
    print(f"   ✓ Exploration started: {result['message']}")
    
    # Step 3: Wait for exploration to complete
    print("\n3. Waiting for exploration to complete...")
    if client.wait_for_completion(session_id):
        print("   ✓ Exploration completed successfully")
    else:
        print("   ✗ Exploration did not complete")
        return
    
    # Step 4: Generate specification
    print("\n4. Generating specification from exploration...")
    spec_result = client.generate_specification(session_id)
    print(f"   ✓ Specification generated")
    print(f"\n   Preview:")
    print("   " + "\n   ".join(spec_result["specification"].split("\n")[:10]))
    print("   ...")
    
    # Step 5: Approve exploration
    print("\n5. Approving exploration summary...")
    approval = client.approve_exploration(
        session_id,
        actor_email,
        "Exploration looks comprehensive, proceeding with generation"
    )
    print(f"   ✓ Exploration approved by {approval['approval']['approved_by']}")
    
    # Step 6: Generate scraper with custom assertions
    print("\n6. Generating scraper code with testing...")
    assertions = [
        {
            "type": "not_empty",
            "description": "Extracted data should not be empty"
        },
        {
            "type": "has_field",
            "field": "products",
            "description": "Must have products field"
        },
        {
            "type": "min_items",
            "field": "products",
            "min_count": 1,
            "description": "At least one product"
        }
    ]
    
    gen_result = client.generate_scraper(session_id, assertions, max_iterations=5)
    print(f"   ✓ Generation started: {gen_result['message']}")
    
    # Step 7: Wait for generation
    print("\n7. Waiting for generation and testing...")
    if client.wait_for_generation(session_id):
        print("   ✓ Scraper generation completed")
    else:
        print("   ✗ Generation did not complete")
        return
    
    # Step 8: Review scraper details
    print("\n8. Reviewing generated scraper...")
    details = client.get_scraper_details(session_id)
    scraper = details["scraper"]
    
    print(f"   Version: {scraper['version']}")
    print(f"   Status: {scraper['status']}")
    print(f"   Test Status: {scraper['last_test_status']}")
    print(f"   Framework: {scraper['framework']}")
    print(f"   Language: {scraper['language']}")
    
    if scraper.get("test_results"):
        last_test = scraper["test_results"][-1]
        print(f"\n   Test Results:")
        print(f"   - Assertions Passed: {last_test['assertions_passed']}")
        print(f"   - Assertions Failed: {last_test['assertions_failed']}")
        print(f"   - Execution Time: {last_test.get('execution_time_ms', 0)}ms")
    
    # Step 9: Get iteration diffs
    print("\n9. Reviewing iteration history...")
    diffs = client.get_diffs(session_id)
    print(f"   Total iterations: {len(diffs['diffs'])}")
    for diff in diffs["diffs"]:
        status_icon = "✓" if diff["status"] == "passed" else "✗"
        print(f"   {status_icon} Iteration {diff['iteration']}: {diff['status']}")
    
    # Step 10: Approve scraper
    print("\n10. Approving generated scraper...")
    scraper_approval = client.approve_scraper(
        session_id,
        actor_email,
        "Code quality is good, tests pass, ready for delivery"
    )
    print(f"    ✓ Scraper approved by {scraper_approval['approval']['approved_by']}")
    
    # Step 11: Download package
    print("\n11. Downloading scraper package...")
    output_file = f"scraper_{session_id}.zip"
    client.download_package(session_id, output_file)
    print(f"    ✓ Package downloaded: {output_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nSession ID: {session_id}")
    print(f"Package: {output_file}")
    print("\nThe package contains:")
    print("  - scraper.py (production-ready scraper)")
    print("  - requirements.txt (dependencies)")
    print("  - README.md (documentation)")
    print("  - metadata.json (generation details)")
    print("  - test_results.json (validation results)")
    print("\nExtract and run with:")
    print(f"  unzip {output_file}")
    print("  cd scraper_package")
    print("  pip install -r requirements.txt")
    print("  python scraper.py")


def example_rejection_workflow():
    """Demonstrate approval rejection and feedback."""
    
    print("\n" + "=" * 70)
    print("REJECTION AND FEEDBACK EXAMPLE")
    print("=" * 70)
    
    client = ApprovalPipelineClient()
    
    # Assume we have a session
    session_id = "example-session-id"
    
    # Reject exploration with feedback
    print("\n1. Rejecting exploration with feedback...")
    try:
        response = requests.post(
            f"{client.api_base}/exploration/sessions/{session_id}/approve-exploration",
            json={
                "action": "reject",
                "actor": "reviewer@example.com",
                "feedback": "Need more detailed product attribute extraction. "
                           "Please capture: brand, color, size options."
            }
        )
        print("   ✓ Rejection recorded with feedback")
    except:
        print("   (This is just an example - session doesn't exist)")
    
    # The feedback can be used to:
    # - Update exploration objectives
    # - Re-run exploration with new instructions
    # - Refine the approach
    
    print("\n   Feedback allows for:")
    print("   - Iterative improvement of exploration")
    print("   - Clear communication of requirements")
    print("   - Quality control before code generation")


if __name__ == "__main__":
    import sys
    
    print("\nApproval Pipeline API Example")
    print("=" * 70)
    print("\nThis script demonstrates the complete workflow:")
    print("  1. Create exploration session")
    print("  2. Run exploration")
    print("  3. Generate specification")
    print("  4. Approve exploration")
    print("  5. Generate and test scraper")
    print("  6. Review results")
    print("  7. Approve scraper")
    print("  8. Download package")
    print("\nNote: Requires running Flask server with OPENAI_API_KEY configured")
    print("=" * 70)
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        try:
            example_workflow()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nMake sure:")
            print("  - Flask server is running")
            print("  - OPENAI_API_KEY is configured")
            print("  - Target URL is accessible")
    else:
        print("\nTo run the example:")
        print("  python approval_pipeline_example.py run")
        print("\nOr import and use the ApprovalPipelineClient class in your code.")
