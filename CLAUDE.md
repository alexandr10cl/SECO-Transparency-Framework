# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SECO-TransP is a transparency evaluation framework for software ecosystem portals. It consists of two main components:

1. **Flask Backend** (`tet-website/`) - Web application with REST API, authentication, and analytics dashboards (server-rendered Jinja2 + static JS)
2. **Chrome Extension** (`tet-extension/`) - Manifest V3 extension for developers to complete evaluation tasks

## Quick Start

```bash
# 1. Start MySQL via Docker (port 3307)
docker-compose up -d

# 2. Setup Flask backend
cd tet-website
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env           # Pre-configured for Docker DB

# 3. Initialize database
set FLASK_APP=index.py         # Windows (export on Linux/Mac)
flask db upgrade
flask seed                     # Populate reference data (guidelines, processes, tasks, etc.)

# 4. Run
python index.py                # or: flask run --debug
```

## Common Commands

### Flask Backend (tet-website/)
```bash
python index.py                # Run dev server (entry point is index.py, NOT app.py)
flask run --debug              # Alternative via Flask CLI (set FLASK_APP=index.py first)
flask db migrate -m "msg"      # Create new migration
flask db upgrade               # Apply migrations
flask seed                     # Seed reference data from seed_data.json
```

### Chrome Extension
Load unpacked extension in Chrome (chrome://extensions/) from `tet-extension/` folder.

## Architecture

### Backend (MVC Pattern, `tet-website/`)
- **Entry point**: `index.py` - Creates Flask app, initializes SQLAlchemy/Migrate, registers blueprints and CLI commands
- **Config**: `database.py` - Builds `SQLALCHEMY_DATABASE_URI` from env vars
- `models/` - SQLAlchemy ORM models. All models exported via `models/__init__.py`
- `views/` - Route handlers: `index.py` (main), `api.py` (REST/heatmap endpoints), `auth.py` (login/signup/password reset), `admin.py`, `pages.py`
- `services/` - Business logic: heatmap generation/caching (`heatmap_service.py`, `heatmap_cache.py`, `heatmap_prefetch.py`), email (`email_service.py`), UX-Tracking token management (`uxt_token_manager.py`)
- `functions.py` - Auth helpers (`isLogged`, `isAdmin`, `login_required` decorator)
- `commands.py` - Custom Flask CLI commands (`flask seed`)
- `external/tasks.py` - Task integration logic
- `templates/` - Jinja2 HTML templates (all dashboards are server-rendered: `dashboard.html`, `dashboardv2.html`, `heatmaps.html`, `heatmap_tasks.html`)
- `static/` - CSS, JS, images

### Chrome Extension (`tet-extension/`)
- Manifest V3 with `popup.js` and `background.js`
- `popup.js` has a `CONFIG` object at the top to toggle between dev (`localhost:5000`) and production URLs via `isDevelopment` flag

### Key Data Flow
1. Portal manager creates an evaluation with selected guidelines/procedures, gets a unique code
2. Developers enter the code in the Chrome extension, complete tasks and questionnaires
3. Extension collects interaction data (navigation, feedback, answers) → sends to Flask API → stored in MySQL
4. Optional UX-Tracking integration captures additional interaction/emotion data via external API
5. Managers view analytics dashboards with heatmaps, word clouds, satisfaction charts, and KPI scores

### Database
- MySQL 8 (Docker Compose exposes on port 3307, database name `tool_portal`)
- SQLAlchemy ORM with Alembic/Flask-Migrate for migrations
- Alembic owns the schema — never use `db.create_all()` directly
- Reference data (guidelines, dimensions, processes, tasks, questions) seeded from `seed_data.json` via `flask seed`

## Environment Variables (.env in tet-website/)

Copy `.env.example` for Docker defaults. Key variables:

| Variable | Purpose |
|----------|---------|
| `SGBD`, `USER`, `PASSW`, `SERVER`, `DATABASE` | DB connection (builds SQLAlchemy URI) |
| `SECRET_KEY` | Flask session signing |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Initial admin account |
| `DEV_MODE` | Enables dev features |
| `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `SENDER_PASSWORD` | Email service |

## Optional Dependencies
- spaCy with `en_core_web_sm` model for improved word cloud stopword filtering (has fallback if not installed)
