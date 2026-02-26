import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "clave-secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

# =========================
# BASE DE DATOS
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT UNIQUE,
        nivel TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id SERIAL PRIMARY KEY,
        alumno_id INTEGER REFERENCES alumnos(id),
        fecha DATE,
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
# RUTA RAÍZ (FIX RENDER)
# =========================
@app.route("/")
def index():
    if es_admin():
        return redirect("/dashboard")
    return redirect("/login")

# =========================
# ESTILO + HEADER
# =========================
BASE_HTML = """
<style>
body {
    margin: 0;
    background: #f2f2f2;
    font-family: Arial;
}
.header {
    position: fixed;
    top: 0;
    width: 100%;
    background: #2563eb;
    color: white;
    padding: 15px;
    display: flex;
    justify-content: center;
    gap: 25px;
}
.header a {
    color: white;
    text-decoration: none;
    font-weight: bold;
}
.container {
    max-width: 900px;
    margin: 100px auto;
    background: white;
    padding: 25px;
    border-radius: 10px;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
}
button {
    padding: 10px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
}
</style>
"""

def render_pagina(contenido):
    header = """
    <div class="header">
        <a href="/dashboard">📊 Dashboard</a>
        <a href="/asistencia">🧪 Asistencia</a>
        <a href="/alumnos">👥 Alumnos</a>
        <a href="/logout">🚪 Salir</a>
    </div>
    """
    return BASE_HTML + header + f"<div class='container'>{contenido}</div>"

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
        error = "Credenciales incorrectas"

    return render_template_string(f"""
    {BASE_HTML}
    <div class="container">
        <h2>Login</h2>
        <p style="color:red;">{error}</p>
        <form method="post">
            <input name="usuario" placeholder="Usuario" required><br><br>
            <input type="password" name="password" placeholder="Contraseña" required><br><br>
            <button>Ingresar</button>
        </form>
    </div>
    """)

# =========================
# REGISTRO ALUMNOS
# =========================
@app.route("/alumnos", methods=["GET", "POST"])
def alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        try:
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
        except:
            pass

    cur.execute("SELECT nombre, apellido, telefono, nivel FROM alumnos ORDER BY apellido")
    alumnos = cur.fetchall()
    conn.close()

    contenido = """
    <h2>Alumnos Registrados</h2>
    <form method="post">
        <input name="nombre" placeholder="Nombre" required>
        <input name="apellido" placeholder="Apellido" required>
        <input name="telefono" placeholder="Teléfono" required>
        <select name="nivel">
            <option>Inicial</option>
            <option>Intermedio</option>
            <option>Avanzado</option>
        </select>
        <button>Registrar</button>
    </form><br>
    <a href="/exportar-alumnos">📥 Descargar Excel</a><br><br>
    <table>
        <tr><th>Alumno</th><th>Teléfono</th><th>Nivel</th></tr>
    """

    for a in alumnos:
        contenido += f"<tr><td>{a[0]} {a[1]}</td><td>{a[2]}</td><td>{a[3]}</td></tr>"

    contenido += "</table>"

    return render_template_string(render_pagina(contenido))

# =========================
# ASISTENCIA
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    if not es_admin():
        return redirect("/login")

    error = ""
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM alumnos WHERE telefono=%s", (request.form["telefono"],))
        alumno = cur.fetchone()

        if alumno:
            cur.execute("""
            SELECT 1 FROM asistencias
            WHERE alumno_id=%s AND fecha=%s
            """, (alumno[0], request.form["fecha"]))

            if not cur.fetchone():
                cur.execute("""
                INSERT INTO asistencias (alumno_id, fecha, turno)
                VALUES (%s, %s, %s)
                """, (alumno[0], request.form["fecha"], request.form["turno"]))
                conn.commit()
            else:
                error = "Ya tiene turno ese día"
        else:
            error = "Alumno no registrado"

        conn.close()

    contenido = f"""
    <h2>Asistencia Laboratorio</h2>
    <p style="color:red;">{error}</p>
    <form method="post" onsubmit="return confirm('¿Confirma el turno?\\n\\n• Llevar herramientas\\n• Respetar horarios\\n• Avisar si no asiste')">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" required>
        <select name="turno">
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select>
        <button>Confirmar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT s.id, a.nombre, a.apellido, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)

    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[3]].append(d)

    contenido = "<h2>Dashboard Asistencias</h2>"

    for fecha, lista in por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Alumno</th><th>Turno</th><th>Acción</th></tr>"
        for d in lista:
            contenido += f"""
            <tr>
                <td>{d[1]} {d[2]}</td>
                <td>{d[4]}</td>
                <td><a href="/eliminar/{d[0]}" style="color:red;">🗑️</a></td>
            </tr>
            """
        contenido += "</table>"

    return render_template_string(render_pagina(contenido))

# =========================
# ELIMINAR ASISTENCIA
# =========================
@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# =========================
# EXPORTAR ALUMNOS
# =========================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, apellido, telefono, nivel FROM alumnos")
    filas = cur.fetchall()
    conn.close()

    def generar():
        yield "Nombre,Apellido,Telefono,Nivel\n"
        for f in filas:
            yield ",".join(f) + "\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=alumnos.csv"}
    )

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =========================
# RUN (RENDER)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
