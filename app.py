import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session
from datetime import datetime, date, timedelta
from collections import defaultdict

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

FERIADOS = {
    "2026-01-01", "2026-03-24", "2026-04-02",
    "2026-05-01", "2026-07-09", "2026-12-25"
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
# BASE HTML + DARK MODE
# =========================
BASE_HTML = """
<style>
:root{
  --bg-main:#0f172a;
  --bg-card:#020617;
  --bg-header:#020617;
  --bg-input:#020617;
  --border:#1e293b;
  --text:#e5e7eb;
  --primary:#3b82f6;
  --success:#22c55e;
  --danger:#ef4444;
}

body{
  margin:0;
  background:var(--bg-main);
  font-family:Arial, sans-serif;
  color:var(--text);
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

.nav a{
  color:var(--text);
  margin-left:18px;
  text-decoration:none;
}

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
  margin-bottom:14px;
  border-radius:10px;
  font-size:16px;
}

input,select{
  background:var(--bg-input);
  border:1px solid var(--border);
  color:var(--text);
}

button{
  background:var(--primary);
  border:none;
  color:white;
  font-weight:600;
}

.turno-libre{color:var(--success)}
.turno-ocupado{color:var(--danger)}

.calendario{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:16px;
  margin-bottom:30px;
}

.dia{
  background:#020617;
  border:1px solid var(--border);
  border-radius:14px;
  padding:14px;
}

.dia h4{
  text-align:center;
  margin:0 0 10px;
}

.turno-btn{
  width:100%;
  padding:10px;
  margin-bottom:8px;
  border-radius:8px;
  border:none;
  font-weight:600;
}

.turno-btn.libre{
  background:#052e16;
  color:#22c55e;
}

.turno-btn.ocupado{
  background:#450a0a;
  color:#ef4444;
}

table{
  width:100%;
  border-collapse:collapse;
}

th,td{
  border:1px solid var(--border);
  padding:8px;
  text-align:center;
}

.eliminar{
  color:var(--danger);
  text-decoration:none;
}
</style>

<script>
function seleccionarTurno(fecha, turno){
  document.querySelector("input[name='fecha']").value = fecha;
  document.querySelector("select[name='turno']").value = turno;
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}
</script>
"""

def render_pagina(contenido):
    return BASE_HTML + f"""
    <div class="header">
      <div class="header-inner">
        <strong>🔧 DRTECNO · Laboratorio</strong>
        <div class="nav">
          <a href="/">Registro</a>
          <a href="/asistencia">Asistencia</a>
          {"<a href='/dashboard'>Dashboard</a> <a href='/logout'>Salir</a>" if es_admin() else "<a href='/login'>Admin</a>"}
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
        except:
            msg="El alumno ya está registrado."
        finally:
            db.close()

    return render_template_string(render_pagina(f"""
    <h2>Registro Único de Alumno</h2>
    <p>{msg}</p>
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
# ASISTENCIA CON CALENDARIO
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    hoy = date.today()
    error=""
    ok=""
    fecha_sel = request.form.get("fecha")

    # calcular próximos 7 días válidos
    dias=[]
    d = hoy + timedelta(days=1)
    while len(dias)<7:
        if d.weekday() in DIAS_HABILITADOS and d.isoformat() not in FERIADOS:
            dias.append(d)
        d += timedelta(days=1)

    ocupacion = defaultdict(set)
    db=get_db(); cur=db.cursor()
    cur.execute("SELECT fecha,turno FROM asistencias")
    for f,t in cur.fetchall():
        ocupacion[str(f)].add(t)
    db.close()

    if request.method=="POST":
        fecha = datetime.strptime(fecha_sel,"%Y-%m-%d").date()
        turno = request.form["turno"]

        if turno in ocupacion[fecha_sel]:
            error="Turno ocupado."
        else:
            db=get_db(); cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alumno=cur.fetchone()
            if alumno:
                cur.execute(
                    "INSERT INTO asistencias(alumno_id,fecha,turno) VALUES(%s,%s,%s)",
                    (alumno[0],fecha,turno))
                db.commit()
                ok=MENSAJE_CONFIRMACION
            else:
                error="Alumno no registrado."
            db.close()

    # calendario HTML
    cal_html=""
    for d in dias:
        cal_html+=f"<div class='dia'><h4>{d.strftime('%a %d/%m')}</h4>"
        for t in TURNOS:
            if t in ocupacion[str(d)]:
                cal_html+=f"<button class='turno-btn ocupado' disabled>🔴 {t}</button>"
            else:
                cal_html+=f"<button class='turno-btn libre' onclick=\"seleccionarTurno('{d}','{t}')\">🟢 {t}</button>"
        cal_html+="</div>"

    return render_template_string(render_pagina(f"""
    <h2>Disponibilidad de Turnos</h2>
    <div class="calendario">{cal_html}</div>

    <h3>Confirmar Asistencia</h3>
    <p style="color:red">{error}</p>
    <p style="color:green;white-space:pre-line">{ok}</p>
    <form method="post">
      <input name="telefono" placeholder="Teléfono" required>
      <input type="date" name="fecha" required>
      <select name="turno" required>
        <option value="">Turno</option>
        {''.join(f"<option>{t}</option>" for t in TURNOS)}
      </select>
      <button>Confirmar</button>
    </form>
    """))

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin(): return redirect("/login")

    db=get_db(); cur=db.cursor()
    cur.execute("""
      SELECT s.id,s.fecha,s.turno,a.nombre,a.apellido
      FROM asistencias s
      JOIN alumnos a ON a.id=s.alumno_id
      ORDER BY s.fecha DESC
    """)
    rows=cur.fetchall(); db.close()

    dias=defaultdict(dict)
    for sid,f,t,n,a in rows:
        dias[f][t]=(f"{n} {a}",sid)

    html="<h2>Dashboard</h2>"
    for fecha in sorted(dias.keys(),reverse=True):
        html+=f"<h3>{fecha}</h3><table><tr><th>Turno</th><th>Alumno</th><th></th></tr>"
        for t in TURNOS:
            if t in dias[fecha]:
                alumno,sid=dias[fecha][t]
                html+=f"<tr><td>{t}</td><td>{alumno}</td><td><a class='eliminar' href='/eliminar/{sid}'>🗑</a></td></tr>"
            else:
                html+=f"<tr><td>{t}</td><td>Libre</td><td>-</td></tr>"
        html+="</table>"
    return render_template_string(render_pagina(html))

@app.route("/eliminar/<int:sid>")
def eliminar(sid):
    if not es_admin(): return redirect("/login")
    db=get_db(); cur=db.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s",(sid,))
    db.commit(); db.close()
    return redirect("/dashboard")

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

# =========================
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
