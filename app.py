import hmac
import json
import os
import secrets
import smtplib
import sqlite3
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from urllib.parse import quote

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from email_validator import EmailNotValidError, validate_email
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "uptime.db"))
WHATSAPP_NUMBER = "5491161471426"
PUBLIC_ASSETS = {"index.html", "styles.css", "script.js"}
MEMBERSHIP_PLANS = {
    "basic": {"name": "Basic", "price": 5000, "description": "Soporte remoto y prioridad estándar."},
    "intermedio": {"name": "Intermedio", "price": 9000, "description": "Soporte remoto y una visita mensual."},
    "premium": {"name": "Premium", "price": 15000, "description": "Atención prioritaria y dos visitas mensuales."},
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32))
app.config["PREFERRED_URL_SCHEME"] = "https"
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
database_initialized = False
database_init_lock = threading.Lock()


@contextmanager
def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS service_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job TEXT NOT NULL,
                payment REAL NOT NULL DEFAULT 0,
                service_history TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS membership_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_reference TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                amount REAL NOT NULL,
                preference_id TEXT,
                mp_payment_id TEXT UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            """
        )
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        migrations = {
            "email": "TEXT",
            "password_hash": "TEXT",
            "email_confirmed": "INTEGER NOT NULL DEFAULT 0",
            "confirmation_token": "TEXT",
            "confirmation_expires": "TEXT",
            "membership_plan": "TEXT",
            "membership_status": "TEXT NOT NULL DEFAULT 'inactive'",
            "membership_started_at": "TEXT",
        }
        for column, definition in migrations.items():
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique "
            "ON users(email COLLATE NOCASE) WHERE email IS NOT NULL"
        )


def user_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("user_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


@app.before_request
def prepare_database():
    global database_initialized
    if database_initialized:
        return None
    try:
        with database_init_lock:
            if not database_initialized:
                init_db()
                database_initialized = True
    except sqlite3.Error:
        app.logger.exception("No se pudo inicializar la base de datos")
        if request.path == "/usuarios/registro" and request.method == "POST":
            return render_template(
                "user_register.html",
                error="La base de datos no está disponible. Intenta nuevamente en unos minutos.",
            ), 503
        raise


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/<path:filename>")
def assets(filename):
    if filename not in PUBLIC_ASSETS:
        abort(404)
    return send_from_directory(BASE_DIR, filename)


@app.post("/contacto")
def contacto():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    telefono = request.form.get("telefono", "").strip()
    mensaje = request.form.get("mensaje", "").strip()
    if not nombre or not email or not mensaje:
        return redirect(url_for("home") + "#contacto"), 400

    texto = (
        "Hola, me gustaría contactarme con Up Time.\n\n"
        f"Nombre: {nombre}\n"
        f"Email: {email}\n"
        f"Teléfono: {telefono}\n\n"
        f"Mensaje: {mensaje}"
    )
    return redirect(
        f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(texto)}",
        code=303,
    )


def send_confirmation_email(email, confirmation_url):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    if not all((smtp_host, smtp_user, smtp_password)):
        return False

    message = EmailMessage()
    message["Subject"] = "Confirma tu email - Up Time"
    message["From"] = os.environ.get("SMTP_FROM", smtp_user)
    message["To"] = email
    message.set_content(
        "Confirma tu cuenta de Up Time abriendo este enlace:\n\n"
        f"{confirmation_url}\n\nEste enlace vence en 24 horas."
    )
    try:
        with smtplib.SMTP(smtp_host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as server:
            if os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as error:
        app.logger.warning("No se pudo enviar el email de confirmacion: %s", error)
        return False
    return True


def mercado_pago_request(path, method="GET", payload=None):
    access_token = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("Mercado Pago no está configurado.")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_data = Request(
        f"https://api.mercadopago.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request_data, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        app.logger.warning("Error al comunicarse con Mercado Pago: %s", error)
        raise RuntimeError("No se pudo iniciar o verificar el pago. Intenta nuevamente.") from error


def apply_mercado_pago_payment(payment_id):
    payment = mercado_pago_request(f"/v1/payments/{payment_id}")
    reference = payment.get("external_reference")
    if not reference:
        return False
    with get_db() as connection:
        order = connection.execute(
            "SELECT * FROM membership_payments WHERE payment_reference = ?", (reference,)
        ).fetchone()
        if not order:
            return False
        if payment.get("status") == "approved":
            connection.execute(
                "UPDATE membership_payments SET mp_payment_id = ?, status = 'approved', paid_at = ? WHERE id = ?",
                (str(payment_id), datetime.now(timezone.utc).isoformat(), order["id"]),
            )
            connection.execute(
                "UPDATE users SET membership_plan = ?, membership_status = 'active', membership_started_at = ? WHERE id = ?",
                (order["plan"], datetime.now(timezone.utc).isoformat(), order["user_id"]),
            )
            return True
        connection.execute(
            "UPDATE membership_payments SET mp_payment_id = ?, status = ? WHERE id = ?",
            (str(payment_id), payment.get("status", "pending"), order["id"]),
        )
    return False


@app.get("/usuarios/registro")
def user_register():
    if session.get("user_id"):
        return redirect(url_for("user_dashboard"))
    return render_template("user_register.html")


@app.post("/usuarios/registro")
def user_register_submit():
    username = request.form.get("username", "").strip()
    raw_email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    password_confirmation = request.form.get("password_confirmation", "")
    try:
        email = validate_email(raw_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        email = ""
    if not username or not email or len(password) < 8 or password != password_confirmation:
        return render_template(
            "user_register.html",
            error="Completa los datos y usa una contraseña de al menos 8 caracteres.",
        ), 400

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    try:
        with get_db() as connection:
            existing_email = connection.execute(
                "SELECT id FROM users WHERE lower(email) = ?", (email,)
            ).fetchone()
            if existing_email:
                return render_template("user_register.html", error="Ese email ya está registrado."), 409
            existing_username = connection.execute(
                "SELECT id FROM users WHERE lower(username) = ?", (username.lower(),)
            ).fetchone()
            if existing_username:
                return render_template("user_register.html", error="Ese nombre de usuario ya está registrado."), 409
            connection.execute(
                """
                INSERT INTO users (username, email, password_hash, email_confirmed,
                    confirmation_token, confirmation_expires)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (username, email, generate_password_hash(password), token, expires.isoformat()),
            )
    except sqlite3.IntegrityError:
        return render_template("user_register.html", error="El usuario o email ya está registrado."), 409
    except sqlite3.Error:
        app.logger.exception("No se pudo guardar el nuevo usuario")
        return render_template(
            "user_register.html",
            error="No se pudo crear la cuenta en este momento. Intenta nuevamente.",
        ), 503
    except Exception:
        app.logger.exception("Error inesperado durante el registro")
        return render_template(
            "user_register.html",
            error="No se pudo crear la cuenta en este momento. Intenta nuevamente.",
        ), 503

    confirmation_url = url_for("confirm_email", token=token, _external=True)
    email_sent = send_confirmation_email(email, confirmation_url)
    return render_template(
        "registration_complete.html",
        email=email,
        email_sent=email_sent,
    )


@app.post("/usuarios/reenviar-confirmacion")
def resend_confirmation_email():
    try:
        email = validate_email(
            request.form.get("email", "").strip(), check_deliverability=False
        ).normalized.lower()
    except EmailNotValidError:
        email = ""

    if email:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        with get_db() as connection:
            user = connection.execute(
                "SELECT id FROM users WHERE email = ? AND email_confirmed = 0", (email,)
            ).fetchone()
            if user:
                connection.execute(
                    "UPDATE users SET confirmation_token = ?, confirmation_expires = ? WHERE id = ?",
                    (token, expires, user["id"]),
                )
                confirmation_url = url_for("confirm_email", token=token, _external=True)
                send_confirmation_email(email, confirmation_url)
    return render_template("registration_complete.html", email=email or "esa dirección", email_sent=True)


@app.get("/usuarios/confirmar-email/<token>")
def confirm_email(token):
    with get_db() as connection:
        user = connection.execute(
            "SELECT id, confirmation_expires FROM users WHERE confirmation_token = ?",
            (token,),
        ).fetchone()
        if not user:
            return render_template("confirmation_result.html", error="El enlace no es valido."), 404
        expires = datetime.fromisoformat(user["confirmation_expires"])
        if expires < datetime.now(timezone.utc):
            return render_template("confirmation_result.html", error="El enlace ya vencio."), 400
        connection.execute(
            "UPDATE users SET email_confirmed = 1, confirmation_token = NULL, confirmation_expires = NULL WHERE id = ?",
            (user["id"],),
        )
    return render_template("confirmation_result.html", confirmed=True)


@app.get("/usuarios/login")
def user_login():
    if session.get("user_id"):
        return redirect(url_for("user_dashboard"))
    return render_template("user_login.html")


@app.post("/usuarios/login")
def user_login_submit():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    with get_db() as connection:
        user = connection.execute(
            "SELECT id, password_hash, email_confirmed FROM users WHERE lower(email) = ?",
            (email,),
        ).fetchone()
    if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], password):
        return render_template("user_login.html", error="Email o contraseña incorrectos."), 401
    if not user["email_confirmed"]:
        return render_template("user_login.html", error="Confirma tu email antes de ingresar."), 403
    session.clear()
    session["user_id"] = user["id"]
    next_url = request.form.get("next", "")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = url_for("user_dashboard")
    return redirect(next_url)


@app.post("/usuarios/logout")
@user_required
def user_logout():
    session.clear()
    return redirect(url_for("user_login"))


@app.get("/usuarios")
@user_required
def user_dashboard():
    with get_db() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        records = connection.execute(
            "SELECT * FROM service_records WHERE user_id = ? ORDER BY created_at DESC, id DESC",
            (session["user_id"],),
        ).fetchall()
    return render_template("user_dashboard.html", user=user, records=records)


@app.post("/usuarios/servicios/repetir/<int:record_id>")
@user_required
def repeat_service(record_id):
    with get_db() as connection:
        record = connection.execute(
            "SELECT job FROM service_records WHERE id = ? AND user_id = ?",
            (record_id, session["user_id"]),
        ).fetchone()
    if not record:
        return redirect(url_for("user_dashboard"))
    texto = f"Hola, quiero volver a solicitar el servicio: {record['job']}"
    return redirect(f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(texto)}", code=303)


@app.get("/membresias")
def memberships():
    return render_template("memberships.html", plans=MEMBERSHIP_PLANS)


@app.post("/membresias/seleccionar")
def select_membership():
    plan = request.form.get("plan", "")
    if plan not in MEMBERSHIP_PLANS:
        return redirect(url_for("memberships"))
    if not session.get("user_id"):
        return redirect(url_for("user_login", next=url_for("memberships")))
    return render_template("membership_checkout.html", plan=MEMBERSHIP_PLANS[plan], plan_key=plan)


@app.post("/membresias/confirmar")
@user_required
def confirm_membership():
    plan = request.form.get("plan", "")
    if plan not in MEMBERSHIP_PLANS:
        return redirect(url_for("memberships"))
    plan_data = MEMBERSHIP_PLANS[plan]
    if not os.environ.get("MERCADOPAGO_ACCESS_TOKEN"):
        return render_template(
            "membership_checkout.html",
            plan=plan_data,
            plan_key=plan,
            error="El medio de pago aún no está configurado. Intenta nuevamente más tarde.",
        ), 503
    payment_reference = secrets.token_urlsafe(24)
    with get_db() as connection:
        user = connection.execute(
            "SELECT username, email FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        connection.execute(
            "INSERT INTO membership_payments (payment_reference, user_id, plan, amount) VALUES (?, ?, ?, ?)",
            (payment_reference, session["user_id"], plan, plan_data["price"]),
        )
    try:
        preference = mercado_pago_request(
            "/checkout/preferences",
            method="POST",
            payload={
                "items": [{
                    "id": f"membership-{plan}",
                    "title": f"Membresía Up Time - {plan_data['name']}",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": plan_data["price"],
                }],
                "payer": {"name": user["username"], "email": user["email"]},
                "external_reference": payment_reference,
                "back_urls": {
                    "success": url_for("membership_payment_result", _external=True),
                    "failure": url_for("membership_payment_result", _external=True),
                    "pending": url_for("membership_payment_result", _external=True),
                },
                "notification_url": url_for("mercado_pago_webhook", _external=True),
            },
        )
    except RuntimeError as error:
        return render_template("membership_checkout.html", plan=plan_data, plan_key=plan, error=str(error)), 503

    checkout_url = preference.get(
        "sandbox_init_point" if os.environ.get("MERCADOPAGO_SANDBOX", "").lower() in {"1", "true", "yes"} else "init_point"
    )
    if not checkout_url:
        app.logger.error("Mercado Pago no devolvió una URL de checkout: %s", preference)
        return render_template("membership_checkout.html", plan=plan_data, plan_key=plan, error="No se pudo iniciar el pago."), 503
    with get_db() as connection:
        connection.execute(
            "UPDATE membership_payments SET preference_id = ? WHERE payment_reference = ?",
            (preference.get("id"), payment_reference),
        )
    return redirect(checkout_url, code=303)


@app.post("/pagos/mercado-pago/webhook")
def mercado_pago_webhook():
    notification = request.get_json(silent=True) or {}
    payment_id = (
        notification.get("data", {}).get("id")
        or request.args.get("data.id")
        or request.args.get("id")
    )
    notification_type = notification.get("type") or request.args.get("type") or request.args.get("topic")
    if payment_id and notification_type in {"payment", None}:
        try:
            apply_mercado_pago_payment(payment_id)
        except RuntimeError:
            # Mercado Pago reintentará el webhook si respondemos con error.
            return "", 500
    return "", 200


@app.get("/membresias/pago/resultado")
@user_required
def membership_payment_result():
    payment_id = request.args.get("payment_id") or request.args.get("collection_id")
    approved = False
    if payment_id:
        try:
            approved = apply_mercado_pago_payment(payment_id)
        except RuntimeError:
            pass
    return render_template("membership_pending.html", approved=approved)


@app.get("/gestion-privada")
def admin_login():
    if session.get("admin_authenticated"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.post("/gestion-privada/login")
def admin_login_submit():
    configured_username = os.environ.get("ADMIN_USERNAME")
    configured_password = os.environ.get("ADMIN_PASSWORD")
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    valid_credentials = (
        configured_username
        and configured_password
        and hmac.compare_digest(username, configured_username)
        and hmac.compare_digest(password, configured_password)
    )
    if not valid_credentials:
        return render_template("admin_login.html", error="Credenciales invalidas"), 401

    session.clear()
    session["admin_authenticated"] = True
    return redirect(url_for("admin_dashboard"))


@app.post("/gestion-privada/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/gestion-privada/panel", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        job = request.form.get("job", "").strip()
        service_history = request.form.get("service_history", "").strip()
        payment_text = request.form.get("payment", "0").strip().replace(",", ".")

        try:
            payment = float(payment_text)
        except ValueError:
            payment = -1

        if not username or not job or not service_history or payment < 0:
            return render_template(
                "admin_dashboard.html",
                users=[] ,
                records=[],
                error="Completa todos los campos y usa un pago valido.",
            ), 400

        with get_db() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO users (username) VALUES (?)", (username,)
            )
            user = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO service_records (user_id, job, payment, service_history)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], job, payment, service_history),
            )
        return redirect(url_for("admin_dashboard"))

    with get_db() as connection:
        users = connection.execute(
            "SELECT id, username, created_at FROM users ORDER BY username"
        ).fetchall()
        records = connection.execute(
            """
            SELECT service_records.*, users.username
            FROM service_records
            JOIN users ON users.id = service_records.user_id
            ORDER BY service_records.created_at DESC, service_records.id DESC
            """
        ).fetchall()
    return render_template("admin_dashboard.html", users=users, records=records)


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
    )
