from flask import Flask, request, redirect, render_template_string, session, Response
import sqlite3
from datetime import datetime
from collections import defaultdict

# GOOGLE SHEETS
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = "clave-secreta"

DB_PATH = "database.db"
GOOGLE_CREDENTIALS = "credenciales_google.json"
SPREADSHEET_NAME = "Alumnos Laboratorio Electrónica"

# =========================
# GOOGLE SHEETS CONEXIÓN
# =========================
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS,
    scopes=scopes
)

gc = gspread.authorize(creds)
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Crear encabezados si la planilla está vacía
if sheet.row_count == 0 or sheet.cell(1, 1).value != "Nombre":
    sheet.append_row([
        "Nombre",
        "Apellido",
        "Teléfono",
        "Nivel",
        "Fecha registro"
    ])

# =========================
# BASE DE DATOS
# =========================
def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT UNIQUE,
        nivel TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alumno_id INTEGER,
        fecha TEXT,
        turno TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# LOGIN
# =========================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def es_admin():
    return "admin" in session

# =========================
# ESTILO + HEADER
# =========================
BASE_HTML = """
<style>
body {
    margin: 0;
    padding: 0;
    background: #f2f2f2;
    font-family: Arial, Helvetica, sans-serif;
}

.header {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: #2563eb;
    color: white;
    padding: 14px;
    display: flex;
    justify-content: center;
    z-index: 1000;
}

.header nav a {
    color: white;
    text-decoration: none;
    margin: 0 12px;
    font-weight: bold;
}

.container {
    max-width: 650px;
    margin: 100px auto 40px auto;
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgba(0,0,0,0.15);
}

h1, h2, h3 {
    text-align: center;
}

input, select, button {
    width: 100%;
    padding: 12px;
    margin-bottom: 12px;
    font-size: 16px;
}

button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

button:hover {
    background: #1e40af;
}
</style>
"""

def render_pagina(contenido):
    admin = es_admin()
    header = f"""
    <div class="header">
        <nav>
            {"<a href='/dashboard'>Dashboard</a><a href='/logout'>Salir</a>"
             if admin else
             "<a href='/'>Registro Alumno</a><a href='/asistencia'>Asistencia</a>"}
        </nav>
    </div>
    """
    return BASE_HTML + header + f"<div class='container'>{contenido}</div>"

# =========================
# REGISTRO ALUMNO
# =========================
@app.route("/", methods=["GET", "POST"])
def registrar_alumno():
    mensaje = ""
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (?, ?, ?, ?)
            """, (nombre, apellido, telefono, nivel))
            conn.commit()
            conn.close()

            # GUARDAR EN GOOGLE SHEETS
            sheet.append_row([
                nombre,
                apellido,
                telefono,
                nivel,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])

            mensaje = "Alumno registrado correctamente."

        except sqlite3.IntegrityError:
            mensaje = "Este alumno ya está registrado."

    contenido = f"""
    <h1>Registro Único de Alumno</h1>
    <p style="color:green;">{mensaje}</p>
    <form method="post">
        <input name="nombre" placeholder="Nombre" required>
        <input name="apellido" placeholder="Apellido" required>
        <input name="telefono" placeholder="Teléfono" required>
        <select name="nivel" required>
            <option value="">Nivel</option>
            <option>Inicial</option>
            <option>Intermedio</option>
            <option>Avanzado</option>
        </select>
        <button>Registrar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

# =========================
# ASISTENCIA (sin cambios)
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    contenido = "<h2>Asistencia (sin cambios)</h2>"
    return render_template_string(render_pagina(contenido))

# =========================
# LOGIN / DASHBOARD BÁSICO
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")

    contenido = """
    <h2>Login</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required>
        <input type="password" name="password" placeholder="Contraseña" required>
        <button>Ingresar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    contenido = "<h2>Dashboard</h2><p>Conectado correctamente</p>"
    return render_template_string(render_pagina(contenido))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
