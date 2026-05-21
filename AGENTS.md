# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

This repository implements an AI hackathon review system:

- FastAPI backend in `src/`
- Celery workers for review, sandbox execution, and report generation
- PostgreSQL, Redis, MinIO, and Docker-in-Docker services via Docker Compose
- LangGraph-based review workflow in `src/workflows/review_graph.py`
- LLM review agents and verifier logic in `src/agents/`
- Static frontend served by nginx from `frontend/`
- Prompt templates in `prompts/`
- Database schema in `database/schema.sql`

Primary runtime endpoints:

- Frontend: `http://localhost:4399`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/api/v1/health`
- MinIO console: `http://localhost:9001`

## Repository Map

- `src/main.py`: FastAPI app setup and router registration.
- `src/config/settings.py`: Pydantic settings loaded from `.env`.
- `src/models.py`: SQLAlchemy ORM models.
- `src/schemas.py`: Pydantic request/response schemas.
- `src/database.py`: database engine/session helpers.
- `src/storage.py`: MinIO bucket and object operations.
- `src/routers/`: API route modules.
- `src/agents/`: review agents for functionality, code quality, architecture, innovation, and verification.
- `src/workflows/`: LangGraph review orchestration.
- `src/tasks/`: Celery task entry points.
- `src/sandbox/`: Docker sandbox execution.
- `src/reports/`: review report generation.
- `src/cache/`: Redis helpers.
- `frontend/`: vanilla HTML/CSS/JS admin UI.
- `docker/`: Docker Compose and service Dockerfiles.
- `database/schema.sql`: PostgreSQL schema and seed data.
- `api/openapi.yaml`: OpenAPI contract.
- `tests/`: tests and injected question fixtures.
- `test_project/`: sample submission project.

## Setup

Create local configuration:

```bash
cp .env.example .env
```

Install Python dependencies for local development:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the venv with:

```powershell
.\venv\Scripts\Activate.ps1
```

## Common Commands

Start the full Docker stack:

```bash
cd docker
docker compose -p hackathon_review up -d
```

Stop the Docker stack:

```bash
cd docker
docker compose -p hackathon_review down
```

Check running services:

```bash
cd docker
docker compose -p hackathon_review ps
```

Run the API locally:

```bash
uvicorn src.main:app --reload --port 8000
```

Run a Celery worker locally:

```bash
celery -A src.celery_app worker -Q review,sandbox,report -l info
```

Run tests:

```bash
pytest
```

Run a targeted test:

```bash
pytest tests/path/to_test.py -q
```

View service logs:

```bash
docker logs -f hackathon-api
docker logs -f hackathon-worker-review
docker logs -f hackathon-worker-sandbox
docker logs -f hackathon-worker-report
```

## Development Guidelines

- Prefer existing patterns in `src/routers`, `src/tasks`, `src/agents`, and `src/workflows` before adding new abstractions.
- Keep API behavior aligned with `api/openapi.yaml` when changing route contracts.
- Keep database changes synchronized between `src/models.py` and `database/schema.sql`.
- Use Pydantic schemas from `src/schemas.py` for request/response validation.
- Use settings from `src/config/settings.py`; do not read environment variables directly in scattered modules.
- Use async SQLAlchemy patterns consistently for database access.
- Use structured logging instead of `print`.
- Keep prompt text in `prompts/*.j2` rather than hard-coding long prompts in Python.
- Keep sandbox execution isolated and resource-limited. Be careful with Docker socket access and user-submitted code paths.
- Do not commit secrets. `.env` is local-only; update `.env.example` when adding required configuration.

## Testing Notes

- Add or update tests when behavior changes in routers, workflows, agents, sandbox execution, storage, or scoring.
- Mock LLM calls in unit tests. Avoid tests that require real API keys unless explicitly marked/integration-only.
- For workflow changes, test both success paths and failure/retry states where practical.
- For sandbox changes, verify timeout, resource limit, and unsafe input handling.
- For frontend changes, manually check the served UI at `http://localhost:4399` when Docker is running.

## LLM Review System Notes

- Review dimensions are implemented by specialized agents:
  - functionality
  - code quality
  - architecture
  - innovation
  - verifier cross-check
- Prompt templates live in `prompts/`; update the matching template with agent behavior changes.
- `src/workflows/review_graph.py` is the coordination point for preprocess, sandbox test, review fan-out, verifier, decision, and report generation.
- Keep score shapes and JSON parsing strict. Fail loudly with useful errors when LLM output is malformed.
- Do not assume a single LLM provider. Settings include OpenAI, Google, and Qwen-related fields.

## Docker And Sandbox Notes

- Compose project name used by docs is usually `hackathon_review`.
- Container names are fixed in `docker/docker-compose.yml`, such as `hackathon-api`, `hackathon-db`, `hackathon-redis`, and `hackathon-minio`.
- Docker-in-Docker is used for sandboxed submission execution. Changes here can affect host security and resource usage.
- Be conservative with privileges, mounted volumes, network access, CPU/memory limits, and timeouts.
- When changing worker queues, update Docker Compose commands and Celery task routing together.

## Frontend Notes

- The frontend is vanilla HTML/CSS/JS under `frontend/`.
- nginx serves the static UI and proxies API requests.
- Keep UI changes consistent with the existing simple admin-console style.
- Avoid adding a build system unless the user explicitly asks for one or the change clearly requires it.

## Encoding Note

Some existing documentation and comments may display as mojibake in certain terminals. Avoid propagating garbled text. New files should be written in UTF-8, and plain ASCII is preferred unless Chinese copy is specifically needed.

