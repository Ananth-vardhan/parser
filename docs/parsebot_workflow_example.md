# Parse.bot Two-Phase Workflow: IMDb Scenario

## Document Overview

**Purpose:** Detailed walkthrough of the Parse.bot two-phase workflow, demonstrating agent-driven exploration and code generation using IMDb movie data extraction as a concrete example.

**Audience:** Engineers implementing Parse.bot workflow orchestration, agents, and code generation pipelines.

**Date:** December 2024  
**Status:** Reference Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Workflow Overview](#workflow-overview)
3. [Phase 1: Exploratory Browsing](#phase-1-exploratory-browsing)
4. [Phase 2: Code Generation](#phase-2-code-generation)
5. [Approval Checkpoints](#approval-checkpoints)
6. [Failure Handling & Recovery](#failure-handling--recovery)
7. [User Feedback Loop](#user-feedback-loop)
8. [Sample Implementation Code](#sample-implementation-code)

---

## Executive Summary

The Parse.bot workflow consists of two distinct phases:

- **Phase 1 (Exploration):** An AI agent autonomously browses the target website (IMDb), navigates DOM structures, captures screenshots, and documents its findings. The agent makes decisions about which pages to visit, what information to extract, and records observations.

- **Phase 2 (Code Generation):** Using the exploration logs from Phase 1, a code generation engine produces runnable Python scraper code that can be executed repeatedly to extract data following the patterns discovered during exploration.

**Success Criteria:**
- Phase 1 produces comprehensive exploration logs with clear decision rationale
- Phase 2 generates executable, well-documented Python code
- User approval occurs at designated checkpoints
- Failure scenarios are handled gracefully with clear recovery paths

---

## Workflow Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parse.bot Workflow Engine                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
        ┌──────────────────┐          ┌──────────────────┐
        │  Phase 1:        │          │  Phase 2:        │
        │  Exploration     │          │  Code Generation │
        │  (User Request)  │          │  (Logs → Code)   │
        └──────────────────┘          └──────────────────┘
                  │                               │
         ┌────────┴──────────┐          ┌────────┴──────────┐
         │                   │          │                   │
    Approves?           Feedback    Generates?          Execute?
         │                   │          │                   │
         ▼                   ▼          ▼                   ▼
       Phase 2         Phase 1 Retry  Ready for      Production
    (if approved)      (Refinement)   Testing        Scraping
```

### Request Timeline

| Step | Phase | Component | Action | Duration |
|------|-------|-----------|--------|----------|
| 1 | Setup | User/Frontend | Submit scraping request (natural language) | Immediate |
| 2 | P1 | Orchestrator | Initialize exploration session | ~1 sec |
| 3 | P1 | Browser Agent | Start autonomous browsing | Variable |
| 4 | P1 | Agent + LLM | Analyze page, decide next steps | Per-page |
| 5 | P1 | Browser Agent | Navigate, capture screenshot | Per-navigation |
| 6 | P1 | Agent | Log observations & decisions | Per-page |
| 7 | P1 | User | Review exploration results | Manual |
| 8 | Checkpoint | Approval System | User approves or provides feedback | Manual |
| 9 | P2 | Code Generator | Transform logs into Python code | ~5-10 sec |
| 10 | P2 | Code Validator | Syntax & safety checks | ~2 sec |
| 11 | P2 | User | Review generated code | Manual |
| 12 | P2 | Executor | Run scraper on live site | Variable |
| 13 | P2 | Storage | Persist extracted data | Immediate |

---

## Phase 1: Exploratory Browsing

### Phase 1 Overview

The agent autonomously browses the IMDb website to understand its structure, navigation patterns, data organization, and extraction points. The agent uses browser-use actions to interact with the site and logs all observations.

**Goal:** Build a mental model of the target website sufficient to generate accurate extraction code in Phase 2.

### User Request Example

```
User Input:
"Extract the following information from IMDb for the top 50 highest-rated movies:
- Movie title
- Release year
- IMDb rating (1-10)
- Number of user ratings
- Director name(s)
- Cast (first 3 actors)
- Plot summary (first 50 words)
- Genre(s)
"
```

### Initial Agent Context Setup

**Agent Instructions:**
```
You are a web scraping agent. Your mission:

1. Navigate to IMDb (https://www.imdb.com)
2. Find the section listing highest-rated movies
3. Understand the page structure, DOM selectors, and data organization
4. Document your discoveries: URLs visited, CSS selectors found, JavaScript interactions required
5. Make decisions: Which pages to visit, which data is extractable, when to stop exploration

Constraints:
- Maximum 10 page visits
- Timeout: 5 minutes total
- Avoid user-disruptive actions
- Capture DOM snapshots when discovering new data sources

Required Log Fields for Each Action:
- Timestamp
- URL (before/after navigation)
- Action taken (click, scroll, type, wait)
- Screenshot captured? (yes/no)
- DOM element selectors discovered
- Data found? (yes/no, what type)
- Decision: Next action & reasoning
```

### Exploration Loop: Detailed Walkthrough

#### Step 1: Initial Navigation

| Component | Action | Observation | Screenshot | Decision |
|-----------|--------|-------------|-----------|----------|
| **Agent** | Navigate to https://www.imdb.com | Page loads (5s) | ✓ Captured | Find highest-rated movies section |
| **DOM Analysis** | Parse navigation menu | Links: Top 250, Popular, Watchlist, etc. | N/A | "Top 250" likely leads to rated movies |
| **Browser Action** | Click "Top 250 Movies" link | Navigate to /chart/top250/ | ✓ Captured | Analyze page structure |
| **Agent Decision** | Evaluate page content | 250 movies listed in table, paginated | N/A | Extract selector for movie rows |

**Log Entry 1:**
```yaml
timestamp: "2024-12-10T10:15:30Z"
step: 1
url: "https://www.imdb.com/chart/top250/"
action: "Navigated to Top 250 chart"
screenshot: "logs/exploration/step_1_top250.png"
dom_selectors_found:
  - "table.imdbTable tbody tr"     # Movie row container
  - "tr.even, tr.odd"               # Row styling
  - "td.titleColumn a"              # Movie title link
  - "td.ratingColumn strong"        # Rating value
observations:
  - "Page displays 250 entries in a table format"
  - "Each row contains: rank, title, year, rating"
  - "Page is paginated (showing rows 1-100)"
  - "No JavaScript rendering required for initial load"
decision: "Proceed to first movie detail page to verify additional data (director, cast, plot)"
next_action: "Click first movie link to explore detail page"
agent_confidence: 0.85
```

#### Step 2: Navigate to Movie Detail Page

| Component | Action | Observation | Screenshot | Decision |
|-----------|--------|-------------|-----------|----------|
| **Browser Action** | Click first movie (The Shawshank Redemption) | Navigate to /title/tt0111161/ | ✓ Captured | Explore detail structure |
| **DOM Analysis** | Inspect title section | Found: title, year, rating, vote count | N/A | All target fields present |
| **DOM Analysis** | Inspect directors/cast section | Found structured data in JSON-LD | ✓ Captured | Can extract via JSON instead of CSS selectors |
| **Agent Decision** | Evaluate data accessibility | JSON-LD structured data available | N/A | Use JSON-LD for reliable extraction |

**Log Entry 2:**
```yaml
timestamp: "2024-12-10T10:16:45Z"
step: 2
url: "https://www.imdb.com/title/tt0111161/"
action: "Navigated to movie detail page"
screenshot: "logs/exploration/step_2_detail.png"
dom_selectors_found:
  - "h1.sc-AxHeZe"                  # Movie title
  - "span.sc-2dddff0-0"              # Release year
  - "span[data-testid='ratingCount']" # Number of ratings
  - "script[type='application/ld+json']" # Structured data
  - "a[href*='/name/'] span"         # Director/actor names
observations:
  - "Movie detail page has two data sources:"
    - "CSS selectors for primary info"
    - "JSON-LD embedded schema (more reliable)"
  - "JSON-LD contains: title, director, actor[], datePublished, description"
  - "Director names at: a[href*='/name/nm']"
  - "No dynamic content loading detected (plot visible in initial DOM)"
decision: "Extraction can use both JSON-LD parsing and CSS selectors as fallback"
next_action: "Return to chart, sample 2 more movies to verify consistency"
agent_confidence: 0.92
json_ld_schema: "Movie"
```

#### Step 3: Verify Pattern Consistency

| Component | Action | Observation | Screenshot | Decision |
|-----------|--------|-------------|-----------|----------|
| **Browser Action** | Navigate back to Top 250 | Return to chart | N/A | Select second movie |
| **Browser Action** | Click movie #5 | Navigate to different movie | ✓ Captured | Verify same structure |
| **DOM Analysis** | Check JSON-LD structure | Schema identical, different values | N/A | Pattern confirmed |
| **Agent Decision** | Pattern verification | Consistent across multiple movies | N/A | Ready for code generation |

**Log Entry 3:**
```yaml
timestamp: "2024-12-10T10:18:20Z"
step: 3
url: "https://www.imdb.com/title/tt0468569/"
action: "Verified pattern on second movie (The Dark Knight)"
screenshot: "logs/exploration/step_3_verify.png"
dom_selectors_found: []  # No new selectors
observations:
  - "JSON-LD structure identical to previous movie"
  - "CSS selectors match expected format"
  - "All required fields present: title, year, rating, directors, cast, plot"
  - "Pagination on main chart works as expected"
decision: "Pattern verified across samples. Ready for Phase 2 code generation."
next_action: "End exploration. Return logs for code generation."
agent_confidence: 0.95
pattern_verified: true
```

### Exploration Summary Table

| Visit # | URL | Purpose | Key Findings | Status |
|---------|-----|---------|--------------|--------|
| 1 | /chart/top250/ | List structure | Table with 250 entries, row selector: `table.imdbTable tbody tr` | ✓ Complete |
| 2 | /title/tt0111161/ | Detail page structure | JSON-LD available, director/cast accessible | ✓ Complete |
| 3 | /title/tt0468569/ | Pattern verification | Confirmed consistency across movies | ✓ Complete |

### Exploration Artifacts

**Generated Files:**
- `logs/exploration/step_1_top250.png` — Screenshot of Top 250 chart
- `logs/exploration/step_2_detail.png` — Screenshot of movie detail page with DOM highlighted
- `logs/exploration/step_3_verify.png` — Second movie detail page
- `logs/exploration/session_log.yaml` — Full session transcript
- `logs/exploration/selectors_found.json` — Extracted CSS/XPath selectors

### Checkpoint 1: Phase 1 Approval

**Approval Prompt to User:**

```
═══════════════════════════════════════════════════════════════
              PHASE 1 EXPLORATION COMPLETE
═══════════════════════════════════════════════════════════════

Summary:
✓ Visited 3 pages (target: 10 max)
✓ Discovered 7 extraction points
✓ Pattern verified across samples
✓ High confidence (0.95)

Key Findings:
- Main list: https://www.imdb.com/chart/top250/
  Selector: table.imdbTable tbody tr
  
- Movie detail pages: https://www.imdb.com/title/tt{MOVIE_ID}/
  Data source: JSON-LD schema (reliable)
  
- Extractable fields:
  ✓ Title (from JSON-LD.name)
  ✓ Year (from JSON-LD.datePublished)
  ✓ Rating (CSS selector: span.sc-2dddff0-0)
  ✓ Vote count (data-testid attribute)
  ✓ Director(s) (JSON-LD.director[])
  ✓ Cast (JSON-LD.actor[] - first 3)
  ✓ Plot (JSON-LD.description)

Screenshots captured: 3
Session duration: 3 min 2 sec

═══════════════════════════════════════════════════════════════

Options:
[A] Approve & Proceed to Phase 2 (Code Generation)
[B] Request Additional Exploration (Refine & Retry)
[C] Cancel & Start Over

Your choice: _
```

**Expected User Response:** Approve (A)

---

## Phase 2: Code Generation

### Phase 2 Overview

The code generation engine transforms the exploration logs into executable Python code. The generated code will:
1. Navigate to the main list page
2. Extract movie IDs and links
3. Visit each movie detail page
4. Parse JSON-LD and CSS selectors
5. Structure data into consistent format
6. Return results

### Code Generation Context

**Input to Code Generator:**
```json
{
  "exploration_logs": "logs/exploration/session_log.yaml",
  "user_request": "Extract top 50 highest-rated IMDb movies with title, year, rating, director, cast, plot",
  "discovered_selectors": {
    "main_list_url": "https://www.imdb.com/chart/top250/",
    "movie_row_selector": "table.imdbTable tbody tr",
    "detail_page_url_template": "https://www.imdb.com/title/{movie_id}/",
    "json_ld_script_selector": "script[type='application/ld+json']"
  },
  "constraints": {
    "max_items": 50,
    "timeout_per_page": 10,
    "max_total_time": 300,
    "user_agent_required": true,
    "proxy_support": true
  },
  "output_format": "structured_json"
}
```

### Generated Code

**File: `generated_scrapers/imdb_top_movies.py`**

```python
"""
IMDb Top 250 Movies Scraper
Generated: 2024-12-10T10:20:00Z
Phase: 2 - Code Generation

This scraper extracts movie data from IMDb's Top 250 chart.
It was generated from Phase 1 exploration logs.
"""

import json
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ============================================================================
# CONFIGURATION
# ============================================================================

MAIN_LIST_URL = "https://www.imdb.com/chart/top250/"
MOVIE_DETAIL_URL_TEMPLATE = "https://www.imdb.com/title/{movie_id}/"

# Selectors discovered during Phase 1 exploration
SELECTORS = {
    "movie_row": "table.imdbTable tbody tr",
    "movie_link": "td.titleColumn a",
    "movie_title": "h1.sc-AxHeZe",
    "rating": "span.sc-2dddff0-0",
    "vote_count": "span[data-testid='ratingCount']",
    "json_ld": "script[type='application/ld+json']",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class MovieData:
    """Extracted movie information"""
    title: str
    year: int
    rating: float
    vote_count: int
    director: List[str]
    cast: List[str]
    plot: str
    movie_id: str
    detail_url: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "year": self.year,
            "rating": self.rating,
            "vote_count": self.vote_count,
            "director": self.director,
            "cast": self.cast[:3],  # Only first 3 actors
            "plot": self.plot[:200] if self.plot else "",  # First 200 chars
            "movie_id": self.movie_id,
            "detail_url": self.detail_url,
        }


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch a page with proper headers and error handling
    
    Args:
        url: Page URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        HTML content or None if request fails
    """
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_movie_list(html: str) -> List[Dict[str, str]]:
    """
    Extract movie IDs and links from top 250 list
    
    Args:
        html: HTML content of top 250 page
        
    Returns:
        List of {movie_id, title, url} dictionaries
    """
    soup = BeautifulSoup(html, "html.parser")
    movies = []
    
    # Find all movie rows
    rows = soup.select(SELECTORS["movie_row"])
    
    for idx, row in enumerate(rows[:50], start=1):  # Limit to 50
        try:
            link_elem = row.select_one(SELECTORS["movie_link"])
            if not link_elem or not link_elem.get("href"):
                continue
                
            # Extract movie ID from URL: /title/tt0111161/
            href = link_elem.get("href", "")
            match = re.search(r"/title/(tt\d+)/", href)
            if not match:
                continue
                
            movie_id = match.group(1)
            title = link_elem.get_text(strip=True)
            detail_url = MOVIE_DETAIL_URL_TEMPLATE.format(movie_id=movie_id)
            
            movies.append({
                "movie_id": movie_id,
                "title": title,
                "url": detail_url,
                "list_position": idx,
            })
        except Exception as e:
            print(f"Error parsing movie row {idx}: {e}")
            continue
    
    return movies


def extract_json_ld(html: str) -> Optional[Dict]:
    """
    Extract JSON-LD structured data from page
    
    Args:
        html: HTML content
        
    Returns:
        Parsed JSON-LD data or None
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.select(SELECTORS["json_ld"])
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            # Only extract Movie schema
            if data.get("@type") == "Movie" or (
                isinstance(data.get("@type"), list) and "Movie" in data["@type"]
            ):
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    
    return None


def extract_movie_details(html: str, movie_id: str) -> Optional[MovieData]:
    """
    Extract all required information from a movie detail page
    
    Args:
        html: HTML content of movie detail page
        movie_id: IMDb movie ID (tt0111161)
        
    Returns:
        MovieData object or None if extraction fails
    """
    try:
        # Try JSON-LD first (most reliable)
        json_ld = extract_json_ld(html)
        
        if not json_ld:
            print(f"No JSON-LD found for {movie_id}")
            return None
        
        # Parse JSON-LD data
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract fields from JSON-LD
        title = json_ld.get("name", "")
        date_published = json_ld.get("datePublished", "")
        year = int(date_published.split("-")[0]) if date_published else 0
        
        # Rating - try CSS selector first, fallback to JSON-LD
        rating_elem = soup.select_one(SELECTORS["rating"])
        if rating_elem:
            try:
                rating = float(rating_elem.get_text(strip=True))
            except ValueError:
                rating = json_ld.get("aggregateRating", {}).get("ratingValue", 0)
        else:
            rating = json_ld.get("aggregateRating", {}).get("ratingValue", 0)
        
        # Vote count
        vote_elem = soup.select_one(SELECTORS["vote_count"])
        if vote_elem:
            vote_text = vote_elem.get_text(strip=True)
            # Remove commas: "123,456" -> 123456
            vote_count = int(vote_text.replace(",", ""))
        else:
            vote_count = json_ld.get("aggregateRating", {}).get("ratingCount", 0)
        
        # Director(s)
        directors = []
        director_data = json_ld.get("director", [])
        if isinstance(director_data, dict):
            directors = [director_data.get("name", "")]
        elif isinstance(director_data, list):
            directors = [d.get("name", "") if isinstance(d, dict) else str(d) 
                        for d in director_data]
        
        # Cast (first 3)
        cast = []
        actor_data = json_ld.get("actor", [])
        if isinstance(actor_data, list):
            cast = [a.get("name", "") if isinstance(a, dict) else str(a)
                   for a in actor_data[:3]]
        
        # Plot summary
        plot = json_ld.get("description", "")
        
        detail_url = MOVIE_DETAIL_URL_TEMPLATE.format(movie_id=movie_id)
        
        return MovieData(
            title=title,
            year=year,
            rating=float(rating) if rating else 0.0,
            vote_count=int(vote_count) if vote_count else 0,
            director=[d for d in directors if d],  # Filter empty strings
            cast=[c for c in cast if c],
            plot=plot,
            movie_id=movie_id,
            detail_url=detail_url,
        )
        
    except Exception as e:
        print(f"Error extracting details for {movie_id}: {e}")
        return None


def scrape_imdb_top_movies(max_items: int = 50, delay: float = 0.5) -> List[Dict]:
    """
    Main scraping function
    
    Args:
        max_items: Maximum number of movies to scrape (default 50)
        delay: Delay between requests in seconds (be respectful)
        
    Returns:
        List of movie data dictionaries
    """
    print(f"[IMDb Scraper] Starting scrape of top {max_items} movies...")
    print(f"[IMDb Scraper] Main list URL: {MAIN_LIST_URL}")
    
    # Step 1: Fetch the main list
    print("[Phase 1] Fetching top 250 list...")
    html = fetch_page(MAIN_LIST_URL)
    if not html:
        print("Failed to fetch main list page")
        return []
    
    # Step 2: Extract movie list
    print("[Phase 1] Extracting movie list...")
    movies = extract_movie_list(html)
    print(f"Found {len(movies)} movies in list")
    
    # Step 3: Fetch details for each movie
    print(f"[Phase 2] Fetching details for {min(len(movies), max_items)} movies...")
    results = []
    
    for idx, movie_info in enumerate(movies[:max_items], start=1):
        print(f"  [{idx}/{min(len(movies), max_items)}] {movie_info['title']}...", end=" ")
        
        # Fetch detail page
        detail_html = fetch_page(movie_info["url"])
        if not detail_html:
            print("✗ Failed to fetch")
            continue
        
        # Extract data
        movie_data = extract_movie_details(detail_html, movie_info["movie_id"])
        if movie_data:
            results.append(movie_data.to_dict())
            print("✓")
        else:
            print("✗ Extraction failed")
        
        # Be respectful - add delay between requests
        if idx < min(len(movies), max_items):
            time.sleep(delay)
    
    print(f"\n[Complete] Scraped {len(results)} movies successfully")
    return results


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run scraper
    results = scrape_imdb_top_movies(max_items=50)
    
    # Output results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "source": "IMDb",
        "total_scraped": len(results),
        "movies": results,
    }
    
    print("\n" + "="*70)
    print("Sample output (first 2 movies):")
    print("="*70)
    for movie in results[:2]:
        print(json.dumps(movie, indent=2))
    
    # Save to file
    output_file = "imdb_top_movies.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {output_file}")
```

### Code Generation Details

**Generated Code Characteristics:**

| Aspect | Detail |
|--------|--------|
| **Language** | Python 3.8+ |
| **Dependencies** | requests, beautifulsoup4 |
| **Input** | Exploration logs (selectors, URLs, patterns) |
| **Output** | JSON with structured movie data |
| **Error Handling** | Try-catch on all network operations and parsing |
| **Rate Limiting** | Configurable delay between requests (0.5s default) |
| **Logging** | Progress indicators for user feedback |
| **Timeout** | 10s per page, 300s total |
| **Documentation** | Inline comments explaining each section |

### Code Validation Checklist

```
✓ Syntax validation (Python AST parse)
✓ Import availability (requests, beautifulsoup4 in requirements)
✓ Selector accuracy (matches exploration logs)
✓ Error handling (all network operations wrapped)
✓ Rate limiting (delay configured)
✓ Data model consistency (MovieData matches request)
✓ JSON-LD parsing (handles dict and list variants)
✓ CSS fallback selectors (for robustness)
✓ Output format (matches user request)
✓ Security checks (no SQL injection, safe subprocess calls)

Status: ✓ PASS - Ready for execution
```

### Checkpoint 2: Phase 2 Code Review Approval

**Code Review Prompt:**

```
═══════════════════════════════════════════════════════════════
           PHASE 2 CODE GENERATION COMPLETE
═══════════════════════════════════════════════════════════════

Generated Scraper: imdb_top_movies.py
Lines of Code: 387
Dependencies: requests, beautifulsoup4

Validation Results:
✓ Syntax valid
✓ All imports available
✓ Selectors match Phase 1 discoveries
✓ Error handling implemented
✓ Rate limiting: 0.5s between requests
✓ Timeout: 10s per page, 300s total

Code Quality:
✓ Docstrings on all functions
✓ Type hints included
✓ Data model (MovieData) defined
✓ JSON-LD parsing with CSS fallback
✓ Respects robots.txt delay guidelines

Estimated Extraction: 50 movies in ~100-120 seconds

Key Features:
- Extracts from Phase 1 selectors
- Uses JSON-LD for primary data (reliable)
- CSS selectors as fallback
- Progress logging for transparency
- Output to JSON file with metadata

═══════════════════════════════════════════════════════════════

Options:
[A] Approve & Execute Scraper
[B] Request Code Changes (Refinement)
[C] Review Different Approach (e.g., Selenium)
[D] Cancel

Your choice: _
```

**Expected User Response:** Approve (A)

---

## Approval Checkpoints

### Checkpoint 1: Phase 1 Completion (Exploration Approval)

**Timing:** After Phase 1 exploration completes

**Review Criteria:**
- Agent visited appropriate pages ✓
- Selectors discovered and verified ✓
- Screenshots captured ✓
- Decision rationale logged ✓
- High confidence score (>0.80) ✓

**User Actions:**
1. Review exploration summary table
2. Examine screenshots
3. Validate selectors match website structure
4. Approve or request additional exploration

**Approval Decision:**
```
User selects: [A] Approve & Proceed to Phase 2
Result: System proceeds to code generation
```

### Checkpoint 2: Phase 2 Code Review (Code Approval)

**Timing:** After code generation completes

**Review Criteria:**
- Code syntax is valid ✓
- Imports match environment ✓
- Selectors from Phase 1 are used ✓
- Error handling is robust ✓
- Respects rate limits ✓
- Output format matches request ✓

**User Actions:**
1. Review generated code
2. Check dependencies available
3. Verify selectors and logic
4. Approve or request modifications

**Approval Decision:**
```
User selects: [A] Approve & Execute Scraper
Result: System executes scraper against live website
```

### Checkpoint 3: Execution Result Review

**Timing:** After scraper execution completes

**Review Criteria:**
- All 50 movies successfully extracted ✓
- Data completeness (all fields present) ✓
- Data accuracy (spot-check samples) ✓
- Execution time reasonable ✓

**User Actions:**
1. Review sample extracted data
2. Verify field values (title, rating, etc.)
3. Check total item count
4. Confirm/retry or refine

**Result:**
```
Status: SUCCESS
Movies extracted: 50/50 (100%)
Execution time: 87 seconds
Output file: imdb_top_movies.json
```

---

## Failure Handling & Recovery

### Failure Scenario 1: Phase 1 Timeout

**Situation:** Agent reaches 5-minute timeout before completing exploration

**Detection:**
```
Error: Exploration timeout exceeded (300s)
Pages visited: 2/10
Confidence: 0.60
```

**Recovery Options:**

| Option | Action | Outcome |
|--------|--------|---------|
| **A: Proceed with partial exploration** | Approve Phase 2 with 60% confidence | Riskier code, may need retry |
| **B: Refine exploration scope** | Reduce number of exploration pages | Faster, less comprehensive |
| **C: Restart exploration** | Reset session with optimized navigation | Complete but slower |

**Recommended:** Option B - Refine scope

### Failure Scenario 2: Selector Not Found During Execution

**Situation:** During Phase 2 execution, a selector returns no elements

**Detection:**
```
Warning: Selector 'td.titleColumn a' not found on page 3
URL: https://www.imdb.com/chart/top250/?start=201
Status: Fallback in progress
```

**Recovery Mechanism:**

1. **Try CSS fallback selector:**
   ```python
   primary_selector = "td.titleColumn a"
   fallback_selectors = [
       "a.titleColumn",
       "table.imdbTable a[href*='/title/']",
       "tr > td:nth-child(2) a"
   ]
   ```

2. **Escalate if all fail:**
   ```
   ERROR: No selector worked for movie extraction
   Row HTML: <tr>...</tr>
   Action: SKIP this row and continue
   ```

3. **Log and continue:**
   ```yaml
   timestamp: "2024-12-10T10:35:22Z"
   error: "Selectors not found"
   page_url: "https://www.imdb.com/chart/top250/?start=201"
   attempted_selectors: 3
   fallback_success: false
   action_taken: "Skipped row, continued with next"
   ```

### Failure Scenario 3: Network Timeout During Detail Page Fetch

**Situation:** Request to movie detail page times out after 10 seconds

**Detection:**
```
Error: Timeout fetching https://www.imdb.com/title/tt1234567/
Timeout: 10s exceeded
Movie: Avatar (2009)
```

**Recovery Mechanism:**

```python
def fetch_page_with_retry(url: str, max_retries: int = 3) -> Optional[str]:
    """Fetch with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return fetch_page(url, timeout=10)
        except requests.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Retry {attempt + 1} in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts")
                return None
```

**Actions:**
1. Retry up to 3 times with exponential backoff (1s, 2s, 4s)
2. Skip movie if all retries fail
3. Log failure and continue
4. Return partial results (49/50 instead of failing completely)

### Failure Scenario 4: IMDb Rate Limiting

**Situation:** IMDb returns HTTP 429 (Too Many Requests)

**Detection:**
```
HTTP 429: Too Many Requests
Retry-After: 60s
Current delay: 0.5s
```

**Recovery Mechanism:**

```python
def fetch_page_with_rate_limit(url: str) -> Optional[str]:
    """Fetch with rate limit handling"""
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(int(retry_after))
            # Retry the request
            return fetch_page_with_rate_limit(url)
        
        response.raise_for_status()
        return response.text
        
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
```

**Actions:**
1. Detect `Retry-After` header
2. Wait for specified duration
3. Retry the same request
4. If still failing, skip and continue with delay increase

---

## User Feedback Loop

### Feedback Type 1: Phase 1 Findings Clarification

**Scenario:** User sees exploration results and wants to focus on specific data

**User Request:**
```
"I noticed you found the director field in JSON-LD. 
Could you also explore if there's a dedicated Directors page 
link that might have more detailed director information?"
```

**System Response:**
```
Initiating targeted exploration:
✓ Adding task: Check for directors page link
✓ Target selector: a[href*='/name/'] in director section
✓ Max new exploration steps: 2
✓ Estimated time: 30s

Proceeding to Phase 2 with:
- Original selectors (unchanged)
- Additional note: Directors page available at detail page
- Code generation will maintain JSON-LD primary path
```

### Feedback Type 2: Generated Code Modification Request

**Scenario:** User reviews code and wants additional processing

**User Request:**
```
"Can you modify the code to also extract the director's birthplace? 
And calculate the vote rating trend (if available)?"
```

**System Response:**

| Request | Feasibility | Action |
|---------|------------|--------|
| Director birthplace | **Medium** | Requires visiting director page (additional requests) |
| Vote trend | **Low** | Not visible in main page, requires historical API |

**Generated Code Change Example:**
```python
# Before
directors = [d.get("name", "") for d in director_data]

# After (with birthplace)
directors_with_birthplace = []
for d in director_data:
    if isinstance(d, dict):
        director_info = {
            "name": d.get("name", ""),
            "birthplace": None  # Would require additional fetch
        }
        directors_with_birthplace.append(director_info)

directors = directors_with_birthplace
```

**Approval Required:**
```
═══════════════════════════════════════════════════════════════
         CODE MODIFICATION FEASIBILITY REVIEW
═══════════════════════════════════════════════════════════════

Request: Extract director birthplace + vote trend

Analysis:
1. Director Birthplace
   - Requires: Visiting /name/{director_id}/ page
   - Additional pages: ~150 (one per director)
   - Est. time: +300s per execution
   - Feasibility: ✓ Possible

2. Vote Trend
   - Requires: IMDb historical API (not exposed in HTML)
   - Data source: Private API endpoint
   - Feasibility: ✗ Not available via public HTML

Modified Code Impact:
- Lines added: 45
- Dependencies: +0
- Execution time: +300s
- Risk: Higher (more requests, more failure points)

Recommendation: Include birthplace, skip vote trend

Options:
[A] Accept full modification
[B] Accept partial (birthplace only)
[C] Revert to original code
[D] Cancel & start over

Your choice: _
```

### Feedback Type 3: Execution Problem Report

**Scenario:** Scraper runs but produces incomplete results

**User Report:**
```
"I ran the scraper and got only 45 movies instead of 50. 
Some movies seem to be missing titles. Can you investigate?"
```

**System Investigation:**

```yaml
execution_log:
  timestamp: "2024-12-10T11:15:00Z"
  status: "PARTIAL_FAILURE"
  movies_extracted: 45
  movies_failed: 5
  
failed_movies:
  - list_position: 12
    movie_id: "tt0110912"
    error: "JSON-LD parsing failed"
    reason: "No name field in JSON-LD"
    html_title: "Pulp Fiction"
    
  - list_position: 23
    movie_id: "tt0073486"
    error: "Network timeout on retry"
    reason: "3 timeout attempts exhausted"
    url: "https://www.imdb.com/title/tt0073486/"

recommendation: "Update selectors for movie #12, increase timeout for movie #23"
```

**Proposed Remediation:**

```python
# Add additional title fallback
title = json_ld.get("name", "")
if not title:
    # Try alternative sources
    soup = BeautifulSoup(html, "html.parser")
    title_elem = soup.select_one("h1 span")
    if title_elem:
        title = title_elem.get_text(strip=True)

# Increase timeout for problematic URLs
if movie_id in ["tt0073486"]:  # Known timeout
    fetch_page(url, timeout=20)  # Increase timeout
```

**User Approval:**
```
[A] Apply remediation and re-run
[B] Accept 45/50 results as-is
[C] Request different approach (Selenium with JavaScript)
[D] Cancel & refine
```

---

## Sample Implementation Code

### Orchestrator Request Handler

**File: `orchestrator/workflow_handler.py`**

```python
"""
Parse.bot Workflow Orchestrator
Manages Phase 1 & Phase 2 workflow execution
"""

from enum import Enum
from typing import Dict, Optional, List
import asyncio
import json
from datetime import datetime

from exploration_agent import ExplorationAgent
from code_generator import CodeGenerator
from scraper_executor import ScraperExecutor


class WorkflowPhase(Enum):
    """Workflow execution phases"""
    SETUP = "setup"
    EXPLORATION = "phase_1_exploration"
    EXPLORATION_REVIEW = "phase_1_review"
    CODE_GENERATION = "phase_2_generation"
    CODE_REVIEW = "phase_2_review"
    EXECUTION = "phase_2_execution"
    COMPLETE = "complete"
    FAILED = "failed"


class ParseBotWorkflow:
    """Two-phase Parse.bot workflow orchestrator"""
    
    def __init__(self, user_request: str, session_id: str):
        """
        Initialize workflow
        
        Args:
            user_request: Natural language scraping request
            session_id: Unique identifier for this workflow execution
        """
        self.user_request = user_request
        self.session_id = session_id
        self.phase = WorkflowPhase.SETUP
        self.exploration_logs = None
        self.generated_code = None
        self.execution_results = None
        self.status_history = []
        
    def log_status(self, phase: WorkflowPhase, details: Dict) -> None:
        """Log workflow status transition"""
        status_entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase.value,
            "details": details,
        }
        self.status_history.append(status_entry)
        self.phase = phase
        print(f"[{self.session_id}] {phase.value}: {details}")
    
    async def execute_phase_1(self) -> bool:
        """
        Execute Phase 1: Exploratory Browsing
        
        Returns:
            True if successful, False if failed
        """
        try:
            self.log_status(WorkflowPhase.EXPLORATION, {
                "action": "Starting Phase 1 exploration",
                "user_request": self.user_request,
            })
            
            # Initialize exploration agent
            agent = ExplorationAgent(
                user_request=self.user_request,
                session_id=self.session_id,
                max_duration=300,  # 5 minutes
                max_pages=10,
            )
            
            # Run exploration
            self.exploration_logs = await agent.execute()
            
            if not self.exploration_logs:
                self.log_status(WorkflowPhase.FAILED, {
                    "phase": "Phase 1",
                    "error": "No exploration logs generated",
                })
                return False
            
            self.log_status(WorkflowPhase.EXPLORATION_REVIEW, {
                "action": "Phase 1 complete, awaiting user approval",
                "exploration_summary": {
                    "pages_visited": len(self.exploration_logs.get("visits", [])),
                    "selectors_found": len(self.exploration_logs.get("selectors", {})),
                    "confidence": self.exploration_logs.get("confidence", 0),
                },
            })
            
            return True
            
        except Exception as e:
            self.log_status(WorkflowPhase.FAILED, {
                "phase": "Phase 1",
                "error": str(e),
            })
            return False
    
    def wait_for_phase_1_approval(self) -> bool:
        """
        Wait for user approval of Phase 1 exploration
        
        Returns:
            True if approved, False if rejected/cancelled
        """
        # In real system, this would wait for user input via API
        # For demo, assume approval
        self.log_status(WorkflowPhase.CODE_GENERATION, {
            "action": "User approved Phase 1, proceeding to Phase 2",
        })
        return True
    
    async def execute_phase_2(self) -> bool:
        """
        Execute Phase 2: Code Generation
        
        Returns:
            True if successful, False if failed
        """
        try:
            self.log_status(WorkflowPhase.CODE_GENERATION, {
                "action": "Generating scraper code from exploration logs",
            })
            
            # Initialize code generator
            generator = CodeGenerator(
                exploration_logs=self.exploration_logs,
                user_request=self.user_request,
                session_id=self.session_id,
            )
            
            # Generate code
            self.generated_code = await generator.generate()
            
            if not self.generated_code:
                self.log_status(WorkflowPhase.FAILED, {
                    "phase": "Phase 2",
                    "error": "Code generation failed",
                })
                return False
            
            self.log_status(WorkflowPhase.CODE_REVIEW, {
                "action": "Code generation complete, awaiting user approval",
                "code_stats": {
                    "lines": self.generated_code.get("stats", {}).get("lines", 0),
                    "functions": len(self.generated_code.get("functions", [])),
                    "syntax_valid": True,
                },
            })
            
            return True
            
        except Exception as e:
            self.log_status(WorkflowPhase.FAILED, {
                "phase": "Phase 2",
                "error": str(e),
            })
            return False
    
    def wait_for_phase_2_approval(self) -> bool:
        """
        Wait for user approval of generated code
        
        Returns:
            True if approved, False if rejected/cancelled
        """
        # In real system, this would wait for user input via API
        # For demo, assume approval
        self.log_status(WorkflowPhase.EXECUTION, {
            "action": "User approved Phase 2 code, executing scraper",
        })
        return True
    
    async def execute_scraper(self) -> bool:
        """
        Execute the generated scraper against live website
        
        Returns:
            True if successful, False if failed
        """
        try:
            executor = ScraperExecutor(
                code=self.generated_code.get("code"),
                session_id=self.session_id,
            )
            
            self.execution_results = await executor.execute()
            
            self.log_status(WorkflowPhase.COMPLETE, {
                "action": "Scraper execution complete",
                "results": {
                    "items_extracted": len(self.execution_results.get("items", [])),
                    "success_rate": self.execution_results.get("success_rate", 0),
                    "execution_time": self.execution_results.get("duration_seconds", 0),
                },
            })
            
            return True
            
        except Exception as e:
            self.log_status(WorkflowPhase.FAILED, {
                "phase": "Execution",
                "error": str(e),
            })
            return False
    
    async def run_full_workflow(self) -> Dict:
        """
        Execute the complete two-phase workflow
        
        Returns:
            Final results dictionary
        """
        # Phase 1: Exploration
        if not await self.execute_phase_1():
            return {"status": "failed", "phase": "Phase 1", "logs": self.status_history}
        
        # Checkpoint 1: User approval
        if not self.wait_for_phase_1_approval():
            return {"status": "cancelled", "phase": "Phase 1 approval", "logs": self.status_history}
        
        # Phase 2: Code Generation
        if not await self.execute_phase_2():
            return {"status": "failed", "phase": "Phase 2", "logs": self.status_history}
        
        # Checkpoint 2: User approval
        if not self.wait_for_phase_2_approval():
            return {"status": "cancelled", "phase": "Phase 2 approval", "logs": self.status_history}
        
        # Phase 2 Execution: Run scraper
        if not await self.execute_scraper():
            return {"status": "failed", "phase": "Execution", "logs": self.status_history}
        
        # Success!
        return {
            "status": "success",
            "phase": "complete",
            "session_id": self.session_id,
            "results": self.execution_results,
            "logs": self.status_history,
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example workflow execution"""
    user_request = """
    Extract the following information from IMDb for the top 50 highest-rated movies:
    - Movie title
    - Release year
    - IMDb rating (1-10)
    - Number of user ratings
    - Director name(s)
    - Cast (first 3 actors)
    - Plot summary (first 50 words)
    - Genre(s)
    """
    
    workflow = ParseBotWorkflow(
        user_request=user_request,
        session_id="session_imdb_001",
    )
    
    result = await workflow.run_full_workflow()
    
    print("\n" + "="*70)
    print("WORKFLOW EXECUTION COMPLETE")
    print("="*70)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

### Error Recovery Example

**File: `recovery/failure_handler.py`**

```python
"""
Error recovery and retry mechanisms
"""

import time
from typing import Optional, Callable, Any
import requests


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


def retry_with_backoff(
    func: Callable,
    config: RetryConfig = None,
    *args,
    **kwargs
) -> Optional[Any]:
    """
    Execute function with exponential backoff retry
    
    Args:
        func: Function to execute
        config: Retry configuration
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function result or None if all retries exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)
            
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exception = e
            
            if attempt < config.max_attempts - 1:
                # Calculate backoff delay
                delay = config.initial_delay * (config.backoff_factor ** attempt)
                
                # Add jitter to prevent thundering herd
                if config.jitter:
                    import random
                    delay *= (0.5 + random.random())
                
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"All {config.max_attempts} attempts exhausted")
    
    return None


def handle_http_error(response: requests.Response) -> bool:
    """
    Handle HTTP errors with appropriate recovery
    
    Args:
        response: HTTP response object
        
    Returns:
        True if error is recoverable, False if fatal
    """
    status_code = response.status_code
    
    if status_code == 429:
        # Rate limited - respect Retry-After
        retry_after = int(response.headers.get("Retry-After", "60"))
        print(f"Rate limited. Waiting {retry_after}s...")
        time.sleep(retry_after)
        return True  # Recoverable
    
    elif status_code == 503:
        # Service unavailable - retry with backoff
        print("Service unavailable. Retrying...")
        return True  # Recoverable
    
    elif status_code == 403:
        # Forbidden - may be due to headers/user-agent
        print("Access forbidden. Check headers/user-agent...")
        return True  # Possibly recoverable
    
    elif status_code == 401:
        # Unauthorized - not recoverable via retry
        print("Unauthorized access")
        return False  # Not recoverable
    
    elif status_code in [400, 404]:
        # Bad request or not found - not recoverable
        print(f"HTTP {status_code} - Not recoverable")
        return False
    
    else:
        # Other errors - attempt retry
        return True


# Example usage:
if __name__ == "__main__":
    def fetch_with_retry(url: str) -> Optional[str]:
        """Fetch URL with retry and error handling"""
        def fetch():
            response = requests.get(url, timeout=10)
            if not handle_http_error(response):
                raise RuntimeError(f"Unrecoverable error: {response.status_code}")
            response.raise_for_status()
            return response.text
        
        return retry_with_backoff(fetch, RetryConfig(max_attempts=3))
    
    # Test
    content = fetch_with_retry("https://www.imdb.com/chart/top250/")
    if content:
        print(f"Successfully fetched {len(content)} bytes")
```

---

## Technical Implementation Guidelines

### Key Components to Implement

1. **Exploration Agent**
   - Browser automation (Selenium/Playwright)
   - DOM parsing and selector extraction
   - Decision logic (when to continue exploring)
   - Log generation

2. **Code Generator**
   - Template-based code generation
   - Selector validation
   - Syntax checking
   - Documentation generation

3. **Scraper Executor**
   - Safe code execution environment
   - Error recovery
   - Progress tracking
   - Result formatting

4. **Approval System**
   - User UI for reviewing Phase 1 results
   - Code diff/review interface
   - Execution result display

### Testing Recommendations

```python
# Test Phase 1 exploration
def test_exploration_phase():
    agent = ExplorationAgent(user_request="...", ...)
    logs = agent.execute()
    assert len(logs["visits"]) > 0
    assert logs["confidence"] > 0.5
    assert "selectors" in logs

# Test code generation
def test_code_generation():
    generator = CodeGenerator(exploration_logs={...}, ...)
    code = generator.generate()
    assert syntax_valid(code["code"])
    assert len(code["functions"]) > 0
    assert "scrape" in code["code"]

# Test scraper execution
def test_execution():
    executor = ScraperExecutor(code="...", ...)
    result = executor.execute()
    assert len(result["items"]) > 0
    assert result["success_rate"] > 0.8
```

---

## Conclusion

The Parse.bot two-phase workflow provides a structured approach to web scraping:

1. **Phase 1** enables intelligent exploration and discovery
2. **Phase 2** translates discoveries into production code
3. **Approval checkpoints** ensure user confidence and control
4. **Error recovery** mechanisms handle real-world challenges
5. **User feedback loops** allow refinement at any stage

This IMDb example demonstrates how the workflow can be applied to real websites, with concrete selectors, code examples, and failure handling strategies.

For implementation, refer to the sample code modules and adapt them to your specific infrastructure and requirements.

---

## References & Assets

- **Exploration Logs:** `logs/exploration/session_log.yaml`
- **Discovered Selectors:** `logs/exploration/selectors_found.json`
- **Generated Scraper:** `generated_scrapers/imdb_top_movies.py`
- **Orchestrator Code:** `orchestrator/workflow_handler.py`
- **Error Recovery:** `recovery/failure_handler.py`
- **Screenshots:** `logs/exploration/*.png` (3 images from walkthrough)

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2024  
**Status:** Ready for Engineering Implementation
