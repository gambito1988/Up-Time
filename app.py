import hmac
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from flask import Flask, redirect, render_template, request, send_from_directory, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "uptime.db"
WHATSAPP_NUMBER = "5491161471426"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32))


@contextmanager
def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
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
            """
        )


def admin_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


@app.before_request
def prepare_database():
    init_db()


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def assets(filename):
    return send_from_directory(BASE_DIR, filename)


@app.post("/contacto")
def contacto():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    telefono = request.form.get("telefono", "").strip()
    mensaje = request.form.get("mensaje", "").strip()

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
    app.run(debug=True)