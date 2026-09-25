"""Flujos completos contra PostgreSQL real.

Se ejecutan solo con TEST_DATABASE_URL apuntando a una base cuyo nombre contenga "test":
vacían las tablas al empezar cada prueba.
    $env:TEST_DATABASE_URL = "postgresql://postgres:clave@localhost:5432/uptime_test"
"""
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest

import app as app_module

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")
DB_NAME = urlparse(TEST_URL).path.lstrip("/")

pytestmark = pytest.mark.skipif(
    not TEST_URL or "test" not in DB_NAME,
    reason='Define TEST_DATABASE_URL con una base PostgreSQL cuyo nombre contenga "test".',
)

PASSWORD = "clave-segura-1"


@pytest.fixture
def db(app_ctx):
    app_ctx.init_db()
    with app_ctx.get_db() as connection:
        connection.execute("TRUNCATE membership_payments, service_records, users RESTART IDENTITY CASCADE")
    return app_ctx


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []
    monkeypatch.setattr(app_module, "send_email", lambda to, subject, body: sent.append((to, subject, body)) or True)
    return sent


def query(sql, params=()):
    with app_module.get_db() as connection:
        return connection.execute(sql, params).fetchall()


def register(client, username="ana", email="ana@example.com", password=PASSWORD):
    return client.post("/usuarios/registro", data={
        "username": username, "email": email, "password": password, "password_confirmation": password,
    })


def confirm(client, email="ana@example.com"):
    token = query("SELECT confirmation_token FROM users WHERE email = %s", (email,))[0]["confirmation_token"]
    return client.get(f"/usuarios/confirmar-email/{token}")


def login(client, email="ana@example.com", password=PASSWORD, **extra):
    return client.post("/usuarios/login", data={"email": email, "password": password, **extra})


@pytest.fixture
def user_client(db, client, sent_emails):
    register(client)
    confirm(client)
    assert login(client).status_code == 302
    return client


# --- Esquema ------------------------------------------------------------------

def test_init_db_is_idempotent_and_enables_rls(db):
    db.init_db()
    tables = query("SELECT relname, relrowsecurity FROM pg_class WHERE relname IN "
                   "('users', 'service_records', 'membership_payments')")
    assert len(tables) == 3 and all(row["relrowsecurity"] for row in tables)


def test_init_db_backfills_expiry_of_legacy_memberships(db):
    query("INSERT INTO users (username, membership_status, membership_started_at) "
          "VALUES ('vieja', 'active', '2026-01-01T00:00:00Z') RETURNING id")
    db.init_db()
    row = query("SELECT membership_expires_at FROM users WHERE username = 'vieja'")[0]
    assert row["membership_expires_at"] == datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=30)


# --- Registro, confirmación y login --------------------------------------------

def test_registration_sends_confirmation_and_blocks_login_until_confirmed(db, client, sent_emails):
    assert register(client).status_code == 200
    user = query("SELECT * FROM users WHERE email = 'ana@example.com'")[0]
    assert user["email_confirmed"] is False and user["password_hash"] != PASSWORD
    assert login(client).status_code == 403

    assert confirm(client).status_code == 200
    assert login(client).status_code == 302


def test_registration_rejects_duplicates_case_insensitively(db, client, sent_emails):
    register(client)
    assert register(client, username="otro", email="ANA@example.com").status_code == 409
    assert register(client, username="ANA", email="otra@example.com").status_code == 409


def test_confirmation_link_invalid_and_expired(db, client, sent_emails):
    assert client.get("/usuarios/confirmar-email/no-existe").status_code == 404
    register(client)
    query("UPDATE users SET confirmation_expires = now() - interval '1 hour' RETURNING id")
    assert confirm(client).status_code == 400
    assert login(client).status_code == 403


def test_login_wrong_password_and_open_redirect(db, client, sent_emails):
    register(client)
    confirm(client)
    assert login(client, password="incorrecta1").status_code == 401
    assert login(client, email="nadie@example.com").status_code == 401
    response = login(client, next="https://evil.example")
    assert response.headers["Location"].endswith("/usuarios")
    response = login(client, next="/membresias")
    assert response.headers["Location"].endswith("/membresias")


def test_user_dashboard_and_logout(user_client):
    response = user_client.get("/usuarios")
    assert response.status_code == 200 and b"ana@example.com" in response.data
    user_client.post("/usuarios/logout")
    assert user_client.get("/usuarios").status_code == 302


# --- Recuperación de contraseña ------------------------------------------------

def reset_token(sent_emails):
    body = sent_emails[-1][2]
    return body.split("/usuarios/restablecer/")[1].split()[0]


def test_password_reset_flow_is_single_use(db, client, sent_emails):
    register(client)
    confirm(client)
    sent_emails.clear()
    assert client.post("/usuarios/recuperar", data={"email": "ana@example.com"}).status_code == 200
    token = reset_token(sent_emails)
    stored = query("SELECT reset_token_hash FROM users")[0]["reset_token_hash"]
    assert stored and token not in stored  # solo se guarda el hash

    assert client.post(f"/usuarios/restablecer/{token}", data={
        "password": "otra-clave-9", "password_confirmation": "distinta-9"}).status_code == 400
    assert client.post(f"/usuarios/restablecer/{token}", data={
        "password": "otra-clave-9", "password_confirmation": "otra-clave-9"}).status_code == 200
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="otra-clave-9").status_code == 302
    assert client.get(f"/usuarios/restablecer/{token}").status_code == 400


def test_password_reset_does_not_reveal_accounts_or_email_unconfirmed(db, client, sent_emails):
    register(client)  # sin confirmar
    sent_emails.clear()
    unknown = client.post("/usuarios/recuperar", data={"email": "nadie@example.com"})
    unconfirmed = client.post("/usuarios/recuperar", data={"email": "ana@example.com"})
    assert unknown.status_code == unconfirmed.status_code == 200
    assert unknown.data == unconfirmed.data
    assert sent_emails == []


def test_password_reset_token_expires(db, client, sent_emails):
    register(client)
    confirm(client)
    sent_emails.clear()
    client.post("/usuarios/recuperar", data={"email": "ana@example.com"})
    token = reset_token(sent_emails)
    query("UPDATE users SET reset_expires = now() - interval '1 minute' RETURNING id")
    assert client.get(f"/usuarios/restablecer/{token}").status_code == 400


# --- Panel de administración -----------------------------------------------------

def admin_login(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secreto-largo")
    client.post("/gestion-privada/login", data={"username": "admin", "password": "secreto-largo"})


RECORD = {"username": "ana", "job": "Limpieza", "service_history": "Se limpió el equipo", "payment": "1500,50"}


def test_admin_record_shows_up_in_the_customer_dashboard(user_client, app_ctx, monkeypatch):
    admin = app_ctx.app.test_client()
    admin_login(admin, monkeypatch)
    assert admin.post("/gestion-privada/panel", data=RECORD).status_code == 302
    assert admin.post("/gestion-privada/panel", data={**RECORD, "job": "Cambio de SSD"}).status_code == 302

    page = user_client.get("/usuarios").data.decode()
    assert "Limpieza" in page and "Cambio de SSD" in page and "1500.50" in page
    assert len(query("SELECT id FROM users WHERE username = 'ana'")) == 1  # no duplica al usuario


def test_admin_validation_error_keeps_existing_data_visible(db, client, sent_emails, app_ctx, monkeypatch):
    admin = app_ctx.app.test_client()
    admin_login(admin, monkeypatch)
    admin.post("/gestion-privada/panel", data=RECORD)
    response = admin.post("/gestion-privada/panel", data={**RECORD, "payment": "abc"})
    assert response.status_code == 400
    assert b"Limpieza" in response.data  # el historial sigue visible


def test_customer_only_sees_own_records_and_cannot_repeat_others(user_client, app_ctx, monkeypatch):
    admin = app_ctx.app.test_client()
    admin_login(admin, monkeypatch)
    admin.post("/gestion-privada/panel", data={**RECORD, "username": "beto", "job": "Trabajo de Beto"})
    assert b"Trabajo de Beto" not in user_client.get("/usuarios").data
    other_id = query("SELECT id FROM service_records")[0]["id"]
    response = user_client.post(f"/usuarios/servicios/repetir/{other_id}")
    assert response.status_code == 302 and "wa.me" not in response.headers["Location"]


# --- Membresías y pagos --------------------------------------------------------

def start_checkout(client, monkeypatch, plan="basic"):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "token-de-prueba")
    calls = []

    def fake_request(path, method="GET", payload=None):
        calls.append((path, payload))
        return {"id": "pref-1", "init_point": "https://mp.example/checkout"}

    monkeypatch.setattr(app_module, "mercado_pago_request", fake_request)
    response = client.post("/membresias/confirmar", data={"plan": plan})
    return response, calls


def fake_payment(monkeypatch, reference, amount, status="approved"):
    monkeypatch.setattr(app_module, "mercado_pago_request", lambda path, **_: {
        "status": status, "external_reference": reference, "transaction_amount": amount, "currency_id": "ARS"})


def order_reference():
    return query("SELECT payment_reference FROM membership_payments ORDER BY id DESC")[0]["payment_reference"]


def test_checkout_creates_order_with_server_side_price(user_client, monkeypatch):
    response, calls = start_checkout(user_client, monkeypatch, plan="premium")
    assert response.status_code == 303 and response.headers["Location"] == "https://mp.example/checkout"
    order = query("SELECT * FROM membership_payments")[0]
    assert order["plan"] == "premium" and order["amount"] == 15000 and order["preference_id"] == "pref-1"
    assert calls[0][1]["items"][0]["unit_price"] == 15000
    assert calls[0][1]["external_reference"] == order["payment_reference"]


def test_approved_payment_activates_membership_for_30_days_and_renewal_extends(user_client, monkeypatch):
    start_checkout(user_client, monkeypatch)
    fake_payment(monkeypatch, order_reference(), 5000)
    assert app_module.apply_mercado_pago_payment("111") is True

    user = query("SELECT * FROM users")[0]
    assert user["membership_status"] == "active" and user["membership_plan"] == "basic"
    first_expiry = user["membership_expires_at"]
    remaining = first_expiry - datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < remaining <= timedelta(days=30)
    assert b"Activa hasta" in user_client.get("/usuarios").data

    assert app_module.apply_mercado_pago_payment("111") is True  # idempotente
    assert query("SELECT membership_expires_at FROM users")[0]["membership_expires_at"] == first_expiry

    start_checkout(user_client, monkeypatch)  # renovación: suma otros 30 días
    fake_payment(monkeypatch, order_reference(), 5000)
    assert app_module.apply_mercado_pago_payment("222") is True
    renewed = query("SELECT membership_expires_at FROM users")[0]["membership_expires_at"]
    assert renewed - first_expiry == timedelta(days=30)


def test_expired_membership_is_shown_as_expired(user_client, monkeypatch):
    start_checkout(user_client, monkeypatch)
    fake_payment(monkeypatch, order_reference(), 5000)
    app_module.apply_mercado_pago_payment("111")
    query("UPDATE users SET membership_expires_at = now() - interval '2 days' RETURNING id")
    page = user_client.get("/usuarios").data
    assert b"Vencida el" in page and b"Renovar" in page


def test_payment_with_wrong_amount_does_not_activate(user_client, monkeypatch):
    start_checkout(user_client, monkeypatch)
    fake_payment(monkeypatch, order_reference(), 1)
    assert app_module.apply_mercado_pago_payment("111") is False
    assert query("SELECT membership_status FROM users")[0]["membership_status"] == "inactive"
    assert query("SELECT status FROM membership_payments")[0]["status"] == "pending"


def test_refund_deactivates_membership(user_client, monkeypatch):
    start_checkout(user_client, monkeypatch)
    reference = order_reference()
    fake_payment(monkeypatch, reference, 5000)
    app_module.apply_mercado_pago_payment("111")
    fake_payment(monkeypatch, reference, 5000, status="refunded")
    assert app_module.apply_mercado_pago_payment("111") is False
    assert query("SELECT membership_status FROM users")[0]["membership_status"] == "inactive"
    assert query("SELECT status FROM membership_payments")[0]["status"] == "refunded"


def test_return_page_only_applies_own_payments(db, client, sent_emails, monkeypatch):
    register(client)
    confirm(client)
    login(client)
    start_checkout(client, monkeypatch)
    reference = order_reference()
    register(client.application.test_client(), username="beto", email="beto@example.com")
    other = client.application.test_client()
    confirm(other, email="beto@example.com")
    login(other, email="beto@example.com")

    fake_payment(monkeypatch, reference, 5000)
    assert b"Membres\xc3\xada activada" not in other.get("/membresias/pago/resultado?payment_id=111").data
    assert b"Membres\xc3\xada activada" in client.get("/membresias/pago/resultado?payment_id=111").data


def test_webhook_activates_membership_end_to_end(user_client, monkeypatch):
    start_checkout(user_client, monkeypatch)
    fake_payment(monkeypatch, order_reference(), 5000)
    monkeypatch.delenv("MERCADOPAGO_WEBHOOK_SECRET", raising=False)
    response = user_client.application.test_client().post(
        "/pagos/mercado-pago/webhook", json={"type": "payment", "data": {"id": "111"}})
    assert response.status_code == 200
    assert query("SELECT membership_status FROM users")[0]["membership_status"] == "active"
