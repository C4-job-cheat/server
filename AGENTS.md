# Repository Guidelines

## Project Structure & Module Organization
- `job_cheat/` holds the Django project root with `manage.py`, `pyproject.toml`, and shared Firebase configuration artifacts.
- `job_cheat/job_cheat/` contains project configuration: `settings.py`, URL routing, and the ASGI/WSGI entry points. Configure Firebase credentials and Firestore clients here instead of Django database settings.
- `job_cheat/main_app/` is the primary application. Keep Firestore-facing services, views, and URLs modular, and expand `tests.py` or create a `tests/` package as functionality grows.
- Store reusable assets (templates, static files) inside app-level folders; avoid committing generated files, service account keys, or other secrets.

## Environment & Tooling
- Target Python 3.12+. Manage environments with `uv venv` and activate the generated virtual environment before development.
- Dependencies live in `pyproject.toml`; install and lock them exclusively with `uv sync` (no `pip` usage).
- Keep Firebase service account credentials and other local settings in environment variables or a `.env` ignored by Git.

## Build, Test, and Development Commands
- `uv run python manage.py runserver 0.0.0.0:8000` ? start the development server for manual testing while loading Firestore clients.
- `uv run python manage.py shell_plus` (if installed) or `uv run python manage.py shell` ? inspect Firestore data access patterns safely.
- Firestore data models live outside Django ORM, so skip `migrate` / `createsuperuser`; manage collections through Firebase Admin SDK or the Firebase Console.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep line length at 88 characters to stay `black`-friendly.
- Use `snake_case` for functions and modules, `PascalCase` for models and forms, and kebab-case for static asset names.
- Co-locate view-specific templates under `main_app/templates/main_app/` and keep URL namespace prefixes aligned with app names.

## Testing Guidelines
- Write unit tests with Django's `TestCase` (or request factory utilities) in `main_app/tests.py`; for larger suites, split into modules under `main_app/tests/`.
- Run `uv run python manage.py test` before opening a pull request. Aim for high coverage on views, Firestore service layers, and forms handling input.
- Use factories or fixtures stored under `main_app/tests/fixtures/` to keep tests deterministic; do not rely on Firestore cloud state—mock or use local emulators instead.

## Commit & Pull Request Guidelines
- Commit messages should use an imperative mood (`Add job board search view`) and stay under 72 characters. Reference issues with `Refs #id` when applicable.
- Keep pull requests focused: describe the change, call out Firestore security rule or index updates, and attach screenshots or cURL snippets when altering UI or APIs.
- Include test evidence (command output or coverage summary) and flag any follow-up tasks in the PR description.

## Security & Configuration Tips
- Never commit API keys or credentials. Load secrets via environment variables and update `settings.py` to read from them when needed.
- Review Firestore security rules and index changes carefully; test updates in a staging project before rolling them out to production.
