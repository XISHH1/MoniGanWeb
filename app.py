from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from functools import wraps
from datetime import datetime
import requests
import re

app = Flask(__name__)
app.secret_key = "monigan_secret_key_2026"

USER = "Admin_Monigan2000"
PASSWORD = "monigan@2026"

BOT_TOKEN = "8938515287:AAGUFlhCWtU1SiQbjQvbJD4a69gi5Bt8eqk"

datos_animal = {
    "hora": datetime.now().strftime("%H:%M"),
    "pulso": 0,
    "movimiento": 0.0,
    "estado": "Normal",
    "alerta": "Esperando datos...",
    "bateria": "N/A",
    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USER and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/estado")
@login_required
def api_estado():
    return jsonify(datos_animal)

# ====== TELEGRAM → PÁGINA ======
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    global datos_animal
    data = request.get_json(silent=True) or {}

    message = data.get("message") or data.get("channel_post") or {}
    texto = (message.get("text") or "").strip()

    if not texto:
        return jsonify({"ok": True})

    texto_lower = texto.lower()
    hora = datetime.now().strftime("%H:%M")
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Intentar leer números: pulso:72 movimiento:1.3
    pulso_match = re.search(r"pulso\s*[:=]?\s*(\d+)", texto_lower)
    mov_match = re.search(r"mov(?:imiento)?\s*[:=]?\s*(\d+(?:\.\d+)?)", texto_lower)

    pulso = int(pulso_match.group(1)) if pulso_match else datos_animal["pulso"]
    movimiento = float(mov_match.group(1)) if mov_match else datos_animal["movimiento"]

    estado = "Normal"
    alerta = texto

    if pulso > 100:
        estado = "Alerta"
        alerta = f"Pulso alto: {pulso} bpm"
    elif pulso > 0 and pulso < 40:
        estado = "Alerta"
        alerta = f"Pulso bajo: {pulso} bpm"
    elif movimiento > 1.8:
        estado = "Alerta"
        alerta = f"Movimiento intenso: {movimiento}"

    datos_animal = {
        "hora": hora,
        "pulso": pulso,
        "movimiento": movimiento,
        "estado": estado,
        "alerta": alerta,
        "bateria": "N/A",
        "ultima_actualizacion": ahora
    }

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
