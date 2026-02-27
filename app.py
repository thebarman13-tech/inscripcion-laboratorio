import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime, date, time, timedelta
from collections import defaultdict, Counter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

# =========================
# CONFIGURACIÓN
# =========================
TURNOS = [
    ("12:00 a 14:00", time(12, 0)),
    ("14:00 a 16:00", time(14, 0)),
    ("16:00 a 18:00", time(16, 0)),
]

DIAS_HABILITADOS = (1, 2, 3)  # martes, miércoles, jueves
UTC_OFFSET = -3  # Argentina

USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

# =========================
# DB
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# =========================
# UTILS
# =========================
def es_admin():
    return session.get("admin") is True

def ahora_arg():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

# =========================
# ESTILOS + LAYOUT
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

table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ccc;padding:10px;text-align:center}

.boton{display:inline-block;margin:10px 10px 10px 0;padding:10px 16px;background:#2563eb;color:white;border-radius:6px;text-decoration:none}
.eliminar{color:red;font-weight:bold;text-decoration:none}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:30px}
.stat{background:#e0e7ff;padding:20px;border-radius:10px;text-align:center}
.stat h2{margin:0;font-size:28px}
.stat p{margin:5px 0 0;font-weight:bold}

.cerrado{color:#6b7280;font-style:italic}
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
# REGISTRO ÚNICO
# =========================
@app.route("/", methods=["GET", "POST"])
def registro():
    mensaje = ""
    if request.method == "POST":
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                INSERT INTO alumnos (nombre, apellido, telefono, nivel)
                VALUES (%s, %s, %s, %s)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            db.commit()
            mensaje = "Alumno registrado correctamente."
        except psycopg2.errors.UniqueViolation:
            mensaje = "El alumno ya está registrado."
        finally:
            db.close()

    return render_template_string(render_pagina(f"""
    <h1>Registro Único de Alumno</h1>
    <p style="color:green">{mensaje}</p>

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

    <a class="boton" href="/asistencia">🧪 Ir a Asistencia</a>
    """))

# =========================
# ASISTENCIA
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""
    ok = ""
    hoy = date.today()
    ahora = ahora_arg()

    if request.method == "POST":
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        turno = request.form["turno"]

        if fecha.weekday() not in DIAS_HABILITADOS:
            error = "Solo martes, miércoles y jueves."
        elif fecha < hoy:
            error = "No se permiten fechas pasadas."
        else:
            for t, h in TURNOS:
                if t == turno and fecha == hoy and ahora.time() >= h:
                    error = "Turno cerrado por horario."

        if not error:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s", (request.form["telefono"],))
            alumno = cur.fetchone()

            if not alumno:
                error = "Alumno no registrado."
            else:
                cur.execute(
                    "SELECT 1 FROM asistencias WHERE fecha=%s AND turno=%s",
                    (fecha, turno)
                )
                if cur.fetchone():
                    error = "Ese turno ya está ocupado."
                else:
                    cur.execute(
                        "INSERT INTO asistencias (alumno_id, fecha, turno) VALUES (%s, %s, %s)",
                        (alumno[0], fecha, turno)
                    )
                    db.commit()
                    ok = "Asistencia confirmada correctamente."
            db.close()

    opciones = ""
    for t, h in TURNOS:
        if hoy == hoy and ahora.time() >= h:
            continue
        opciones += f"<option>{t}</option>"

    return render_template_string(render_pagina(f"""
    <h1>Asistencia al Laboratorio</h1>
    <p style="color:red">{error}</p>
    <p style="color:green">{ok}</p>

    <form method="post">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" min="{hoy}" required>
        <select name="turno" required>{opciones}</select>
        <button>Confirmar Turno</button>
    </form>
    """))

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    hoy = date.today()
    ahora = ahora_arg()

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM alumnos")
    total_alumnos = cur.fetchone()[0]

    cur.execute("SELECT fecha, turno FROM asistencias")
    asistencias = cur.fetchall()
    total_asistencias = len(asistencias)

    dia_mas = Counter([a[0] for a in asistencias]).most_common(1)
    turno_mas = Counter([a[1] for a in asistencias]).most_common(1)

    dia_mas = dia_mas[0][0] if dia_mas else "—"
    turno_mas = turno_mas[0][0] if turno_mas else "—"

    cur.execute("""
        SELECT s.id, s.fecha, s.turno, a.nombre, a.apellido
        FROM asistencias s
        JOIN alumnos a ON a.id = s.alumno_id
        WHERE s.fecha >= %s
        ORDER BY s.fecha
    """, (hoy,))
    rows = cur.fetchall()
    db.close()

    data = defaultdict(dict)
    for r in rows:
        data[r[1]][r[2]] = (r[3] + " " + r[4], r[0])

    html = f"""
    <h2>Dashboard</h2>

    <div class="stats">
        <div class="stat"><h2>{total_alumnos}</h2><p>Alumnos registrados</p></div>
        <div class="stat"><h2>{total_asistencias}</h2><p>Asistencias</p></div>
        <div class="stat"><h2>{dia_mas}</h2><p>Día más concurrido</p></div>
        <div class="stat"><h2>{turno_mas}</h2><p>Turno más usado</p></div>
    </div>

    <a class="boton" href="/exportar-asistencias">📄 Exportar asistencias</a>
    """

    for fecha in sorted(data.keys()):
        html += f"<h3>📅 {fecha}</h3><table>"
        html += "<tr><th>Turno</th><th>Estado</th><th>Acción</th></tr>"

        for nombre, hora_inicio in TURNOS:
            if fecha == hoy and ahora.time() >= hora_inicio:
                html += f"<tr><td>{nombre}</td><td class='cerrado'>Cerrado</td><td>-</td></tr>"
            elif nombre in data[fecha]:
                alumno, aid = data[fecha][nombre]
                html += f"""
                <tr>
                    <td>{nombre}</td>
                    <td>{alumno}</td>
                    <td><a class="eliminar" href="/eliminar-asistencia/{aid}">🗑️</a></td>
                </tr>
                """
            else:
                html += f"<tr><td>{nombre}</td><td>Libre</td><td>-</td></tr>"

        html += "</table>"

    return render_template_string(render_pagina(html))

# =========================
# EXPORTAR ASISTENCIAS
# =========================
@app.route("/exportar-asistencias")
def exportar_asistencias():
    if not es_admin():
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.fecha, s.turno, a.nombre, a.apellido, a.telefono, a.nivel
        FROM asistencias s
        JOIN alumnos a ON a.id = s.alumno_id
        ORDER BY s.fecha
    """)
    rows = cur.fetchall()
    db.close()

    def generar():
        yield "Fecha,Turno,Nombre,Apellido,Telefono,Nivel\n"
        for r in rows:
            yield ",".join(str(x) for x in r) + "\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=asistencias.csv"}
    )

# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
    return render_template_string(render_pagina("""
    <h2>Login Admin</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario">
        <input type="password" name="password" placeholder="Contraseña">
        <button>Ingresar</button>
    </form>
    """))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
