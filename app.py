import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime, date
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

TURNOS = [
    "12:00 a 14:00",
    "14:00 a 16:00",
    "16:00 a 18:00"
]

# =========================
# DB
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# =========================
# ADMIN
# =========================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def es_admin():
    return session.get("admin") is True

# =========================
# ESTILOS
# =========================
BASE_HTML = """
<style>
body{margin:0;background:#f2f2f2;font-family:Arial}
.header{position:fixed;top:0;width:100%;background:#2563eb;color:white;padding:16px}
.header-inner{max-width:1000px;margin:auto;display:flex;justify-content:space-between}
.header a{color:white;margin-left:16px;font-weight:bold;text-decoration:none}
.container{max-width:1000px;margin:110px auto;background:white;padding:30px;border-radius:12px}

input,select,button{width:100%;padding:14px;font-size:17px;margin-bottom:14px}
button{background:#2563eb;color:white;border:none;border-radius:8px}

table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ccc;padding:10px;text-align:center}

.nivel-Inicial{background:#dbeafe}
.nivel-Intermedio{background:#fef9c3}
.nivel-Avanzado{background:#dcfce7}

.eliminar{color:red;font-weight:bold;text-decoration:none}
.boton{display:inline-block;margin:10px 10px 10px 0;padding:10px 16px;background:#2563eb;color:white;border-radius:6px;text-decoration:none}

.mensaje-ok{
    background:#dcfce7;
    border:2px solid #22c55e;
    padding:20px;
    border-radius:10px;
    margin-bottom:20px;
}
.mensaje-ok h3{margin-top:0;color:#166534}
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
@app.route("/", methods=["GET","POST"])
def registro():
    msg=""
    if request.method=="POST":
        try:
            db=get_db();cur=db.cursor()
            cur.execute("""
                INSERT INTO alumnos(nombre,apellido,telefono,nivel)
                VALUES(%s,%s,%s,%s)
            """,(request.form["nombre"],request.form["apellido"],
                 request.form["telefono"],request.form["nivel"]))
            db.commit()
            msg="Alumno registrado correctamente."
        except psycopg2.errors.UniqueViolation:
            msg="El alumno ya está registrado."
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
        <button>Registrar</button>
    </form>
    """))

# =========================
# ASISTENCIA (Paso 7)
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    error=""
    mensaje_ok=""
    hoy = date.today()

    if request.method=="POST":
        fecha = datetime.strptime(request.form["fecha"],"%Y-%m-%d").date()
        turno = request.form["turno"]

        if fecha < hoy:
            error="No se permiten fechas pasadas."
        elif fecha.weekday() not in (1,2,3):
            error="Solo martes, miércoles o jueves."
        else:
            db=get_db();cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alumno = cur.fetchone()

            if not alumno:
                error="Alumno no registrado."
            else:
                cur.execute("""
                    SELECT 1 FROM asistencias
                    WHERE alumno_id=%s AND fecha=%s
                """,(alumno[0],fecha))
                if cur.fetchone():
                    error="Ya tiene un turno ese día."
                else:
                    cur.execute("""
                        INSERT INTO asistencias(alumno_id,fecha,turno)
                        VALUES(%s,%s,%s)
                    """,(alumno[0],fecha,turno))
                    db.commit()

                    mensaje_ok = f"""
                    <div class="mensaje-ok">
                        <h3>✅ Asistencia confirmada</h3>
                        <p><b>📅 Día:</b> {fecha}</p>
                        <p><b>⏰ Horario:</b> {turno}</p>
                        <ul>
                            <li>🔧 Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).</li>
                            <li>⏱️ Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.</li>
                            <li>🧹 Respetar las normas de convivencia del Laboratorio (orden y limpieza del puesto de trabajo).</li>
                            <li>📲 De no poder asistir al curso elegido dar aviso por WhatsApp para liberar el horario.</li>
                        </ul>
                    </div>
                    """
            db.close()

    opciones = "".join([f"<option>{t}</option>" for t in TURNOS])

    return render_template_string(render_pagina(f"""
    <h1>Asistencia al Laboratorio</h1>
    {mensaje_ok}
    <p style="color:red">{error}</p>

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
    db=get_db();cur=db.cursor()
    cur.execute("""
        SELECT s.id, s.fecha, s.turno, a.nombre, a.apellido, a.nivel
        FROM asistencias s
        JOIN alumnos a ON a.id = s.alumno_id
        WHERE s.fecha >= %s
        ORDER BY s.fecha
    """,(hoy,))
    rows=cur.fetchall();db.close()

    data=defaultdict(list)
    for r in rows:
        data[r[1]].append(r)

    html = """
    <h2>Dashboard – Asistencias</h2>
    <a class="boton" href="/alumnos">👥 Alumnos Registrados</a>
    """

    for fecha in sorted(data.keys()):
        html += f"<h3>📅 {fecha}</h3><table>"
        html += "<tr><th>Turno</th><th>Alumno</th><th>Nivel</th><th>Acción</th></tr>"
        for r in data[fecha]:
            html += f"""
            <tr class="nivel-{r[5]}">
                <td>{r[2]}</td>
                <td>{r[3]} {r[4]}</td>
                <td>{r[5]}</td>
                <td>
                    <a class="eliminar"
                       href="/eliminar-asistencia/{r[0]}"
                       onclick="return confirm('¿Eliminar esta asistencia?')">
                       🗑️
                    </a>
                </td>
            </tr>
            """
        html += "</table>"

    return render_template_string(render_pagina(html))

# =========================
# ELIMINAR ASISTENCIA
# =========================
@app.route("/eliminar-asistencia/<int:aid>")
def eliminar_asistencia(aid):
    if not es_admin():
        return redirect("/login")

    db=get_db();cur=db.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s",(aid,))
    db.commit();db.close()
    return redirect("/dashboard")

# =========================
# ALUMNOS
# =========================
@app.route("/alumnos")
def alumnos():
    if not es_admin():
        return redirect("/login")

    db=get_db();cur=db.cursor()
    cur.execute("SELECT id,nombre,apellido,telefono,nivel FROM alumnos ORDER BY apellido")
    rows=cur.fetchall();db.close()

    html = """
    <h2>Alumnos Registrados</h2>
    <a class="boton" href="/exportar-alumnos">📥 Exportar alumnos</a>
    <table>
    <tr><th>Nombre</th><th>Teléfono</th><th>Nivel</th><th>Acción</th></tr>
    """

    for r in rows:
        html += f"""
        <tr class="nivel-{r[4]}">
            <td>{r[1]} {r[2]}</td>
            <td>{r[3]}</td>
            <td>{r[4]}</td>
            <td><a class="eliminar" href="/eliminar-alumno/{r[0]}">🗑️</a></td>
        </tr>
        """

    html += "</table>"
    return render_template_string(render_pagina(html))

# =========================
# ELIMINAR ALUMNO
# =========================
@app.route("/eliminar-alumno/<int:aid>")
def eliminar_alumno(aid):
    if not es_admin():
        return redirect("/login")

    db=get_db();cur=db.cursor()
    cur.execute("SELECT 1 FROM asistencias WHERE alumno_id=%s",(aid,))
    if cur.fetchone():
        db.close()
        return redirect("/alumnos")

    cur.execute("DELETE FROM alumnos WHERE id=%s",(aid,))
    db.commit();db.close()
    return redirect("/alumnos")

# =========================
# EXPORTAR
# =========================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    if not es_admin():
        return redirect("/login")

    db=get_db();cur=db.cursor()
    cur.execute("SELECT nombre,apellido,telefono,nivel FROM alumnos")
    rows=cur.fetchall();db.close()

    def gen():
        yield "Nombre,Apellido,Telefono,Nivel\n"
        for r in rows:
            yield ",".join(r) + "\n"

    return Response(gen(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=alumnos.csv"})

# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["usuario"]==USUARIO_ADMIN and request.form["password"]==PASSWORD_ADMIN:
            session["admin"]=True
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
    session.pop("admin",None)
    return redirect("/login")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
