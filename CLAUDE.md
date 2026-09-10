# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SECO-TransP is a transparency evaluation framework for software ecosystem portals. It consists of two main components:

1. **Flask Backend** (`tet-website/`) - Web application with REST API, authentication, and analytics dashboards (server-rendered Jinja2 + static JS)
2. **Chrome Extension** (`tet-extension/`) - Manifest V3 extension for developers to complete evaluation tasks

## Quick Start

### Option A — everything in Docker (backend + MySQL)

```bash
cd tet-website && cp .env.example .env && cd ..
docker compose up -d --build   # builds backend image, runs migrations + seed automatically
# App at http://localhost:5000 (code hot-reloads via volume mount)
```

### Option B — MySQL in Docker, Flask in venv (better for debugging)

```bash
# 1. Start MySQL only (port 3307)
docker compose up -d db

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

## Environment Flags

Two independent flags in `.env` (read via `tet-website/config_flags.py`):

| Flag | Default | Effect |
|------|---------|--------|
| `DEV_MODE` | `False` | `True`: accounts are born verified (no SMTP needed), unverified users can sign in. `False`: email verification required. |
| `UXT_INTEGRATION` | `True` | `False`: fully local — signup/signin skip the UX-Tracking API, heatmap endpoints return empty payloads with `uxt_disabled: true` and the UI shows a disabled notice, password reset is unavailable, evaluation codes are generated locally. `True`: production behavior (calls `uxt.liis.com.br`). |

All four combinations are valid. For fully local development use `DEV_MODE=True` + `UXT_INTEGRATION=False`.

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
- `services/` - Business logic: heatmap generation/caching (`heatmap_service.py`, `heatmap_cache.py`, `heatmap_prefetch.py`), email (`email_service.py`), and **all** UX-Tracking integration (`uxt_service.py` - the single gateway for every call to the external UXT API: auth/token, password reset, evaluation-code generation, heatmap fetch)
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

### UX-Tracking integration: two tokens, never interchangeable

UXT segregates data per manager. The evaluation code embeds the id of whoever generated it (last 3 digits), the participants' sessions land in that manager's collection, and reading someone else's code returns 403. So:

- **`get_gestor_token()`** — the logged-in manager's token (stored in the session at login). The **only** valid one for data: generating evaluation codes, reading heatmaps, running analyses. When it is missing the operation fails with a clear message; it must never fall back to the service account, which sees none of that manager's data.
- **`get_service_token()`** — the integration account from `ADMIN_EMAIL`/`ADMIN_PASSWORD` (SUPERVISOR on UXT — the name is historical, it is not the portal's admin). Used **only** to provision: create the manager's UXT account at signup and promote it to MANAGER.

Heatmaps come from `GET /generate-code/used/{code}` → `POST /analysis/heatmap_summary`, which returns one image per page **with the heat already rendered** plus structured hotspots. The older `GET /view/heatmap/code/{code}` responds 200 with an empty `heatmap_images` in production — a silent empty dashboard — and now only serves the legacy `/api/view_heatmap` and `/api/heatmap-tasks` routes.

### Heatmaps in the AI analysis (`services/ai/heatmap_evidence.py`)

The same pages feed the AI layer as `HM-<n>` evidence, under the rules below — enforced in code, not in the prompt:

- **The data is the spatial distribution of recorded *interactions*, never attention.** There is no eye tracking anywhere in the product. A cold zone means no interaction was recorded there. Prompt, rule 14 and UI copy must not say *attention*, *gaze*, *saw / did not see*, *noticed* or *ignored*.
- **The image is also the page, and the model is told to read it.** Rule 14 and the prompt section instruct it to read the visible content of the capture — text, labels, links, layout — because this is the only place in the whole context where the portal's own content appears; everything else is URLs, timings and what participants wrote. Both also cap it: *report only what is legible*, since the capture has a finite resolution and the heat is drawn **over** the page. Images are sent at `MEDIA_RESOLUTION_HIGH` (1,120 tokens each), Google's recommendation for images and the API's own default — anything lower asks for less detail than Gemini gives unprompted. The level is the `MEDIA_RESOLUTION` constant in `providers/gemini.py`, deliberately not configurable, and it is applied **per part**, which is Gemini-3 only: if the fallback chain descends to a 2.x model the images may be refused, and the recovery is the text-only retry in `pipeline._analyze`.
- **The page floor is absolute (`MIN_INTERACTIONS`), never a share of the total.** A relative floor divides by the sum over *all* pages, so it errs at both ends: it tightens on its own as an evaluation covers more pages — with a flat enough distribution it discards the entire set — and it slackens exactly when data is scarce, letting 1-interaction pages through. Emptying the set that way raises its own `below_floor` reason: reusing `no_images` would blame UXT for a payload it delivered intact.
- **Context, not weight.** `metrics.AGGREGATE_TYPES` keeps heatmap out of `confidence_band` and out of the affected-participants count; `validate_findings` rejects a finding whose evidence is only `HM-<n>`.
- **No owner and no scenario:** `participant_id = None`, `task_id = None`. The image is already aggregated per URL across all sessions. `metrics.compute_finding_metrics` therefore **filters `participant_id is None`** — and it runs on every `GET`, so that filter is what stops a persisted `None` from turning the analysis endpoint into a permanent 500.
- **Aggregate evidence carries its `payload` into the snapshot** (`build_evidence_snapshot`): the finding panel reads URL, counts and hotspot coordinates from there and names each zone with `SecoHeatmaps.describeZone`, the same function the Hotspots tab uses. The `summary` string is a *prompt* format only — nothing in the UI parses it. The image, and only the image, comes from the live Hotspots payload.

The UXT token only exists inside a request: within the analysis thread `has_request_context()` is always `False` and `get_gestor_token()` returns `None` silently. It is resolved in `views/ai_analysis.py` and passed down to `build_context` — the `heatmap_prefetch.py` pattern. `fetch_pages` never raises; every failure becomes `([], reason)` (see `REASON_LABEL`) so a text-only analysis can never die because of a heatmap. `AI_HEATMAP_MAX_PAGES` (default 10, 0 disables it) is the only env flag: more pages cost tokens, never UXT time, since `fetch_pages` makes one call that already returns them all and the cut happens in memory.

### Database
- MySQL 8 (Docker Compose exposes on port 3307, database name `tool_portal`)
- SQLAlchemy ORM with Alembic/Flask-Migrate for migrations
- Alembic owns the schema — never use `db.create_all()` directly
- Reference data (guidelines, dimensions, processes, tasks, questions) seeded from `seed_data.json` via `flask seed`

## Environment Variables (.env in tet-website/)

Copy `.env.example` for Docker defaults. Key variables:

| Variable | Purpose |
|----------|---------|
| `SGBD`, `DB_USER`, `PASSW`, `SERVER`, `DATABASE` | DB connection (builds SQLAlchemy URI). `DB_USER`, never `USER` — on Linux/Mac the shell exports `USER` and it wins over `.env`. A legacy `USER` fallback still works but is deprecated. |
| `SECRET_KEY` | Flask session signing |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | **The UXT integration account, despite the name** — not the portal's admin, which is never created from `.env`. Must be **SUPERVISOR (role 3)** on UXT: it provisions each manager's UXT account at signup (`register` + promote to MANAGER). Never used to read data — see UX-Tracking integration above. |
| `DEV_MODE` | Dev vs production behavior (see Environment Flags) |
| `UXT_INTEGRATION` | UX-Tracking integration on/off (see Environment Flags) |
| `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `SENDER_PASSWORD` | Email service |

## Optional Dependencies
- spaCy with `en_core_web_sm` model for improved word cloud stopword filtering (has fallback if not installed)
