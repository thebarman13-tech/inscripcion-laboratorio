import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import datetime, date
from collections import defaultdict
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta")
DATABASE_URL = os.environ.get("DATABASE_URL")

# =========================
# CONFIGURACIÓN
# =========================
TURNOS = [
    "12:00 a 14:00",
    "14:00 a 16:00",
    "16:00 a 18:00",
]

DIAS_HABILITADOS = (1, 2, 3)  # martes, miércoles, jueves

USUARIO_ADMIN = "DRTECNO"
PASSWORD_ADMIN = "laboratorio2026"

NIVELES = ["Inicial", "Intermedio", "Avanzado"]

FERIADOS = {
    "2026-01-01",
    "2026-03-24",
    "2026-04-02",
    "2026-05-01",
    "2026-07-09",
    "2026-12-25",
}

MENSAJE_CONFIRMACION = """
✅ Turno confirmado.

Recordar:
• Llevar herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).
• Respetar el horario elegido.
• Mantener orden y limpieza del puesto de trabajo.
• Si no puede asistir, avisar por WhatsApp para liberar el turno.
"""

# =========================
# UTILIDADES
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def es_admin():
    return session.get("admin") is True

# =========================
# BASE HTML – DARK MODE
# =========================
BASE_HTML = """
<style>
:root{
  --bg-main:#0f172a;
  --bg-card:#020617;
  --bg-header:#020617;
  --bg-input:#020617;
  --border:#1e293b;
  --text-main:#e5e7eb;
  --text-muted:#94a3b8;
  --primary:#3b82f6;
  --success:#22c55e;
  --danger:#ef4444;
  --warning:#f59e0b;
}

*{box-sizing:border-box}

body{
  margin:0;
  background:var(--bg-main);
  font-family:Arial, sans-serif;
  color:var(--text-main);
}

.header{
  position:fixed;
  top:0;
  width:100%;
  background:var(--bg-header);
  border-bottom:1px solid var(--border);
}

.header-inner{
  max-width:1200px;
  margin:auto;
  padding:16px 24px;
  display:flex;
  justify-content:space-between;
}

.logo{
  font-size:20px;
  font-weight:700;
}

.nav a{
  color:var(--text-main);
  margin-left:18px;
  font-weight:500;
  text-decoration:none;
}

.nav a:hover{color:var(--primary)}

.container{
  max-width:1200px;
  margin:110px auto 40px;
  background:var(--bg-card);
  padding:30px;
  border-radius:16px;
  border:1px solid var(--border);
}

input,select,button{
  width:100%;
  padding:14px;
  font-size:16px;
  margin-bottom:14px;
  border-radius:10px;
}

input,select{
  background:var(--bg-input);
  border:1px solid var(--border);
  color:var(--text-main);
}

button{
  background:var(--primary);
  border:none;
  color:white;
  font-weight:600;
  cursor:pointer;
}

button:hover{opacity:.9}

.boton{
  display:inline-block;
  padding:12px 18px;
  background:var(--primary);
  color:white;
  border-radius:10px;
  text-decoration:none;
  margin:8px 8px 8px 0;
  font-weight:600;
}

.eliminar{
  color:var(--danger);
  font-weight:bold;
  text-decoration:none;
}

.turno-libre{color:var(--success)}
.turno-ocupado{color:var(--danger)}
</style>
"""

def render_pagina(contenido):
    return BASE_HTML + f"""
    <div class="header">
      <div class="header-inner">
        <div class="logo">🔧 DRTECNO · Laboratorio</div>
        <div class="nav">
          <a href="/">Registro</a>
          <a href="/asistencia">Asistencia</a>
          {"<a href='/dashboard'>Dashboard</a><a href='/logout'>Salir</a>" if es_admin() else "<a href='/login'>Admin</a>"}
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
            db=get_db(); cur=db.cursor()
            cur.execute("""
              INSERT INTO alumnos(nombre,apellido,telefono,nivel)
              VALUES(%s,%s,%s,%s)
            """,(request.form["nombre"],request.form["apellido"],request.form["telefono"],request.form["nivel"]))
            db.commit()
            msg="Alumno registrado correctamente."
        except psycopg2.errors.UniqueViolation:
            msg="El alumno ya está registrado."
        finally:
            db.close()

    return render_template_string(render_pagina(f"""
    <h1>Registro Único de Alumno</h1>
    <p style="color:var(--success)">{msg}</p>
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
# ASISTENCIA CON CUPOS VISIBLES
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    hoy = date.today()
    error = ""
    ok = ""
    fecha_seleccionada = request.form.get("fecha")
    ocupados = set()

    if fecha_seleccionada:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT turno FROM asistencias WHERE fecha=%s", (fecha_seleccionada,))
        ocupados = {r[0] for r in cur.fetchall()}
        db.close()

    if request.method=="POST":
        fecha = datetime.strptime(fecha_seleccionada,"%Y-%m-%d").date()
        turno = request.form["turno"]

        if fecha.weekday() not in DIAS_HABILITADOS:
            error="Solo martes, miércoles y jueves."
        elif fecha<=hoy:
            error="Los turnos deben sacarse con al menos 24 horas de anticipación."
        elif fecha_seleccionada in FERIADOS:
            error="No se puede sacar turno en un feriado."
        elif turno in ocupados:
            error="Ese turno ya está ocupado."
        else:
            db=get_db(); cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alumno=cur.fetchone()
            if not alumno:
                error="Alumno no registrado."
            else:
                cur.execute(
                    "INSERT INTO asistencias(alumno_id,fecha,turno) VALUES(%s,%s,%s)",
                    (alumno[0],fecha,turno)
                )
                db.commit()
                ok=MENSAJE_CONFIRMACION
            db.close()

    opciones=""
    for t in TURNOS:
        if t in ocupados:
            opciones+=f"<option disabled class='turno-ocupado'>🔴 {t} (Ocupado)</option>"
        else:
            opciones+=f"<option class='turno-libre'>🟢 {t} (Disponible)</option>"

    return render_template_string(render_pagina(f"""
    <h1>Asistencia al Laboratorio</h1>
    <p style="color:var(--danger)">{error}</p>
    <p style="color:var(--success);white-space:pre-line">{ok}</p>
    <form method="post">
      <input name="telefono" placeholder="Teléfono" required>
      <input type="date" name="fecha" value="{fecha_seleccionada or ''}" required>
      <select name="turno" required>
        <option value="">Seleccionar turno</option>
        {opciones}
      </select>
      <button>Confirmar Turno</button>
    </form>
    """))

# =========================
# LOGIN
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
      <input name="usuario">
      <input type="password" name="password">
      <button>Ingresar</button>
    </form>
    """))

@app.route("/logout")
def logout():
    session.pop("admin",None)
    return redirect("/login")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
