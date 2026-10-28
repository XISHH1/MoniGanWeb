from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from functools import wraps
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = "monigan_secret_key_2026"

USER = "Admin_Monigan2000"
PASSWORD = "monigan@2026"

BOT_TOKEN = "8938515287:AAGUFlhCWtU1SiQbjQvbJD4a69gi5Bt8eqk"

# Estado actual (Inicia en pulso 0 y mov 0, por lo tanto "Sin señal")
datos_animal = {
    "hora": datetime.now().strftime("%H:%M"),
    "pulso": 0,
    "movimiento": 0.0,
    "estado": "Alerta",
    "alerta": "Sin señal de sensores",
    "bateria": "N/A",
    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# Historial para guardar los últimos registros (máx 20 para no saturar la memoria)
historial_datos = []

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
    # Retornamos el estado actual y el historial completo
    return jsonify({
        "actual": datos_animal,
        "historial": historial_datos
    })

# ====== TELEGRAM → PÁGINA ======
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    global datos_animal, historial_datos
    data = request.get_json(silent=True) or {}

    message = data.get("message") or data.get("channel_post") or {}
    texto = (message.get("text") or "").strip()

    if not texto:
        return jsonify({"ok": True})

    texto_lower = texto.lower()
    hora = datetime.now().strftime("%H:%M")
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Intentar leer números: pulso:72 movimiento:1.3 bateria:85
    pulso_match = re.search(r"pulso\s*[:=]?\s*(\d+)", texto_lower)
    mov_match = re.search(r"mov(?:imiento)?\s*[:=]?\s*(\d+(?:\.\d+)?)", texto_lower)
    bat_match = re.search(r"bat(?:er[ií]a)?\s*[:=]?\s*(\d+)", texto_lower)

    # Actualizar valores si vienen en el mensaje, si no, mantener los anteriores
    pulso = int(pulso_match.group(1)) if pulso_match else datos_animal["pulso"]
    movimiento = float(mov_match.group(1)) if mov_match else datos_animal["movimiento"]
    
    # Manejo numérico de la batería para poder evaluarla
    if bat_match:
        bat_val = int(bat_match.group(1))
        bateria_str = f"{bat_val}%"
    else:
        bateria_str = datos_animal["bateria"]
        # Si ya hay un porcentaje guardado de un mensaje anterior, extraemos el número
        if bateria_str != "N/A":
            bat_val = int(bateria_str.replace('%', ''))
        else:
            bat_val = None

    # ====== LÓGICA DE ESTADOS Y RANGOS ======
    estado = "Normal"
    alerta = texto

    # 1. Prioridad: Salud y conexión (Pulso y Movimiento)
    if pulso == 0 and movimiento == 0:
        estado = "Alerta"
        alerta = "Sin señal de sensores"
    elif pulso == 0:
        estado = "Alerta"
        alerta = "Sin señal de pulso"
    elif movimiento == 0:
        estado = "Alerta"
        alerta = "Sin señal de movimiento"
    elif pulso < 60:
        estado = "Alerta"
        alerta = f"Pulso bajo: {pulso} bpm"
    elif pulso > 100:
        estado = "Alerta"
        alerta = f"Pulso alto: {pulso} bpm"
    elif movimiento >= 1.8:
        estado = "Alerta"
        alerta = f"Movimiento intenso: {movimiento}"
    
    # 2. Prioridad secundaria: Batería (solo evalúa si pulso y mov están bien)
    elif bat_val is not None and bat_val < 20:
        estado = "Alerta"
        alerta = f"Batería baja: {bat_val}%"
    elif bat_val is not None and bat_val > 80:
        estado = "Alerta"
        alerta = f"Batería alta: {bat_val}%"
        
    # 3. Todo está dentro de los rangos normales (Pulso 60-100, Mov 0.1-1.7, Bat 20-80)
    else:
        estado = "Normal"
        alerta = f"Parámetros y batería normales"

    # Actualizar estado global
    datos_animal = {
        "hora": hora,
        "pulso": pulso,
        "movimiento": movimiento,
        "estado": estado,
        "alerta": alerta,
        "bateria": bateria_str,
        "ultima_actualizacion": ahora
    }
    
    # Agregar copia al historial (al inicio de la lista)
    historial_datos.insert(0, datos_animal.copy())
    
    # Mantener el historial limpio (solo los últimos 20 registros)
    if len(historial_datos) > 20:
        historial_datos.pop()

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
