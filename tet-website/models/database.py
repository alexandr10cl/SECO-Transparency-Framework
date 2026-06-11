from index import app, db


def init_db():
    """Import all models so Alembic can detect them.

    Tables are created/modified exclusively via ``flask db upgrade``.
    Never call ``db.create_all()`` directly - Alembic owns the schema.
    """
    with app.app_context():
        import models  # noqa: F401 - ensure all models are registered
