# Code Generation and Approval Pipeline

This document describes the complete code generation and approval pipeline that bridges exploration to scraper delivery.

## Overview

The approval pipeline transforms exploration findings into production-ready scraper code through a multi-stage workflow with user approval gates, automated testing, and iterative refinement.

## Architecture

### Components

1. **Data Models** (`app/models/`)
   - `ApprovalGate` - Manages approval workflow with status tracking
   - `GeneratedScraper` - Stores generated code, versions, and metadata
   - `ScraperTestResult` - Captures test execution results and assertions

2. **Services** (`app/services/`)
   - `ScraperGenerator` - LLM-powered code generation from exploration logs
   - `ScraperTester` - Automated testing harness with configurable assertions
   - `ApprovalPipeline` - Orchestrates the entire workflow

3. **API Endpoints** (`app/api/routes.py`)
   - Specification generation
   - Approval management
   - Code generation and testing
   - Package download

## Workflow

### Stage 1: Exploration Summary Generation

**Endpoint:** `POST /api/v1/exploration/sessions/{id}/generate-spec`

Transforms exploration logs into a structured specification:
- Target URL and objectives
- Actions performed during exploration
- Page structure observations
- Agent analysis and insights

**Approval Gate:** `EXPLORATION_SUMMARY`

The user must review and approve the exploration summary before proceeding.

### Stage 2: Exploration Approval

**Endpoint:** `POST /api/v1/exploration/sessions/{id}/approve-exploration`

**Request:**
```json
{
  "action": "approve",
  "actor": "user@example.com",
  "feedback": "Looks comprehensive, proceed with generation"
}
```

**Actions:**
- `approve` - Allows progression to code generation
- `reject` - Blocks generation, feedback captured for iteration

### Stage 3: Scraper Generation with Testing

**Endpoint:** `POST /api/v1/exploration/sessions/{id}/generate-scraper`

**Request:**
```json
{
  "max_iterations": 5,
  "assertions": [
    {
      "type": "not_empty",
      "description": "Extracted data should not be empty"
    },
    {
      "type": "has_field",
      "field": "url",
      "description": "Must include source URL"
    },
    {
      "type": "min_items",
      "field": "items",
      "min_count": 1,
      "description": "At least one item extracted"
    }
  ]
}
```

**Process:**
1. Generates Playwright/Python scraper code using OpenAI GPT-4
2. Tests the generated code against the target URL
3. If tests fail, refines the code with error feedback
4. Iterates until tests pass or max iterations reached

**Assertion Types:**
- `not_empty` - Data is not empty
- `has_field` - Specific field exists
- `field_not_empty` - Field has a value
- `min_items` - List has minimum items
- `field_type` - Field matches expected type
- `custom` - Custom expression evaluation

### Stage 4: Scraper Approval

**Endpoint:** `POST /api/v1/exploration/sessions/{id}/approve-scraper`

**Request:**
```json
{
  "action": "approve",
  "actor": "user@example.com",
  "feedback": "Code looks good, test results satisfactory"
}
```

**Approval Gate:** `SCRAPER_GENERATION`

User reviews:
- Generated code
- Test results
- Execution time
- Assertion outcomes

If approved, creates `FINAL_DELIVERY` gate.

### Stage 5: Download Package

**Endpoint:** `GET /api/v1/exploration/sessions/{id}/download`

**Requirements:**
- `FINAL_DELIVERY` gate must be approved
- Returns ZIP file containing:
  - `scraper.py` - Production-ready scraper script
  - `requirements.txt` - Python dependencies
  - `README.md` - Documentation and usage
  - `metadata.json` - Generation metadata
  - `test_results.json` - Test execution details

## Approval Sequencing

The pipeline enforces strict sequencing:

1. **Exploration Summary** must be approved before **Scraper Generation**
2. **Scraper Generation** must be approved before **Final Delivery**
3. **Final Delivery** must be approved before **Download**

Attempting to skip stages returns an error with clear messaging.

## Iterative Refinement

The code generator supports iterative refinement:

1. **Initial Generation** - Creates scraper from specification
2. **Testing** - Runs against target URL with assertions
3. **Error Analysis** - Extracts errors and failure details
4. **Refinement** - Regenerates with error feedback
5. **Retry** - Tests refined version

This continues until:
- Tests pass successfully, OR
- Maximum iterations reached (default: 5)

Each iteration increments the version number and preserves history.

## Testing Harness

### Features

- **Subprocess Execution** - Isolates scraper in safe environment
- **Timeout Protection** - Prevents infinite loops
- **Console Capture** - Records stdout/stderr
- **JSON Parsing** - Validates output format
- **Assertion Framework** - Configurable validation rules

### Default Assertions

If no custom assertions provided, applies:
1. Data is not empty
2. Data includes source URL field

### Custom Assertions

Users can specify custom validation:

```json
{
  "type": "custom",
  "expression": "len(data['products']) >= 5 and all('price' in p for p in data['products'])",
  "description": "At least 5 products with prices"
}
```

## API Reference

### Generate Specification

```
POST /api/v1/exploration/sessions/{id}/generate-spec
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc-123",
  "specification": "# Web Scraper Specification\n...",
  "approval": {
    "approval_id": "def-456",
    "approval_type": "exploration_summary",
    "status": "pending",
    "summary": "# Exploration Summary...",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Approve Exploration

```
POST /api/v1/exploration/sessions/{id}/approve-exploration
```

**Body:**
```json
{
  "action": "approve|reject",
  "actor": "user@example.com",
  "feedback": "Optional feedback"
}
```

### Generate Scraper

```
POST /api/v1/exploration/sessions/{id}/generate-scraper
```

**Body:**
```json
{
  "max_iterations": 5,
  "assertions": [...]
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc-123",
  "status": "generating",
  "message": "Scraper generation started in background"
}
```

### Test Scraper

```
POST /api/v1/exploration/sessions/{id}/test-scraper
```

**Body:**
```json
{
  "assertions": [...]
}
```

### Get Scraper Details

```
GET /api/v1/exploration/sessions/{id}/scraper
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc-123",
  "scraper": {
    "scraper_id": "xyz-789",
    "version": 2,
    "status": "completed",
    "code": "import asyncio\n...",
    "language": "python",
    "framework": "playwright",
    "test_results": [...],
    "last_test_status": "passed"
  },
  "approval_gates": [...]
}
```

### Get Iteration Diffs

```
GET /api/v1/exploration/sessions/{id}/diffs
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc-123",
  "diffs": [
    {
      "iteration": 1,
      "version": 1,
      "timestamp": "2024-01-01T00:00:00Z",
      "status": "failed",
      "test_summary": {
        "passed": 2,
        "failed": 1,
        "errors": true
      },
      "error": "NameError: name 'products' is not defined"
    },
    {
      "iteration": 2,
      "version": 2,
      "timestamp": "2024-01-01T00:01:00Z",
      "status": "passed",
      "test_summary": {
        "passed": 3,
        "failed": 0,
        "errors": false
      }
    }
  ]
}
```

### Download Package

```
GET /api/v1/exploration/sessions/{id}/download
```

**Response:** ZIP file (`application/zip`)

## Configuration

### Environment Variables

```bash
# Required for code generation
OPENAI_API_KEY=sk-...

# Optional: Configure model (default: gpt-4)
OPENAI_MODEL=gpt-4

# Optional: Test timeout (default: 60 seconds)
SCRAPER_TEST_TIMEOUT=60

# Optional: Max generation iterations (default: 5)
MAX_SCRAPER_ITERATIONS=5
```

## Error Handling

### Common Errors

**Missing API Key:**
```json
{
  "error": "Code generation not configured. OpenAI API key required."
}
```

**Approval Sequencing Violation:**
```json
{
  "error": "Exploration summary must be approved before scraper generation"
}
```

**Generation Failure:**
```json
{
  "error": "Failed to generate specification: Connection timeout"
}
```

**Test Timeout:**
```json
{
  "error": "Scraper execution timed out after 60 seconds"
}
```

## Best Practices

### 1. Comprehensive Exploration

Ensure exploration captures:
- Page structure and key elements
- Navigation patterns
- Data extraction points
- Dynamic content handling

### 2. Clear Objectives

Write specific, actionable objectives:
- ✅ "Extract product names, prices, and availability from category pages"
- ❌ "Get product data"

### 3. Appropriate Assertions

Define assertions that match requirements:
- Verify required fields exist
- Check data types
- Validate minimum/maximum counts
- Test for specific patterns

### 4. Review Before Approval

Always review:
- Exploration summary completeness
- Generated code quality
- Test results and assertions
- Error messages and stack traces

### 5. Iterative Improvement

Use rejection feedback to refine:
- Provide specific issues in feedback
- Suggest improvements
- Reference specific requirements

## Examples

### Complete Workflow Example

```bash
# 1. Create exploration session
curl -X POST http://localhost:5000/api/v1/exploration/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/products",
    "objectives": "Extract product names, prices, and ratings"
  }'

# 2. Start exploration
curl -X POST http://localhost:5000/api/v1/exploration/sessions/{id}/start

# 3. Wait for completion, then generate spec
curl -X POST http://localhost:5000/api/v1/exploration/sessions/{id}/generate-spec

# 4. Approve exploration
curl -X POST http://localhost:5000/api/v1/exploration/sessions/{id}/approve-exploration \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "actor": "developer@example.com"
  }'

# 5. Generate scraper
curl -X POST http://localhost:5000/api/v1/exploration/sessions/{id}/generate-scraper \
  -H "Content-Type: application/json" \
  -d '{
    "max_iterations": 5,
    "assertions": [
      {"type": "has_field", "field": "products"},
      {"type": "min_items", "field": "products", "min_count": 1}
    ]
  }'

# 6. Check status periodically
curl http://localhost:5000/api/v1/exploration/sessions/{id}/scraper

# 7. Review and approve scraper
curl -X POST http://localhost:5000/api/v1/exploration/sessions/{id}/approve-scraper \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "actor": "developer@example.com"
  }'

# 8. Download package
curl -O http://localhost:5000/api/v1/exploration/sessions/{id}/download
```

## Security Considerations

1. **Code Execution** - Generated scrapers run in isolated subprocesses
2. **Timeout Protection** - All executions have configurable timeouts
3. **Input Validation** - Assertions and feedback are validated
4. **Approval Tracking** - All approvals logged with actor and timestamp
5. **Package Integrity** - Generated packages include verification metadata

## Limitations

1. **LLM Dependency** - Requires OpenAI API access
2. **Language Support** - Currently Python/Playwright only
3. **Testing Scope** - Tests run against live URLs only
4. **Iteration Limit** - Maximum refinement iterations enforced
5. **Synchronous Testing** - Test execution blocks during run

## Future Enhancements

- Support for additional frameworks (Selenium, Scrapy)
- Multi-language generation (Node.js, Go)
- Visual diff viewer for code iterations
- Scheduled scraper execution
- Data validation rules
- Performance benchmarking
- Cloud deployment integration
