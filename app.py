import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "clave-secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

CUPOS_POR_TURNO = {
    "12:00 a 14:00": 1,
    "14:00 a 16:00": 1,
    "16:00 a 18:00": 1
}

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

@app.route("/")
def index():
    if es_admin():
        return redirect("/dashboard")
    return redirect("/login")

# =========================
# ESTILO (VISUAL GRANDE)
# =========================
BASE_HTML = """
<style>
body {
    margin: 0;
    background: #f2f2f2;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 18px;
}
.header {
    position: fixed;
    top: 0;
    width: 100%;
    background: #2563eb;
    color: white;
    padding: 16px;
    display: flex;
    justify-content: center;
    gap: 30px;
    z-index: 1000;
}
.header a {
    color: white;
    text-decoration: none;
    font-weight: bold;
    font-size: 18px;
}
.container {
    max-width: 900px;
    margin: 110px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 0 15px rgba(0,0,0,0.15);
}
h1, h2, h3 {
    text-align: center;
}
input, select, button {
    width: 100%;
    padding: 14px;
    font-size: 18px;
    margin-bottom: 14px;
}
button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}
button:hover {
    background: #1e40af;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    border: 1px solid #ccc;
    padding: 10px;
    text-align: center;
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
# LOGIN (GRANDE Y CENTRADO)
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
    <div class="container" style="max-width:500px;">
        <h1>🔐 Login Administrador</h1>
        <p style="color:red;text-align:center;">{error}</p>
        <form method="post">
            <input name="usuario" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button>Ingresar</button>
        </form>
    </div>
    """)

# =========================
# ALUMNOS
# =========================
@app.route("/alumnos")
def alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, apellido, telefono, nivel FROM alumnos ORDER BY apellido")
    alumnos = cur.fetchall()
    conn.close()

    contenido = "<h2>👥 Alumnos Registrados</h2>"
    contenido += "<a href='/exportar-alumnos'>📥 Descargar Excel</a>"
    contenido += "<table><tr><th>Alumno</th><th>Teléfono</th><th>Nivel</th></tr>"

    for a in alumnos:
        contenido += f"<tr><td>{a[0]} {a[1]}</td><td>{a[2]}</td><td>{a[3]}</td></tr>"

    contenido += "</table>"
    return render_template_string(render_pagina(contenido))

# =========================
# ASISTENCIA CON CUPOS
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    if not es_admin():
        return redirect("/login")

    mensaje = ""
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        fecha = request.form["fecha"]
        turno = request.form["turno"]

        cur.execute("SELECT id FROM alumnos WHERE telefono=%s", (request.form["telefono"],))
        alumno = cur.fetchone()

        if not alumno:
            mensaje = "Alumno no registrado"
        else:
            cur.execute("""
            SELECT 1 FROM asistencias
            WHERE alumno_id=%s AND fecha=%s
            """, (alumno[0], fecha))

            if cur.fetchone():
                mensaje = "El alumno ya tiene turno ese día"
            else:
                cur.execute("""
                SELECT COUNT(*) FROM asistencias
                WHERE fecha=%s AND turno=%s
                """, (fecha, turno))

                usados = cur.fetchone()[0]

                if usados >= CUPOS_POR_TURNO[turno]:
                    mensaje = "Cupo completo para ese turno"
                else:
                    cur.execute("""
                    INSERT INTO asistencias (alumno_id, fecha, turno)
                    VALUES (%s, %s, %s)
                    """, (alumno[0], fecha, turno))
                    conn.commit()
                    mensaje = "Turno confirmado correctamente"

        conn.close()

    contenido = f"""
    <h2>🧪 Asistencia al Laboratorio</h2>
    <p style="color:red;text-align:center;">{mensaje}</p>
    <form method="post"
          onsubmit="return confirm('¿Confirma la asistencia al laboratorio en el día y horario elegido?\\n\\n• Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).\\n• Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.\\n• Respetar normas de convivencia del laboratorio (orden y limpieza del puesto de trabajo).\\n• De no poder asistir dar aviso por WhatsApp para liberar el horario.')">
        <input name="telefono" placeholder="Teléfono del alumno" required>
        <input type="date" name="fecha" required>
        <select name="turno" required>
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select>
        <button>Confirmar turno</button>
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
    ORDER BY s.fecha ASC
    """)

    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[3]].append(d)

    contenido = "<h2>📊 Dashboard – Asistencias</h2>"

    for fecha, lista in por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Alumno</th><th>Turno</th><th>Acción</th></tr>"
        for d in lista:
            contenido += f"""
            <tr>
                <td>{d[1]} {d[2]}</td>
                <td>{d[4]}</td>
                <td><a href="/eliminar/{d[0]}" style="color:red;">🗑️ Eliminar</a></td>
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
