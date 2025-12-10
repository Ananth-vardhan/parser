# Parse.bot API Behavior & Request Investigation

## Document Overview

**Investigation Date:** December 10, 2024  
**Investigator:** AI Research Team  
**Status:** Initial Discovery Phase  
**Confidence Level:** Medium (based on public API endpoints and network traces)

This document represents a reverse-engineering effort to understand Parse.bot's API architecture, request patterns, and data extraction workflow based on publicly available information. All findings are derived from official Parse.bot endpoints, network traces, and public documentation.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Investigation Methodology](#investigation-methodology)
3. [API Architecture](#api-architecture)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Patterns](#requestresponse-patterns)
6. [Authentication & Authorization](#authentication--authorization)
7. [Proxy Infrastructure](#proxy-infrastructure)
8. [Data Extraction Workflow](#data-extraction-workflow)
9. [Throttling & Rate Limiting](#throttling--rate-limiting)
10. [Uncertainties & Gaps](#uncertainties--gaps)
11. [Evidence Sources](#evidence-sources)

---

## Executive Summary

Parse.bot is a cloud-based web scraping service built on **FastAPI (Python)** with AWS Lambda integration for asynchronous scraper execution. The service provides a natural-language interface for web scraping, backed by a REST API exposed at `https://api.parse.bot`.

**Key Findings:**
- **Backend:** FastAPI with AWS Lambda workers
- **Infrastructure:** Cloudflare CDN, proxy pool management
- **API Style:** RESTful JSON API with OpenAPI/Swagger documentation
- **Authentication:** Session-based (inferred from frontend providers)
- **Scraping Architecture:** Multi-endpoint scraper execution model
- **Natural Language Processing:** Query endpoint for NLP-based scraper modification

---

## Investigation Methodology

### Discovery Steps

1. **Initial Reconnaissance**
   - Accessed main website: `https://www.parse.bot`
   - Attempted documentation URL: `https://docs.parse.bot` (deployment not found)
   - Probed API endpoint: `https://api.parse.bot`

2. **API Documentation Discovery**
   - Located Swagger UI at: `https://api.parse.bot/docs`
   - Retrieved OpenAPI specification: `https://api.parse.bot/openapi.json`

3. **Network Trace Analysis**
   - Examined HTTP response headers
   - Analyzed response payloads for system behavior
   - Tested health check and status endpoints

4. **Frontend Analysis**
   - Examined Next.js hydration data
   - Identified client-side providers (Auth, Conversation, PostHog)

### Tools Used

```bash
# HTTP requests
curl -i -s "https://api.parse.bot/health" -A "Mozilla/5.0"

# OpenAPI spec retrieval
curl -s "https://api.parse.bot/openapi.json" | python3 -m json.tool

# Header inspection
curl -I "https://api.parse.bot"
```

---

## API Architecture

### Technology Stack

| Component | Technology | Evidence Source |
|-----------|-----------|-----------------|
| **Backend Framework** | FastAPI (Python) | `x-service: fastapi` header, Swagger UI |
| **API Version** | OpenAPI 3.1.0 | `/openapi.json` specification |
| **CDN/Edge** | Cloudflare | HTTP headers, cf-ray |
| **Execution Layer** | AWS Lambda | OpenAPI description, health check response |
| **Frontend** | Next.js (React) | Server-side rendering artifacts |
| **Analytics** | PostHog | Frontend provider detection |
| **Proxy Provider** | Oxylabs ISP Proxies | Proxy pool status endpoint |

### System Architecture Diagram

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloudflare CDN/WAF        │
│   (Edge Layer)              │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│   FastAPI Backend           │
│   https://api.parse.bot     │
│   ┌───────────────────────┐ │
│   │ Route Handlers        │ │
│   │ - Health Check        │ │
│   │ - Scraper Execution   │ │
│   │ - Query Processing    │ │
│   │ - Proxy Management    │ │
│   └───────────────────────┘ │
└────────────┬────────────────┘
             │
             ├──────────────────┐
             ▼                  ▼
    ┌────────────────┐  ┌─────────────┐
    │  AWS Lambda    │  │ Proxy Pool  │
    │  Workers       │  │ (Oxylabs)   │
    │  (Scrapers)    │  │ 20 proxies  │
    └────────────────┘  └─────────────┘
             │
             ▼
    ┌────────────────┐
    │  Target Sites  │
    └────────────────┘
```

### Deployment Information

From HTTP headers:
- **Build Time:** `20251124-125017-8c898fe`
- **Git Commit:** `8c898feea81c41cba5cfd391e5fefb1a5870da07`
- **Service Identifier:** `fastapi-scraper`

---

## API Endpoints

### Complete Endpoint Inventory

| Endpoint | Method | Purpose | Authentication Required |
|----------|--------|---------|------------------------|
| `/health` | GET | Service health check | No |
| `/proxy-pool/status` | GET | Proxy pool monitoring | No (⚠️ likely should be protected) |
| `/scraper/{scraper_id}/{endpoint_name}` | POST | Execute scraper endpoint | Yes (assumed) |
| `/scraper/{scraper_id}/query` | POST | Natural language scraper query | Yes (assumed) |
| `/scraper/{scraper_id}` | GET | Get scraper information | Yes (assumed) |

### Endpoint Details

#### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** System health verification and Lambda availability check

**Request:**
```bash
curl -X GET "https://api.parse.bot/health"
```

**Response:**
```json
{
  "status": "healthy",
  "service": "fastapi-scraper",
  "timestamp": "2025-12-10T19:14:26.180749",
  "lambda_available": true
}
```

**Fields:**
- `status`: Service health status (`healthy` | `degraded` | `down`)
- `service`: Service identifier
- `timestamp`: ISO 8601 timestamp
- `lambda_available`: Boolean indicating Lambda worker availability

**Rate Limiting:** None observed (public endpoint)

---

#### 2. Proxy Pool Status

**Endpoint:** `GET /proxy-pool/status`

**Purpose:** Monitor proxy pool health and availability

**Request:**
```bash
curl -X GET "https://api.parse.bot/proxy-pool/status"
```

**Response:**
```json
{
  "status": "ok",
  "pool": {
    "pool_size": 20,
    "max_size": 20,
    "min_size": 5,
    "current_index": 1,
    "last_refresh": "2025-12-10T18:25:29.414856",
    "needs_refill": false,
    "proxies": [
      "isp.oxylabs.io:8033",
      "isp.oxylabs.io:8161",
      "193.23.192.101:3129",
      "108.165.145.160:3129"
    ]
  },
  "timestamp": "2025-12-10T19:14:40.205971"
}
```

**⚠️ Security Concern:** This endpoint exposes internal infrastructure details including proxy addresses. Should likely be protected.

**Pool Management:**
- **Dynamic sizing:** 5-20 proxies
- **Auto-refresh:** Timestamp indicates last refresh
- **Round-robin rotation:** `current_index` suggests sequential proxy selection
- **Mix of providers:** Oxylabs ISP and direct IP addresses

---

#### 3. Run Scraper Endpoint

**Endpoint:** `POST /scraper/{scraper_id}/{endpoint_name}`

**Purpose:** Execute a specific endpoint of a configured scraper

**Path Parameters:**
- `scraper_id` (string): Unique identifier for the scraper instance
- `endpoint_name` (string): Name of the endpoint to execute (supports multi-endpoint scrapers)

**Request Body Schema:**
```json
{
  "type": "object",
  "additionalProperties": true,
  "description": "Request model for scraper execution"
}
```

**Example Request (Hypothetical):**
```bash
curl -X POST "https://api.parse.bot/scraper/abc123/extract_products" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "url": "https://example.com/products",
    "options": {
      "wait_for": "selector",
      "timeout": 30000
    }
  }'
```

**⚠️ Uncertainty:** 
- Exact request body structure is flexible (`additionalProperties: true`)
- Response format not documented in OpenAPI spec
- Authentication mechanism unclear

---

#### 4. Query Scraper (Natural Language)

**Endpoint:** `POST /scraper/{scraper_id}/query`

**Purpose:** Query or modify scraper behavior using natural language

**Path Parameters:**
- `scraper_id` (string): Scraper to query/modify

**Request Body Schema:**
```json
{
  "type": "object",
  "additionalProperties": true
}
```

**Example Request (Hypothetical):**
```bash
curl -X POST "https://api.parse.bot/scraper/abc123/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "Extract the product prices and convert them to USD",
    "context": {}
  }'
```

**Use Cases:**
- Modify extraction rules
- Add new data fields
- Change scraping behavior
- Query scraper capabilities

**⚠️ Uncertainty:** 
- NLP processing backend (OpenAI/Gemini?) not exposed in API
- Query syntax and capabilities unknown
- Response format undocumented

---

#### 5. Get Scraper Info

**Endpoint:** `GET /scraper/{scraper_id}`

**Purpose:** Retrieve scraper configuration and metadata

**Path Parameters:**
- `scraper_id` (string): Scraper identifier

**Example Request:**
```bash
curl -X GET "https://api.parse.bot/scraper/abc123" \
  -H "Authorization: Bearer <token>"
```

**Expected Response (Inferred):**
```json
{
  "scraper_id": "abc123",
  "name": "Product Scraper",
  "endpoints": ["extract_products", "get_details"],
  "created_at": "2024-12-01T10:00:00Z",
  "last_run": "2024-12-10T19:00:00Z",
  "status": "active"
}
```

---

## Request/Response Patterns

### HTTP Headers

#### Standard Request Headers

```http
GET /health HTTP/2
Host: api.parse.bot
User-Agent: Mozilla/5.0 (compatible)
Accept: application/json
```

#### Standard Response Headers

```http
HTTP/2 200
date: Wed, 10 Dec 2025 19:14:26 GMT
content-type: application/json
server: cloudflare
x-build-time: 20251124-125017-8c898fe
x-git-commit: 8c898feea81c41cba5cfd391e5fefb1a5870da07
x-service: fastapi
cf-cache-status: DYNAMIC
cf-ray: 9abf10b16d0b22ee-ORD
```

**Custom Headers:**
- `x-build-time`: Build timestamp and commit hash
- `x-git-commit`: Full git commit hash
- `x-service`: Service type identifier

### Content Type

All endpoints use `application/json` for both requests and responses.

### Error Responses

Based on OpenAPI spec, validation errors follow this format:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**HTTP Status Codes:**
- `200`: Success
- `404`: Not Found (invalid endpoint)
- `422`: Validation Error (malformed request)
- `401`: Unauthorized (authentication required - inferred)
- `429`: Too Many Requests (rate limit - inferred)

---

## Authentication & Authorization

### Authentication Mechanism

**Evidence:**
- Frontend uses `AuthProvider` component (Next.js)
- No API key parameters in OpenAPI spec
- Protected endpoints lack public documentation

**Likely Approach:** Session-based authentication with HTTP-only cookies

### Authentication Flow (Inferred)

```
┌─────────┐                ┌──────────────┐                ┌─────────┐
│ Client  │                │   Frontend   │                │   API   │
│ Browser │                │  (Next.js)   │                │         │
└────┬────┘                └──────┬───────┘                └────┬────┘
     │                            │                             │
     │  1. Login Request          │                             │
     ├───────────────────────────>│                             │
     │                            │  2. Authenticate            │
     │                            ├────────────────────────────>│
     │                            │                             │
     │                            │  3. Session Cookie          │
     │                            │<────────────────────────────┤
     │  4. Session Cookie         │                             │
     │<───────────────────────────┤                             │
     │                            │                             │
     │  5. API Request (with cookie)                           │
     ├─────────────────────────────────────────────────────────>│
     │                            │                             │
     │  6. API Response           │                             │
     │<─────────────────────────────────────────────────────────┤
     │                            │                             │
```

### Alternative Authentication Methods

**Possible but unconfirmed:**
- Bearer tokens (JWT)
- API keys in headers (`X-API-Key`)
- OAuth 2.0 (given oauth2-redirect reference in Swagger UI)

**⚠️ Uncertainty:** 
- No public authentication documentation available
- Requires account creation to test auth flow
- Production authentication may differ from documented patterns

---

## Proxy Infrastructure

### Proxy Pool Architecture

Parse.bot maintains a managed pool of residential/ISP proxies for scraping operations:

**Configuration:**
- **Provider:** Oxylabs ISP Proxies
- **Pool Size:** 20 proxies (configurable 5-20)
- **Rotation:** Round-robin with current index tracking
- **Refresh Interval:** Automatic (timestamp-based)

### Proxy Distribution

**Identified Providers:**

1. **Oxylabs ISP Proxies** (~70% of pool)
   - Format: `isp.oxylabs.io:PORT`
   - Ports: 8033, 8161, 8186, 8227, 8502, 8299, etc.

2. **Direct IP Proxies** (~30% of pool)
   - Format: `IP:3129`
   - Examples:
     - `193.23.192.101:3129`
     - `108.165.145.160:3129`
     - `108.165.145.98:3129`

### Proxy Rotation Strategy

```python
# Inferred rotation algorithm
def get_next_proxy(pool):
    """Round-robin proxy selection"""
    current = pool['current_index']
    proxy = pool['proxies'][current]
    pool['current_index'] = (current + 1) % pool['pool_size']
    return proxy
```

**Benefits:**
- Distributes requests across proxies
- Reduces IP-based blocking
- Maintains request throughput

### Health Monitoring

The `/proxy-pool/status` endpoint provides real-time monitoring:
- Pool size utilization
- Last refresh timestamp
- Refill status indicator
- Complete proxy list (security concern)

---

## Data Extraction Workflow

### Scraper Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Scraper Execution Lifecycle               │
└──────────────────────────────────────────────────────────────┘

1. Client Submission
   ┌─────────────────┐
   │  POST /scraper/ │
   │  {scraper_id}/  │
   │  {endpoint}     │
   └────────┬────────┘
            │
            ▼
2. Request Validation & Queuing
   ┌─────────────────┐
   │  FastAPI        │
   │  Validates JSON │
   │  Queues Job     │
   └────────┬────────┘
            │
            ▼
3. Lambda Invocation
   ┌─────────────────┐
   │  AWS Lambda     │
   │  Worker Spawn   │
   └────────┬────────┘
            │
            ├──────────────┐
            ▼              ▼
4a. Proxy Selection    4b. Scraper Config Load
   ┌──────────────┐       ┌─────────────────┐
   │ Get Proxy    │       │ Load Endpoint   │
   │ from Pool    │       │ Configuration   │
   └──────┬───────┘       └────────┬────────┘
          │                        │
          └────────┬───────────────┘
                   ▼
5. HTTP Request Execution
   ┌─────────────────┐
   │  Target Site    │
   │  via Proxy      │
   └────────┬────────┘
            │
            ▼
6. HTML Parsing & Extraction
   ┌─────────────────┐
   │  Parse HTML     │
   │  Extract Data   │
   │  (CSS/XPath)    │
   └────────┬────────┘
            │
            ▼
7. AI Post-Processing (Optional)
   ┌─────────────────┐
   │  NLP Refinement │
   │  Data Cleaning  │
   └────────┬────────┘
            │
            ▼
8. Response Assembly
   ┌─────────────────┐
   │  JSON Response  │
   │  Return to API  │
   └────────┬────────┘
            │
            ▼
9. Client Response
   ┌─────────────────┐
   │  HTTP 200       │
   │  {data}         │
   └─────────────────┘
```

### Multi-Endpoint Architecture

Parse.bot supports **multiple endpoints per scraper**, allowing:

**Use Case Example:**
```
Scraper: "E-commerce Product Scraper"
├── Endpoint 1: "list_products"    (listing pages)
├── Endpoint 2: "product_details"  (detail pages)
└── Endpoint 3: "reviews"          (review pages)
```

**Benefits:**
- Modular scraper design
- Reusable configurations
- Different extraction rules per page type

### Natural Language Query Integration

The `/query` endpoint enables runtime scraper modification:

**Example Workflow:**
```
1. User: "Also extract the product ratings"
   ↓
2. API: Send to NLP processor (GPT-4/Gemini)
   ↓
3. NLP: Generate selector/extraction logic
   ↓
4. API: Update scraper configuration
   ↓
5. Response: Confirmation + updated schema
```

**⚠️ Speculation:** This likely uses prompt engineering with OpenAI/Gemini to:
- Interpret natural language requests
- Generate CSS selectors or XPath expressions
- Modify extraction schemas dynamically

---

## Throttling & Rate Limiting

### Observed Behavior

**Public Endpoints:**
- `/health` - No rate limiting observed
- `/proxy-pool/status` - No rate limiting observed

**Protected Endpoints:**
- Rate limiting likely present but untested (no authentication)

### Inferred Rate Limiting Strategy

Based on industry best practices and infrastructure:

| Endpoint Type | Likely Limit | Time Window |
|---------------|-------------|-------------|
| Health checks | Unlimited | - |
| Scraper execution | 60 requests | per minute |
| Query endpoint | 20 requests | per minute |
| Scraper info | 100 requests | per minute |

**Cloudflare Integration:**
Cloudflare provides DDoS protection and may enforce:
- Connection limits per IP
- Request rate per IP
- JavaScript challenge for suspicious traffic

### Concurrency Limits

**Lambda-Based Execution:**
- AWS Lambda has default concurrency limits (1000 per region)
- Parse.bot likely has account-based concurrency limits
- Prevents resource exhaustion from parallel scraping

**⚠️ Uncertainty:**
- No public documentation on rate limits
- Actual limits may vary by subscription tier
- Testing requires authenticated requests

---

## Uncertainties & Gaps

### Critical Unknowns

1. **Authentication Details**
   - ❓ Exact authentication mechanism (cookies vs. tokens)
   - ❓ API key provisioning process
   - ❓ Token expiration and refresh logic
   - ❓ OAuth provider support

2. **Response Formats**
   - ❓ Scraper execution response structure
   - ❓ Error handling and retry logic
   - ❓ Streaming vs. batch response delivery
   - ❓ Pagination for large datasets

3. **Pricing & Limits**
   - ❓ Rate limiting specifics
   - ❓ Scraper execution quotas
   - ❓ Concurrent request limits
   - ❓ Data volume restrictions

4. **AI Integration**
   - ❓ Which LLM provider (OpenAI vs. Gemini)
   - ❓ Prompt engineering strategies
   - ❓ Cost attribution for AI queries
   - ❓ Model selection options

5. **Data Storage**
   - ❓ Scraper configuration persistence
   - ❓ Historical run data retention
   - ❓ Result caching mechanisms
   - ❓ Database backend (PostgreSQL? DynamoDB?)

6. **Webhook Support**
   - ❓ Async job notifications
   - ❓ Webhook configuration endpoints
   - ❓ Retry and delivery guarantees

### Areas Requiring Testing

To validate hypotheses and fill gaps:

```bash
# 1. Authentication flow testing
# Create account → Capture auth tokens → Test API access

# 2. Scraper execution response format
# Execute sample scraper → Analyze response structure

# 3. Rate limit discovery
# Burst requests → Document throttling behavior

# 4. Error scenarios
# Test malformed requests → Document error formats

# 5. Natural language query capabilities
# Test query endpoint → Document NLP limitations
```

---

## Evidence Sources

### Primary Sources

| Source | Type | URL | Reliability |
|--------|------|-----|-------------|
| OpenAPI Specification | Official | `https://api.parse.bot/openapi.json` | ✅ High |
| Swagger UI | Official | `https://api.parse.bot/docs` | ✅ High |
| Health Endpoint | Live API | `https://api.parse.bot/health` | ✅ High |
| Proxy Status | Live API | `https://api.parse.bot/proxy-pool/status` | ✅ High |
| HTTP Headers | Network Trace | Response headers | ✅ High |

### Secondary Sources

| Source | Type | Reliability |
|--------|------|-------------|
| Frontend HTML/JS | Reverse Engineering | ⚠️ Medium |
| Infrastructure inference | Analysis | ⚠️ Medium |
| Behavioral assumptions | Speculation | ❌ Low |

### Verification Methodology

For each finding, confidence is assessed based on:

1. **Direct Observation** (✅ High)
   - Documented in OpenAPI spec
   - Observable in API responses
   - Confirmed via network traces

2. **Strong Inference** (⚠️ Medium)
   - Consistent with observed patterns
   - Industry standard practices
   - Multiple supporting indicators

3. **Speculation** (❌ Low)
   - No direct evidence
   - Based on common patterns
   - Requires testing to confirm

---

## Recommendations for Future Investigation

### Immediate Next Steps

1. **Create Test Account**
   - Sign up at `https://www.parse.bot`
   - Capture authentication flow
   - Document onboarding process

2. **Authenticated API Testing**
   - Execute scraper endpoints
   - Test query functionality
   - Measure rate limits

3. **Frontend Code Analysis**
   - Examine Next.js page sources
   - Identify API client code
   - Map client-side workflows

4. **Network Traffic Capture**
   - Use browser DevTools
   - Record WebSocket connections (if any)
   - Analyze request cadence

### Long-Term Research Goals

1. **Comprehensive API Documentation**
   - Document all request/response formats
   - Create working code examples
   - Build API client library

2. **Performance Benchmarking**
   - Measure scraper execution times
   - Test concurrent request limits
   - Evaluate proxy pool performance

3. **AI Capabilities Assessment**
   - Test natural language query boundaries
   - Evaluate extraction accuracy
   - Compare OpenAI vs. Gemini behavior (if selectable)

4. **Cost Modeling**
   - Understand pricing tiers
   - Calculate cost per scrape
   - Identify optimization strategies

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2024-12-10 | Initial investigation and documentation | AI Research Team |

---

## Appendix A: Raw OpenAPI Specification

<details>
<summary>Click to expand full OpenAPI JSON</summary>

```json
{
    "openapi": "3.1.0",
    "info": {
        "title": "Parse Scraper Service",
        "description": "Async scraper execution service with AWS Lambda integration",
        "version": "1.0.0"
    },
    "paths": {
        "/health": {
            "get": {
                "summary": "Health Check",
                "description": "Health check endpoint",
                "operationId": "health_check_health_get",
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    }
                }
            }
        },
        "/proxy-pool/status": {
            "get": {
                "summary": "Get Proxy Pool Status",
                "description": "Get proxy pool status for monitoring",
                "operationId": "get_proxy_pool_status_proxy_pool_status_get",
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    }
                }
            }
        },
        "/scraper/{scraper_id}/{endpoint_name}": {
            "post": {
                "summary": "Run Scraper Endpoint",
                "description": "Execute a specific endpoint of a scraper (multi-endpoint support)",
                "operationId": "run_scraper_endpoint_scraper__scraper_id___endpoint_name__post",
                "parameters": [
                    {
                        "name": "scraper_id",
                        "in": "path",
                        "required": true,
                        "schema": {
                            "type": "string",
                            "title": "Scraper Id"
                        }
                    },
                    {
                        "name": "endpoint_name",
                        "in": "path",
                        "required": true,
                        "schema": {
                            "type": "string",
                            "title": "Endpoint Name"
                        }
                    }
                ],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ScraperRunRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/scraper/{scraper_id}/query": {
            "post": {
                "summary": "Query Scraper",
                "description": "Query/modify a scraper with natural language",
                "operationId": "query_scraper_scraper__scraper_id__query_post",
                "parameters": [
                    {
                        "name": "scraper_id",
                        "in": "path",
                        "required": true,
                        "schema": {
                            "type": "string",
                            "title": "Scraper Id"
                        }
                    }
                ],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "additionalProperties": true,
                                "title": "Query Data"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/scraper/{scraper_id}": {
            "get": {
                "summary": "Get Scraper Info",
                "description": "Get scraper information",
                "operationId": "get_scraper_info_scraper__scraper_id__get",
                "parameters": [
                    {
                        "name": "scraper_id",
                        "in": "path",
                        "required": true,
                        "schema": {
                            "type": "string",
                            "title": "Scraper Id"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/HTTPValidationError"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "HTTPValidationError": {
                "properties": {
                    "detail": {
                        "items": {
                            "$ref": "#/components/schemas/ValidationError"
                        },
                        "type": "array",
                        "title": "Detail"
                    }
                },
                "type": "object",
                "title": "HTTPValidationError"
            },
            "ScraperRunRequest": {
                "properties": {},
                "additionalProperties": true,
                "type": "object",
                "title": "ScraperRunRequest",
                "description": "Request model for scraper execution"
            },
            "ValidationError": {
                "properties": {
                    "loc": {
                        "items": {
                            "anyOf": [
                                {
                                    "type": "string"
                                },
                                {
                                    "type": "integer"
                                }
                            ]
                        },
                        "type": "array",
                        "title": "Location"
                    },
                    "msg": {
                        "type": "string",
                        "title": "Message"
                    },
                    "type": {
                        "type": "string",
                        "title": "Error Type"
                    }
                },
                "type": "object",
                "required": [
                    "loc",
                    "msg",
                    "type"
                ],
                "title": "ValidationError"
            }
        }
    }
}
```

</details>

---

## Appendix B: Example HTTP Traces

### Health Check Request/Response

```http
GET /health HTTP/2
Host: api.parse.bot
User-Agent: Mozilla/5.0
Accept: application/json

HTTP/2 200
date: Wed, 10 Dec 2025 19:14:26 GMT
content-type: application/json
content-length: 113
server: cloudflare
x-build-time: 20251124-125017-8c898fe
x-git-commit: 8c898feea81c41cba5cfd391e5fefb1a5870da07
x-service: fastapi
cf-cache-status: DYNAMIC
cf-ray: 9abf10b16d0b22ee-ORD

{
  "status": "healthy",
  "service": "fastapi-scraper",
  "timestamp": "2025-12-10T19:14:26.180749",
  "lambda_available": true
}
```

### Proxy Pool Status Request/Response

```http
GET /proxy-pool/status HTTP/2
Host: api.parse.bot
User-Agent: Mozilla/5.0
Accept: application/json

HTTP/2 200
date: Wed, 10 Dec 2025 19:14:40 GMT
content-type: application/json
server: cloudflare
x-build-time: 20251124-125017-8c898fe
x-service: fastapi

{
  "status": "ok",
  "pool": {
    "pool_size": 20,
    "max_size": 20,
    "min_size": 5,
    "current_index": 1,
    "last_refresh": "2025-12-10T18:25:29.414856",
    "needs_refill": false,
    "proxies": [
      "isp.oxylabs.io:8033",
      "isp.oxylabs.io:8161",
      "isp.oxylabs.io:8186",
      "193.23.192.101:3129",
      "isp.oxylabs.io:8227",
      "isp.oxylabs.io:8502",
      "108.165.145.160:3129",
      "108.165.145.98:3129",
      "108.165.145.228:3129",
      "isp.oxylabs.io:8299",
      "isp.oxylabs.io:8490",
      "isp.oxylabs.io:8385",
      "193.23.192.78:3129",
      "isp.oxylabs.io:8109",
      "193.23.192.110:3129",
      "isp.oxylabs.io:8297",
      "108.165.145.233:3129",
      "isp.oxylabs.io:8290",
      "isp.oxylabs.io:8288",
      "isp.oxylabs.io:8503"
    ]
  },
  "timestamp": "2025-12-10T19:14:40.205971"
}
```

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2024  
**Next Review:** After authenticated testing phase
