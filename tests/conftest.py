import os

import pytest

# app.py exige una cadena PostgreSQL al importarse; no se conecta hasta la primera consulta.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.pop("RENDER", None)
os.environ.pop("APP_ENV", None)

import app as app_module  # noqa: E402


@pytest.fixture
def app_ctx(monkeypatch):
    """La app con CSRF y límites desactivados, sin inicializar el esquema."""
    monkeypatch.setattr(app_module, "database_initialized", True)
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    app_module.limiter.enabled = False
    yield app_module
    app_module.limiter.enabled = True


@pytest.fixture
def client(app_ctx):
    return app_ctx.app.test_client()
