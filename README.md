# Football Academy — Backend (Django)

A standalone Django REST API for the Football Academy. Provides endpoints for authentication, coaches, groups, players, evaluations, and PDF report generation.

## Requirements

- Python 3.11+
- pip (and optionally virtualenv)

## Setup

1) Create and activate a virtual environment

- Windows PowerShell:
  - `python -m venv venv`
  - `venv\Scripts\Activate.ps1`

2) Install dependencies

- `pip install -r requirements.txt`

3) Configure environment

- Copy `.env.example` to `.env` and edit values:

```
DJANGO_SECRET_KEY=change-this
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=*
# Uncomment to use Postgres (otherwise SQLite is used)
# DB_NAME=your_db
# DB_USER=your_user
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432
```

Notes:
- When `DJANGO_DEBUG=true`, CORS allows all origins. In production, set `DEBUG=false` and add your frontend origin to `CORS_ALLOWED_ORIGINS` in `academy/settings.py`.

4) Apply migrations and run

- `python manage.py migrate`
- `python manage.py runserver` (default `http://127.0.0.1:8000`)

## API Overview

- Base URL: `http://<host>:<port>/api/`
- Auth: JWT (SimpleJWT)
  - `POST /api/auth/token/` → `{ access, refresh }`
  - `POST /api/auth/token/refresh/`
  - `POST /api/auth/signup/`
- Resources:
  - `GET/POST /api/coaches/`
  - `GET/POST /api/groups/` and `GET /api/groups/{id}/report-pdf/`
  - `GET/POST /api/players/` and `GET /api/players/{id}/report-pdf/`

## CORS

- Dev: all origins allowed when `DEBUG=true`.
- Prod: update `CORS_ALLOWED_ORIGINS` in `academy/settings.py` to include your frontend origin (e.g., `https://app.example.com`).

## Static & Media

- Media files served in development from `MEDIA_URL` and stored in `academy/media/`.
- For production, configure proper static/media hosting.

## Deployment Checklist (Production)

- Configure environment:
  - `DJANGO_DEBUG=false`
  - `DJANGO_ALLOWED_HOSTS=<your-api-domain>,<another-domain>`
  - `DJANGO_CORS_ALLOWED_ORIGINS=https://<your-frontend-domain>`
  - `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-frontend-domain>` (if using admin/forms over HTTPS or behind proxies)
- Apply DB migrations: `python manage.py migrate`
- Collect static files: `python manage.py collectstatic`
- Create an admin user (if needed): `python manage.py createsuperuser`
- Run behind a production server (ASGI/Wsgi), e.g., `uvicorn`/`gunicorn` with a reverse proxy (Nginx/IIS/Apache) and TLS
- Monitor logs and errors; rotate secret keys appropriately