# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SECO-TransP is a transparency evaluation framework for software ecosystem portals. It consists of three main components:

1. **Flask Backend** (`tet-website/`) - Web application with REST API, authentication, and analytics dashboards
2. **React Dashboard** (`secodashboard/`) - Standalone React app compiled into Flask static assets for data visualization
3. **Chrome Extension** (`tet-extension/`) - Manifest V3 extension for developers to complete evaluation tasks

## Common Commands

### Flask Backend (tet-website/)
```bash
# Install dependencies (from tet-website/ directory)
pip install -r requirements.txt

# Run development server
python app.py
# or
flask run --debug

# Database migrations
flask db migrate    # Create new migration
flask db upgrade    # Apply migrations
```

### React Dashboard (secodashboard/)
```bash
# Install dependencies
npm install

# Development server (proxies to Flask at localhost:5000)
npm start

# Build and deploy to Flask
npm run build-for-flask        # Linux/Mac
npm run build-for-flask-win    # Windows

# Run tests
npm test
```

### Chrome Extension
Load unpacked extension in Chrome (chrome://extensions/) from `tet-extension/` folder.

## Architecture

### Backend Structure (MVC Pattern)
- `models/` - SQLAlchemy ORM models (User, Evaluation, Task, Guideline, Questionnaire, CollectionData)
- `views/` - Flask route handlers (index.py, api.py, auth.py, admin.py, pages.py)
- `services/` - Business logic (email_service.py, heatmap_service.py, heatmap_cache.py)
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JS, images, and compiled React dashboard

### Key Data Flow
1. Extension collects user interaction data → sends to Flask API → stored in MySQL
2. Managers access web interface → dashboard renders → fetches aggregated data from API
3. Heatmaps and analytics generated server-side with caching

### Database
- MySQL with SQLAlchemy ORM
- Migrations managed via Alembic/Flask-Migrate
- Connection configured via `.env` file (SGBD, USER, PASSW, SERVER, DATABASE)

### Extension Configuration
The extension's `popup.js` has a CONFIG object at the top to switch between development (localhost:5000) and production URLs via the `isDevelopment` flag.

## Environment Variables (.env in tet-website/)
Required variables: `SGBD`, `USER`, `PASSW`, `SERVER`, `DATABASE`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEV_MODE`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`

## Optional Dependencies
- spaCy with `en_core_web_sm` model for improved word cloud stopword filtering (has fallback if not installed)
