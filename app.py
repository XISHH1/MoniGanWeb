from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from functools import wraps
from datetime import datetime
import re
import json
import os

app = Flask(__name__)
app.secret_key = "monigan_secret_key_2026"

USER = "Admin_Monigan2000"
PASSWORD = "monigan@2026"

BOT_TOKEN = "8938515287:AAGUFlhCWtU1SiQbjQvbJD4a69gi5Bt8eqk"

# Archivo donde se guardará la memoria permanentemente
ARCHIVO_DATOS = "datos_monigan.json"

# Estado por defecto (en caso de que el archivo no exista aún)
estado_por_defecto = {
    "hora": datetime.now().strftime("%H:%M"),
    "pulso": 0,
    "movimiento": 0.0,
    "estado": "Alerta",
    "alerta": "Sin señal de sensores",
    "bateria": "N/A",
    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

def cargar_memoria():
    """Lee el archivo JSON para recuperar los datos guardados"""
    if os.path.exists(ARCHIVO_DATOS):
        try:
            with open(ARCHIVO_DATOS, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("actual", estado_por_defecto.copy()), data.get("historial", [])
        except Exception as e:
            print(f"Error al leer la memoria: {e}")
    return estado_por_defecto.copy(), []

def guardar_memoria():
    """Guarda el estado actual y el historial en el archivo JSON"""
    try:
        with open(ARCHIVO_DATOS, 'w', encoding='utf-8') as f:
            json.dump({
                "actual": datos_animal,
                "historial": historial_datos
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error al guardar la memoria: {e}")

# Cargar los datos nada más encender el servidor
datos_animal, historial_datos = cargar_memoria()

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
    # Retornamos la memoria cargada
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

    # Extraer valores
    pulso_match = re.search(r"pulso\s*[:=]?\s*(\d+)", texto_lower)
    mov_match = re.search(r"mov(?:imiento)?\s*[:=]?\s*(\d+(?:\.\d+)?)", texto_lower)
    bat_match = re.search(r"bat(?:er[ií]a)?\s*[:=]?\s*(\d+)", texto_lower)

    # Actualizar valores
    pulso = int(pulso_match.group(1)) if pulso_match else datos_animal["pulso"]
    movimiento = float(mov_match.group(1)) if mov_match else datos_animal["movimiento"]
    
    if bat_match:
        bat_val = int(bat_match.group(1))
        bateria_str = f"{bat_val}%"
    else:
        bateria_str = datos_animal["bateria"]
        if bateria_str != "N/A":
            try:
                bat_val = int(bateria_str.replace('%', ''))
            except:
                bat_val = None
        else:
            bat_val = None

    # ====== LÓGICA DE ESTADOS Y RANGOS ======
    estado = "Normal"
    alerta = texto

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
    elif bat_val is not None and bat_val < 20:
        estado = "Alerta"
        alerta = f"Batería baja: {bat_val}%"
    elif bat_val is not None and bat_val > 80:
        estado = "Alerta"
        alerta = f"Batería alta: {bat_val}%"
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
    
    # Agregar copia al historial
    historial_datos.insert(0, datos_animal.copy())
    if len(historial_datos) > 20:
        historial_datos.pop()

    # === AQUÍ GUARDAMOS TODO EN EL ARCHIVO ===
    guardar_memoria()

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
