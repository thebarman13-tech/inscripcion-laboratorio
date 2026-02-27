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

DIAS_HABILITADOS = (1, 2, 3)
UTC_OFFSET = -3

USUARIO_ADMIN = "DRTECNO"
PASSWORD_ADMIN = "laboratorio2026"

NIVELES = ["Inicial", "Intermedio", "Avanzado"]

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

.boton{display:inline-block;padding:12px 18px;background:#2563eb;color:white;border-radius:8px;text-decoration:none;margin:8px}

.nivel-inicial{background:#22c55e}
.nivel-intermedio{background:#3b82f6}
.nivel-avanzado{background:#a855f7}

.eliminar{color:red;font-weight:bold;text-decoration:none}
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
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, s.fecha, s.turno, a.nombre, a.apellido
        FROM asistencias s
        JOIN alumnos a ON a.id = s.alumno_id
        ORDER BY s.fecha DESC
    """)
    rows = cur.fetchall()
    db.close()

    dias = defaultdict(dict)
    for aid, f, t, n, a in rows:
        dias[f][t] = (f"{n} {a}", aid)

    html = """
    <h2>📊 Dashboard</h2>
    <a class="boton" href="/alumnos">👥 Alumnos registrados</a>
    """

    for fecha in sorted(dias.keys(), reverse=True):
        html += f"<h3>📅 {fecha}</h3><table border=1 width=100%>"
        html += "<tr><th>Turno</th><th>Alumno</th><th>Acción</th></tr>"
        for t,_ in TURNOS:
            if t in dias[fecha]:
                alumno, aid = dias[fecha][t]
                html += f"<tr><td>{t}</td><td>{alumno}</td><td><a class='eliminar' href='/eliminar-asistencia/{aid}'>🗑</a></td></tr>"
            else:
                html += f"<tr><td>{t}</td><td>Libre</td><td>-</td></tr>"
        html += "</table>"

    return render_template_string(render_pagina(html))

# =========================
# MENU ALUMNOS
# =========================
@app.route("/alumnos")
def alumnos_menu():
    if not es_admin():
        return redirect("/login")

    html = """
    <h2>📘 Historial de Alumnos</h2>
    <p>Seleccioná un nivel:</p>

    <a class="boton nivel-inicial" href="/alumnos/Inicial">🟢 Inicial</a>
    <a class="boton nivel-intermedio" href="/alumnos/Intermedio">🔵 Intermedio</a>
    <a class="boton nivel-avanzado" href="/alumnos/Avanzado">🟣 Avanzado</a>
    """

    return render_template_string(render_pagina(html))

# =========================
# ALUMNOS POR NIVEL
# =========================
@app.route("/alumnos/<nivel>")
def alumnos_por_nivel(nivel):
    if not es_admin():
        return redirect("/login")
    if nivel not in NIVELES:
        return redirect("/alumnos")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.id, a.nombre, a.apellido, a.telefono,
               s.fecha, s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        WHERE a.nivel=%s
        ORDER BY a.apellido, a.nombre, s.fecha
    """, (nivel,))
    rows = cur.fetchall()
    db.close()

    alumnos = defaultdict(list)
    info = {}

    for aid, n, a, tel, f, t in rows:
        info[aid] = (n, a, tel)
        if f:
            alumnos[aid].append((f, t))

    html = f"""
    <h2>🎓 Nivel {nivel}</h2>
    <a class="boton" href="/exportar-alumnos/{nivel}">📥 Descargar Excel</a>
    """

    for aid, datos in info.items():
        n,a,tel = datos
        hist = alumnos.get(aid, [])
        html += f"<hr><b>{n} {a}</b><br>📞 {tel}<br>✔ Asistencias: {len(hist)}<ul>"
        for f,t in hist:
            html += f"<li>{f} – {t}</li>"
        html += "</ul>"

    return render_template_string(render_pagina(html))

# =========================
# EXPORT POR NIVEL
# =========================
@app.route("/exportar-alumnos/<nivel>")
def exportar_por_nivel(nivel):
    if not es_admin():
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.nombre, a.apellido, a.telefono, a.nivel,
               s.fecha, s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        WHERE a.nivel=%s
        ORDER BY a.apellido, a.nombre
    """, (nivel,))
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
        headers={"Content-Disposition":f"attachment;filename=alumnos_{nivel}.csv"}
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

@app.route("/eliminar-asistencia/<int:aid>")
def eliminar_asistencia(aid):
    if not es_admin():
        return redirect("/login")
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s",(aid,))
    db.commit()
    db.close()
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
