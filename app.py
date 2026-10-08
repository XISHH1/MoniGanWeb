from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "monigan_secret_key_2026"

# Usuario y contraseña
USER = "Admin_Monigan2000"
PASSWORD = "monigan@2026"

# Datos de ejemplo (después se actualizarán solos)
datos_animal = {
    "hora": "16:30",
    "pulso": 72,
    "movimiento": 1.2,
    "estado": "Normal",
    "alerta": "Sin alertas",
    "bateria": "N/A",
    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M")
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
    return render_template("dashboard.html", datos=datos_animal)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Ruta para recibir datos del ESP32 (después)
@app.route("/api/datos", methods=["POST"])
def recibir_datos():
    global datos_animal
    data = request.json
    if data:
        datos_animal["hora"] = data.get("hora", datos_animal["hora"])
        datos_animal["pulso"] = data.get("pulso", datos_animal["pulso"])
        datos_animal["movimiento"] = data.get("movimiento", datos_animal["movimiento"])
        datos_animal["estado"] = data.get("estado", datos_animal["estado"])
        datos_animal["alerta"] = data.get("alerta", datos_animal["alerta"])
        datos_animal["bateria"] = data.get("bateria", datos_animal["bateria"])
        datos_animal["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)