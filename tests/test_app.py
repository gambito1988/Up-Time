import hashlib
import hmac
from contextlib import contextmanager

import pytest

import app as app_module


# --- Páginas públicas ---------------------------------------------------------

def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_home_serves_landing(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Up Time" in response.data


@pytest.mark.parametrize("path", ["/styles.css", "/index.html"])
def test_public_assets_are_served(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/script.js", "/app.py", "/requirements.txt", "/render.yaml", "/.env", "/CLAUDE.md"])
def test_source_files_are_not_served(client, path):
    assert client.get(path).status_code == 404


def test_contact_redirects_to_whatsapp(client):
    response = client.post(
        "/contacto",
        data={"nombre": "Ana", "email": "ana@example.com", "telefono": "1", "mensaje": "No enciende"},
    )
    assert response.status_code == 303
    assert response.headers["Location"].startswith(f"https://wa.me/{app_module.WHATSAPP_NUMBER}?text=")
    assert "Ana" in response.headers["Location"]


def test_contact_requires_fields(client):
    response = client.post("/contacto", data={"nombre": "Ana"})
    assert response.status_code == 400


def test_membership_page_lists_plans(client):
    response = client.get("/membresias")
    assert response.status_code == 200
    for plan in app_module.MEMBERSHIP_PLANS.values():
        assert plan["name"].encode() in response.data


# --- Redirecciones y autenticación -------------------------------------------

@pytest.mark.parametrize("value", [
    "https://evil.example", "//evil.example", "/\\evil.example", "/%5cevil.example",
    "javascript:alert(1)", "/ok\r\nSet-Cookie: x=1", "", None,
])
def test_safe_next_url_rejects_external_targets(value):
    assert app_module.safe_next_url(value, "/default") == "/default"


def test_safe_next_url_accepts_local_paths():
    assert app_module.safe_next_url("/membresias", "/default") == "/membresias"


@pytest.mark.parametrize("path", ["/usuarios", "/membresias/pago/resultado"])
def test_user_pages_redirect_to_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/usuarios/login" in response.headers["Location"]


def test_admin_panel_redirects_when_anonymous(client):
    response = client.get("/gestion-privada/panel")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/gestion-privada")


def test_admin_login_rejects_bad_credentials(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secreto-largo")
    response = client.post("/gestion-privada/login", data={"username": "admin", "password": "otra"})
    assert response.status_code == 401


def test_admin_login_fails_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    response = client.post("/gestion-privada/login", data={"username": "", "password": ""})
    assert response.status_code == 401


def test_admin_login_and_session_expiry(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secreto-largo")
    response = client.post("/gestion-privada/login", data={"username": "admin", "password": "secreto-largo"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/gestion-privada/panel")

    with client.session_transaction() as session:
        assert session["admin_authenticated"] is True
        session["admin_at"] -= app_module.ADMIN_SESSION_SECONDS + 1
    response = client.get("/gestion-privada/panel")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/gestion-privada")


def test_membership_selection_requires_login(client):
    response = client.post("/membresias/seleccionar", data={"plan": "basic"})
    assert response.status_code == 302
    assert "/usuarios/login" in response.headers["Location"]


def test_membership_selection_ignores_unknown_plan(client):
    response = client.post("/membresias/seleccionar", data={"plan": "gratis"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/membresias")


def test_membership_checkout_without_mercadopago_token(client, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN", raising=False)
    with client.session_transaction() as session:
        session["user_id"] = 1
    response = client.post("/membresias/confirmar", data={"plan": "basic"})
    assert response.status_code == 503


# --- Registro: validaciones que no llegan a la base --------------------------

@pytest.mark.parametrize("form", [
    {"username": "", "email": "a@example.com", "password": "12345678", "password_confirmation": "12345678"},
    {"username": "ana", "email": "no-es-email", "password": "12345678", "password_confirmation": "12345678"},
    {"username": "ana", "email": "a@example.com", "password": "corta", "password_confirmation": "corta"},
    {"username": "ana", "email": "a@example.com", "password": "12345678", "password_confirmation": "distinta1"},
    {"username": "x" * 101, "email": "a@example.com", "password": "12345678", "password_confirmation": "12345678"},
])
def test_registration_rejects_invalid_input(client, form):
    response = client.post("/usuarios/registro", data=form)
    assert response.status_code == 400


# --- Seguridad transversal ----------------------------------------------------

def test_csrf_blocks_post_without_token(app_ctx):
    app_ctx.app.config["WTF_CSRF_ENABLED"] = True
    response = app_ctx.app.test_client().post("/usuarios/login", data={"email": "a@example.com", "password": "x"})
    assert response.status_code == 400
    assert "caducó".encode() in response.data


def test_webhook_is_exempt_from_csrf(app_ctx, monkeypatch):
    app_ctx.app.config["WTF_CSRF_ENABLED"] = True
    monkeypatch.delenv("MERCADOPAGO_WEBHOOK_SECRET", raising=False)
    response = app_ctx.app.test_client().post("/pagos/mercado-pago/webhook", json={})
    assert response.status_code == 200


def test_login_is_rate_limited(app_ctx, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secreto-largo")
    app_ctx.limiter.enabled = True
    app_ctx.limiter.reset()
    client = app_ctx.app.test_client()
    statuses = [
        client.post("/gestion-privada/login", data={"username": "admin", "password": "mal"}).status_code
        for _ in range(7)
    ]
    assert statuses[:5] == [401] * 5
    assert statuses[5:] == [429, 429]
    app_ctx.limiter.reset()


def test_session_cookie_flags(app_ctx):
    assert app_ctx.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app_ctx.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


# --- Webhook de Mercado Pago ---------------------------------------------------

def sign(secret, data_id, request_id, timestamp):
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    return hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()


def test_webhook_rejects_missing_or_wrong_signature(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "clave")
    url = "/pagos/mercado-pago/webhook?data.id=123&type=payment"
    assert client.post(url).status_code == 401
    bad = {"x-signature": "ts=1,v1=deadbeef", "x-request-id": "abc"}
    assert client.post(url, headers=bad).status_code == 401


def test_webhook_accepts_valid_signature_and_applies_payment(client, monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "clave")
    applied = []
    monkeypatch.setattr(app_module, "apply_mercado_pago_payment", lambda payment_id: applied.append(payment_id))
    headers = {"x-signature": f"ts=1,v1={sign('clave', '123', 'abc', '1')}", "x-request-id": "abc"}
    response = client.post("/pagos/mercado-pago/webhook?data.id=123&type=payment", headers=headers)
    assert response.status_code == 200
    assert applied == ["123"]


def test_webhook_returns_500_when_mercadopago_fails(client, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_WEBHOOK_SECRET", raising=False)

    def fail(payment_id):
        raise RuntimeError("caído")

    monkeypatch.setattr(app_module, "apply_mercado_pago_payment", fail)
    response = client.post("/pagos/mercado-pago/webhook?data.id=123&type=payment")
    assert response.status_code == 500


# --- Lógica de pagos con una base simulada ------------------------------------

class FakeResult:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, order):
        self.order = order
        self.writes = []

    def execute(self, query, params=()):
        if query.lstrip().startswith("SELECT"):
            return FakeResult(self.order)
        self.writes.append((query, params))
        return FakeResult(None)


@pytest.fixture
def fake_payment(monkeypatch):
    """Devuelve una función que ejecuta apply_mercado_pago_payment con un pago y pedido simulados."""

    def run(payment, order, **kwargs):
        connection = FakeConnection(order)

        @contextmanager
        def fake_get_db():
            yield connection

        monkeypatch.setattr(app_module, "get_db", fake_get_db)
        monkeypatch.setattr(app_module, "mercado_pago_request", lambda path, **_: payment)
        return app_module.apply_mercado_pago_payment("99", **kwargs), connection

    return run


ORDER = {"id": 1, "user_id": 7, "plan": "basic", "amount": 5000.0, "status": "pending", "mp_payment_id": None}
PAYMENT = {"status": "approved", "external_reference": "ref", "transaction_amount": 5000, "currency_id": "ARS"}


def test_approved_payment_activates_membership(fake_payment):
    approved, connection = fake_payment(PAYMENT, ORDER)
    assert approved is True
    assert any("membership_status = 'active'" in query for query, _ in connection.writes)


def test_payment_with_wrong_amount_is_not_applied(fake_payment):
    approved, connection = fake_payment({**PAYMENT, "transaction_amount": 1}, ORDER)
    assert approved is False
    assert connection.writes == []


def test_payment_with_wrong_currency_is_not_applied(fake_payment):
    approved, connection = fake_payment({**PAYMENT, "currency_id": "USD"}, ORDER)
    assert approved is False
    assert connection.writes == []


def test_already_approved_order_is_idempotent(fake_payment):
    approved, connection = fake_payment(PAYMENT, {**ORDER, "status": "approved", "mp_payment_id": "99"})
    assert approved is True
    assert connection.writes == []


def test_payment_of_another_user_is_ignored(fake_payment):
    approved, connection = fake_payment(PAYMENT, ORDER, expected_user_id=8)
    assert approved is False
    assert connection.writes == []


def test_refund_deactivates_membership(fake_payment):
    order = {**ORDER, "status": "approved", "mp_payment_id": "99"}
    approved, connection = fake_payment({**PAYMENT, "status": "refunded"}, order)
    assert approved is False
    assert any("membership_status = 'inactive'" in query for query, _ in connection.writes)


def test_late_rejection_does_not_override_approved_order(fake_payment):
    order = {**ORDER, "status": "approved", "mp_payment_id": "99"}
    approved, connection = fake_payment({**PAYMENT, "status": "rejected"}, order)
    assert approved is False
    assert connection.writes == []


def test_non_numeric_payment_id_is_rejected(app_ctx):
    assert app_ctx.apply_mercado_pago_payment("1; DROP TABLE users") is False


# --- Webhook sin clave y vencimiento de membresías ------------------------------

def test_webhook_without_secret_is_rejected_in_production(client, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(app_module, "IS_PRODUCTION", True)
    response = client.post("/pagos/mercado-pago/webhook?data.id=123&type=payment")
    assert response.status_code == 401


def test_membership_state():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    state = app_module.membership_state
    assert state({"membership_status": "inactive"}) == "inactive"
    assert state({"membership_status": "active", "membership_expires_at": now + timedelta(days=1)}) == "active"
    assert state({"membership_status": "active", "membership_expires_at": now - timedelta(days=1)}) == "expired"
    assert state({"membership_status": "active", "membership_expires_at": None}) == "active"
