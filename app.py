from flask import Flask, request, redirect, render_template_string, session, Response
import psycopg2
import os
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
# ESTILO GENERAL
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
    max-width: 900px;
    margin: 110px auto 40px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 0 15px rgba(0,0,0,0.15);
}

h1, h2, h3 {
    text-align: center;
}

.dashboard-buttons {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin-top: 40px;
    flex-wrap: wrap;
}

.dashboard-btn {
    width: 260px;
    height: 160px;
    background: #2563eb;
    color: white;
    border-radius: 14px;
    text-decoration: none;
    font-size: 20px;
    font-weight: bold;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    transition: transform 0.2s, background 0.2s;
}

.dashboard-btn:hover {
    background: #1e40af;
    transform: scale(1.05);
}

.dashboard-btn span {
    font-size: 48px;
    margin-bottom: 10px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}

th, td {
    padding: 8px;
    border: 1px solid #ccc;
    text-align: center;
}

.export-btn {
    display: inline-block;
    margin-bottom: 15px;
    padding: 10px 15px;
    background: #16a34a;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-weight: bold;
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
# DASHBOARD PRINCIPAL
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    contenido = """
    <h1>📊 Dashboard</h1>

    <div class="dashboard-buttons">
        <a class="dashboard-btn" href="/dashboard/asistencias">
            <span>🧪</span>
            Asistencia<br>al laboratorio
        </a>

        <a class="dashboard-btn" href="/dashboard/alumnos">
            <span>👥</span>
            Alumnos<br>registrados
        </a>
    </div>
    """
    return render_template_string(render_pagina(contenido))

# =========================
# DASHBOARD ASISTENCIAS
# =========================
@app.route("/dashboard/asistencias")
def dashboard_asistencias():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT s.id, a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha ASC
    """)
    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[5]].append(d)

    contenido = "<h2>🧪 Asistencias al laboratorio</h2>"

    for fecha in sorted(por_dia.keys()):
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += """
        <tr>
            <th>Alumno</th>
            <th>Teléfono</th>
            <th>Nivel</th>
            <th>Turno</th>
            <th>Acción</th>
        </tr>
        """
        for d in por_dia[fecha]:
            contenido += f"""
            <tr>
                <td>{d[1]} {d[2]}</td>
                <td>{d[3]}</td>
                <td>{d[4]}</td>
                <td>{d[6]}</td>
                <td>
                    <a href="/eliminar-asistencia/{d[0]}"
                       onclick="return confirm('¿Eliminar esta asistencia?')"
                       style="color:red;font-weight:bold;">
                       🗑️
                    </a>
                </td>
            </tr>
            """
        contenido += "</table>"

    return render_template_string(render_pagina(contenido))

# =========================
# DASHBOARD ALUMNOS
# =========================
@app.route("/dashboard/alumnos")
def dashboard_alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT nombre, apellido, telefono, nivel
    FROM alumnos
    ORDER BY apellido, nombre
    """)
    alumnos = cur.fetchall()
    conn.close()

    contenido = """
    <h2>👥 Alumnos registrados</h2>
    <a class="export-btn" href="/exportar-alumnos">📥 Exportar alumnos</a>
    <table>
        <tr>
            <th>Nombre</th>
            <th>Teléfono</th>
            <th>Nivel</th>
        </tr>
    """

    for a in alumnos:
        contenido += f"""
        <tr>
            <td>{a[0]} {a[1]}</td>
            <td>{a[2]}</td>
            <td>{a[3]}</td>
        </tr>
        """

    contenido += "</table>"
    return render_template_string(render_pagina(contenido))

# =========================
# EXPORTAR ALUMNOS
# =========================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    if not es_admin():
        return redirect("/login")

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
# ELIMINAR ASISTENCIA
# =========================
@app.route("/eliminar-asistencia/<int:asistencia_id>")
def eliminar_asistencia(asistencia_id):
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s", (asistencia_id,))
    conn.commit()
    conn.close()

    return redirect("/dashboard/asistencias")

# =========================
# LOGIN / LOGOUT
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

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =========================
# ASISTENCIA (PÚBLICO)
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM alumnos WHERE telefono=%s", (request.form["telefono"],))
        alumno = cur.fetchone()

        if not alumno:
            error = "Alumno no registrado."
        else:
            cur.execute("""
            SELECT 1 FROM asistencias
            WHERE alumno_id=%s AND fecha=%s
            """, (alumno[0], request.form["fecha"]))

            if cur.fetchone():
                error = "Este alumno ya tiene un turno ese día."
            else:
                cur.execute("""
                INSERT INTO asistencias (alumno_id, fecha, turno)
                VALUES (%s, %s, %s)
                """, (alumno[0], request.form["fecha"], request.form["turno"]))
                conn.commit()

        conn.close()

    contenido = f"""
    <h1>Asistencia Laboratorio</h1>
    <p style="color:red;">{error}</p>

    <form method="post"
          onsubmit="return confirm('¿Confirma la asistencia al laboratorio en el día y horario elegido?\\n\\n• Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).\\n• Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.\\n• Respetar normas de convivencia del laboratorio (orden y limpieza del puesto de trabajo).\\n• De no poder asistir dar aviso por WhatsApp para liberar el horario.')">
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=10000)
