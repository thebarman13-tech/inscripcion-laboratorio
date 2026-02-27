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
.header-inner{max-width:900px;margin:auto;display:flex;justify-content:space-between}
.header a{color:white;margin-left:16px;font-weight:bold;text-decoration:none}
.container{max-width:900px;margin:110px auto;background:white;padding:30px;border-radius:12px}
input,select,button{width:100%;padding:14px;font-size:17px;margin-bottom:14px}
button{background:#2563eb;color:white;border:none;border-radius:8px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ccc;padding:10px;text-align:center}

.ocupado{background:#fecaca}
.libre{background:#bbf7d0}
.cerrado{background:#e5e7eb;font-weight:bold}

.nivel-Inicial{background:#dbeafe}
.nivel-Intermedio{background:#fef9c3}
.nivel-Avanzado{background:#dcfce7}

.eliminar{color:red;font-weight:bold;text-decoration:none}
.boton{display:inline-block;margin:10px 0;padding:10px 16px;background:#2563eb;color:white;border-radius:6px;text-decoration:none}
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
# ASISTENCIA (turnos visibles + días completos ocultos)
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    error=""
    hoy = date.today()
    cupos = {}

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT fecha, turno FROM asistencias
        WHERE fecha >= %s
    """,(hoy,))
    rows = cur.fetchall()
    db.close()

    for f,t in rows:
        cupos.setdefault(f, []).append(t)

    if request.method=="POST":
        fecha = request.form["fecha"]
        turno = request.form["turno"]
        fecha_dt = datetime.strptime(fecha,"%Y-%m-%d").date()

        if fecha_dt < hoy:
            error="No se pueden usar fechas pasadas."
        elif fecha_dt.weekday() not in (1,2,3):
            error="Solo martes, miércoles o jueves."
        elif len(cupos.get(fecha_dt,[])) >= len(TURNOS):
            error="Ese día está completo."
        else:
            db=get_db();cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alumno = cur.fetchone()

            if not alumno:
                error="Alumno no registrado."
            else:
                cur.execute("""
                    SELECT 1 FROM asistencias
                    WHERE fecha=%s AND turno=%s
                """,(fecha,turno))
                if cur.fetchone():
                    error="Ese turno ya está ocupado."
                else:
                    cur.execute("""
                        INSERT INTO asistencias(alumno_id,fecha,turno)
                        VALUES(%s,%s,%s)
                    """,(alumno[0],fecha,turno))
                    db.commit()
            db.close()

    opciones=""
    for t in TURNOS:
        opciones += f"<option>{t}</option>"

    dias_completos_js = ",".join([f"'{f}'" for f in cupos if len(cupos[f])>=len(TURNOS)])

    return render_template_string(render_pagina(f"""
    <h1>Asistencia al Laboratorio</h1>
    <p style="color:red">{error}</p>

    <form method="post"
      onsubmit="return confirm('¿Confirma la asistencia al laboratorio en el día y horario elegido?\\n\\n• Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).\\n• Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.\\n• Respetar normas de convivencia del laboratorio (orden y limpieza del puesto de trabajo).\\n• De no poder asistir dar aviso por WhatsApp para liberar el horario.')">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" id="fecha" name="fecha" min="{hoy}" required>
        <select name="turno" required>{opciones}</select>
        <button>Confirmar Turno</button>
    </form>

    <script>
    const diasCompletos = [{dias_completos_js}];
    document.getElementById("fecha").addEventListener("change", e => {{
        if (diasCompletos.includes(e.target.value)) {{
            alert("Ese día ya está completo.");
            e.target.value = "";
        }}
    }});
    </script>
    """))

# =========================
# DASHBOARD (colores por nivel)
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

    data=defaultdict(dict)
    conteo=defaultdict(int)
    for r in rows:
        data[r[1]][r[2]] = (r[3]+" "+r[4], r[5], r[0])
        conteo[r[1]] += 1

    html="<h2>Dashboard – Cupos por Día</h2>"

    for fecha in sorted(data.keys()):
        completo = conteo[fecha] >= len(TURNOS)
        html+=f"<h3>📅 {fecha}{' 🔒 COMPLETO' if completo else ''}</h3><table>"
        html+="<tr><th>Turno</th><th>Alumno</th><th>Acción</th></tr>"
        for t in TURNOS:
            if t in data[fecha]:
                alumno,nivel,aid = data[fecha][t]
                html+=f"""
                <tr class="nivel-{nivel}">
                    <td>{t}</td>
                    <td>{alumno} ({nivel})</td>
                    <td><a class="eliminar" href="/eliminar-asistencia/{aid}">🗑️</a></td>
                </tr>
                """
            else:
                html+=f"<tr class='libre'><td>{t}</td><td>Libre</td><td>-</td></tr>"
        html+="</table>"

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
