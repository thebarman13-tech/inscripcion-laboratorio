from flask import Flask, request, redirect, render_template_string, session, Response
import psycopg2
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "clave-secreta"

# =========================
# CONEXIÓN POSTGRESQL
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        telefono TEXT UNIQUE NOT NULL,
        nivel TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id SERIAL PRIMARY KEY,
        alumno_id INTEGER REFERENCES alumnos(id) ON DELETE CASCADE,
        fecha DATE NOT NULL,
        turno TEXT NOT NULL
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
    margin: 0 15px;
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

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 8px;
    border: 1px solid #ccc;
    text-align: center;
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
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (%s, %s, %s, %s)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            conn.commit()
            conn.close()
            mensaje = "Alumno registrado correctamente."
        except psycopg2.errors.UniqueViolation:
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
# ASISTENCIA
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM alumnos WHERE telefono=%s",
            (request.form["telefono"],)
        )
        alumno = cur.fetchone()

        if not alumno:
            error = "Alumno no registrado."
        else:
            cur.execute("""
            INSERT INTO asistencias (alumno_id, fecha, turno)
            VALUES (%s, %s, %s)
            """, (
                alumno[0],
                request.form["fecha"],
                request.form["turno"]
            ))
            conn.commit()

        conn.close()

    contenido = f"""
    <h1>Asistencia Laboratorio</h1>
    <p style="color:red;">{error}</p>
    <form method="post">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" required>
        <select name="turno" required>
            <option value="">Turno</option>
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select>
        <button>Confirmar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

# =========================
# LOGIN / DASHBOARD
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

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)
    datos = cur.fetchall()
    conn.close()

    contenido = "<h2>Dashboard</h2><table>"
    contenido += """
    <tr>
        <th>Alumno</th>
        <th>Teléfono</th>
        <th>Nivel</th>
        <th>Fecha</th>
        <th>Turno</th>
    </tr>
    """
    for d in datos:
        contenido += f"""
        <tr>
            <td>{d[0]} {d[1]}</td>
            <td>{d[2]}</td>
            <td>{d[3]}</td>
            <td>{d[4]}</td>
            <td>{d[5]}</td>
        </tr>
        """
    contenido += "</table>"

    return render_template_string(render_pagina(contenido))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
