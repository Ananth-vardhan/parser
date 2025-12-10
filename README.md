# parser

An intelligent web scraper powered by Flask, browser-use, OpenAI, and Gemini. It uses natural-language prompts to orchestrate browser automation and return structured data from complex, dynamic websites.

## Project structure

```
app/
├── __init__.py          # Flask application factory
├── api/                 # Versioned REST API blueprints
├── agents/              # Lightweight planning agents (stubs for now)
├── config.py            # Environment-aware settings
└── services/            # Session orchestration and browser-use integration
```

## Requirements

- Python 3.12 (or any 3.10+ interpreter supported by Flask 3)
- A virtual environment (`python -m venv .venv && source .venv/bin/activate`)
- System dependencies required by [Playwright](https://playwright.dev/) / `browser-use`

Install Python dependencies with pip:

```bash
pip install -r requirements.txt
```

`browser-use` relies on Playwright, so make sure to install the browsers before running the backend:

```bash
python -m playwright install chromium
```

## Environment variables

The service is fully driven by environment variables so it can run in different profiles (development, testing, production). The most common variables are:

| Variable | Description |
| --- | --- |
| `FLASK_APP` | Set to `app:create_app` to use the application factory. |
| `FLASK_ENV` / `APP_ENV` | Chooses the config profile (`development`, `production`, `testing`). |
| `LOG_LEVEL` | Logging level passed to the Flask logger (`INFO` by default). |
| `OPENAI_API_KEY` | API key used by the OpenAI SDK. |
| `GOOGLE_API_KEY` | API key for Gemini / Google Generative AI. |
| `DEFAULT_LLM_PROVIDER` | Name of the preferred LLM provider (defaults to `openai`). |
| `REDIS_URL` | Redis connection string (`redis://localhost:6379/0` by default). |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Override Celery's broker/backend when they differ from `REDIS_URL`. |
| `BROWSER_USE_HEADLESS` | Toggle headless mode for Playwright (`true` by default). |
| `BROWSER_USE_VIEWPORT_WIDTH` / `BROWSER_USE_VIEWPORT_HEIGHT` | Control the viewport size. |
| `BROWSER_USE_PROFILE_ID` | Optional browser profile identifier for persistent sessions. |
| `BROWSER_USE_START_URL` | Pre-load URL for new sessions. |
| `BROWSER_USE_USE_CLOUD_BROWSER` | Set to `true` to leverage Browser Use Cloud. |
| `BROWSER_USE_ENV_*` | Any variable with this prefix is forwarded to the browser-use session (e.g., `BROWSER_USE_ENV_HTTP_PROXY`). |

You can place these values inside a `.env` file (the project automatically loads it via `python-dotenv`).

## Running the development server

```bash
export FLASK_APP=app:create_app
export FLASK_ENV=development
flask run
```

The `create_app` factory wires the REST API blueprint and loads configuration from the variables above. The current implementation exposes placeholder endpoints while the browser-use integration is fleshed out.

### Available endpoints

- `GET /api/v1/health` &mdash; Simple readiness probe returning the active environment.
- `POST /api/v1/sessions` &mdash; Submit a URL plus optional instructions/metadata to create a scraping session. Returns a queued session payload.
- `GET /api/v1/sessions/<id>` &mdash; Retrieve the current status of a previously submitted session (stored in-memory for now).

Example request:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://example.com/jobs",
        "instructions": "Extract the job cards and normalize salary data",
        "metadata": {"source": "example"}
      }'
```

The response contains placeholder plan metadata, timestamps, and whether a `browser-use` session successfully instantiated. When Playwright/browser-use prerequisites are missing, the backend logs a warning but continues returning stub data so that API consumers can integrate early.

## Next steps

- Plug the service into Celery workers once task orchestration is required.
- Swap the in-memory session registry for Redis/Postgres to persist long-running jobs.
- Replace the stub agent with actual OpenAI/Gemini powered planners and attach real browser automation steps.
