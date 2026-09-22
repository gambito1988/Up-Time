from pathlib import Path
from urllib.parse import quote

from flask import Flask, redirect, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
WHATSAPP_NUMBER = "5491161471426"

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True)