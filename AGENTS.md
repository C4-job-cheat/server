# Repository Guidelines

## Project Structure & Module Organization
The Django project root lives in `job_cheat/job_cheat`. Domain apps include `api/` for REST endpoints, `core/` for shared services (Firebase adapters, storage), `personas/` for persona ingestion flows, `job_search/` for scraping logic, and `cover_letters/` plus `interviews/` for feature-specific flows. JSON helper scripts such as `check_json_files.py` and `view_storage_json.py` sit at `job_cheat/`. Persistent docs live under `docs/` (see `database-schema.md` and `rag-system-implementation-plan.md`). Client-side artifacts and tooling prototypes are isolated in `tools/` and `chatgpt_export/`. Static and media assets are pushed to Firebase; no local `static/` directory is versioned.

## Build, Test & Development Commands
Use uv for Python environment management. Run `uv sync` after pulling to install dependencies. Apply migrations with `uv run python manage.py migrate`. Launch the default WSGI server at `uv run python manage.py runserver 0.0.0.0:8000`; prefer `uv run python runserver_asgi.py 0.0.0.0:8000` for large HTML uploads. Format `.env` locally and export Firebase credentials before starting the server. Call `uv run python job_cheat/check_json_files.py` to validate stored persona payloads when debugging.

## Coding Style & Naming Conventions
Target Python 3.12 syntax with 4-space indentation. Modules, packages, and test files follow snake_case (`core/services/firebase_storage.py`). Classes and DRF serializers stay in PascalCase, while constants are UPPER_SNAKE. Keep view names aligned with URL patterns (`personas-input-create`). Prefer Django ORM querysets over raw SQL; isolate external service calls inside `core/services`. Maintain docstrings on public interfaces and mirror existing Korean user-facing strings for consistency.

## Testing Guidelines
Tests use Django's `TestCase` and DRF's `APIClient` (`personas/tests/test_views.py`). Name files `test_*.py` and classes `*Tests`. Run the suite with `uv run python manage.py test`, or scope to an app via `uv run python manage.py test personas`. Mock Firebase interactions with `unittest.mock.patch` and provide sample uploads via `SimpleUploadedFile`, matching current fixtures.

## Commit & Pull Request Guidelines
Recent commits favor concise Korean summaries beginning with the completed work, e.g., `완료된 기능 - person input 비동기 뷰로 구현`. Follow that pattern: short context first, details after a hyphen. For pull requests, include: (1) a summary of functional changes, (2) linked Jira/issue IDs, (3) screenshots or API demo URLs when touching personas endpoints, and (4) test evidence (`manage.py test` output or manual checklist). Highlight Firebase rule updates and new environment variables explicitly.
