import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime, date, time, timedelta
from collections import defaultdict
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta")
DATABASE_URL = os.environ.get("DATABASE_URL")

# =========================
# CONFIG
# =========================
TURNOS = [
    ("12:00 a 14:00", time(12, 0)),
    ("14:00 a 16:00", time(14, 0)),
    ("16:00 a 18:00", time(16, 0)),
]

DIAS_HABILITADOS = (1, 2, 3)  # martes, miércoles, jueves
UTC_OFFSET = -3

USUARIO_ADMIN = "DRTECNO"
PASSWORD_ADMIN = "laboratorio2026"

# =========================
# DB / UTILS
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def es_admin():
    return session.get("admin") is True

def ahora_arg():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

# =========================
# HTML BASE
# =========================
BASE_HTML = """
<style>
body{margin:0;background:#f2f2f2;font-family:Arial}
.header{position:fixed;top:0;width:100%;background:#2563eb;color:white;padding:16px}
.header-inner{max-width:1100px;margin:auto;display:flex;justify-content:space-between}
.header a{color:white;margin-left:16px;font-weight:bold;text-decoration:none}
.container{max-width:1100px;margin:110px auto;background:white;padding:30px;border-radius:12px}

input,select,button{width:100%;padding:14px;font-size:17px;margin-bottom:14px}
button{background:#2563eb;color:white;border:none;border-radius:8px}

.boton{display:inline-block;padding:10px 16px;background:#2563eb;color:white;border-radius:6px;text-decoration:none;margin-bottom:20px}

.nivel-inicial{border-left:6px solid #22c55e;padding-left:12px}
.nivel-intermedio{border-left:6px solid #3b82f6;padding-left:12px}
.nivel-avanzado{border-left:6px solid #a855f7;padding-left:12px}

hr{margin:25px 0}
</style>
"""

def render_pagina(contenido):
    return BASE_HTML + f"""
    <div class="header">
        <div class="header-inner">
            <div>🔧 Laboratorio Electrónica</div>
            <div>
                <a href="/">🧑 Registro</a>
                <a href="/asistencia">🧪 Asistencia</a>
                {"<a href='/dashboard'>📊 Dashboard</a><a href='/logout'>🚪 Salir</a>" if es_admin() else "<a href='/login'>🔐 Admin</a>"}
            </div>
        </div>
    </div>
    <div class="container">{contenido}</div>
    """

# =========================
# REGISTRO
# =========================
@app.route("/", methods=["GET", "POST"])
def registro():
    msg = ""
    if request.method == "POST":
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                INSERT INTO alumnos (nombre, apellido, telefono, nivel)
                VALUES (%s,%s,%s,%s)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            db.commit()
            msg = "Alumno registrado correctamente."
        except psycopg2.errors.UniqueViolation:
            msg = "El alumno ya está registrado."
        finally:
            db.close()

    return render_template_string(render_pagina(f"""
    <h1>Registro Único de Alumno</h1>
    <p style="color:green">{msg}</p>
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
        <button>Registrar Alumno</button>
    </form>
    """))

# =========================
# HISTORIAL POR NIVEL
# =========================
@app.route("/alumnos")
def alumnos():
    if not es_admin():
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.id, a.nombre, a.apellido, a.telefono, a.nivel,
               s.fecha, s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        ORDER BY a.nivel, a.apellido, a.nombre, s.fecha
    """)
    rows = cur.fetchall()
    db.close()

    niveles = {
        "Inicial": [],
        "Intermedio": [],
        "Avanzado": []
    }

    alumnos = {}
    asistencias = defaultdict(list)

    for aid, n, a, tel, niv, f, t in rows:
        alumnos[aid] = (n, a, tel, niv)
        if f:
            asistencias[aid].append((f, t))

    for aid, data in alumnos.items():
        niveles[data[3]].append(aid)

    html = """
    <h2>📘 Alumnos registrados por nivel</h2>
    <a class="boton" href="/exportar-alumnos">📥 Descargar Excel</a>
    """

    for nivel, clase in [
        ("Inicial", "nivel-inicial"),
        ("Intermedio", "nivel-intermedio"),
        ("Avanzado", "nivel-avanzado")
    ]:
        html += f"<h3 class='{clase}'>🎓 {nivel}</h3>"

        if not niveles[nivel]:
            html += "<p>No hay alumnos en este nivel.</p>"
            continue

        for aid in niveles[nivel]:
            n, a, tel, _ = alumnos[aid]
            asist = asistencias.get(aid, [])
            html += f"""
            <hr>
            <b>{n} {a}</b><br>
            📞 {tel}<br>
            ✔ Asistencias: {len(asist)}
            <ul>
            """
            for f, t in asist:
                html += f"<li>{f} – {t}</li>"
            html += "</ul>"

    return render_template_string(render_pagina(html))

# =========================
# EXPORT
# =========================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    if not es_admin():
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.nombre, a.apellido, a.telefono, a.nivel,
               s.fecha, s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        ORDER BY a.nivel, a.apellido, a.nombre
    """)
    rows = cur.fetchall()
    db.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nombre","Apellido","Teléfono","Nivel","Fecha","Turno"])
    for r in rows:
        writer.writerow(r)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=alumnos_historial.csv"}
    )

# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
    return render_template_string(render_pagina("""
    <h2>Login Admin</h2>
    <form method="post">
        <input name="usuario">
        <input type="password" name="password">
        <button>Ingresar</button>
    </form>
    """))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")
