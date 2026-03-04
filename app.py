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
  font-family:Inter, Arial, sans-serif;
  color:var(--text-main);
}

.header{
  position:fixed;
  top:0;
  width:100%;
  background:var(--bg-header);
  border-bottom:1px solid var(--border);
  z-index:10;
}

.header-inner{
  max-width:1200px;
  margin:auto;
  padding:16px 24px;
  display:flex;
  justify-content:space-between;
  align-items:center;
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

.nav a:hover{
  color:var(--primary);
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

table{
  width:100%;
  border-collapse:collapse;
  margin-top:16px;
}

th,td{
  border:1px solid var(--border);
  padding:12px;
  text-align:center;
}

th{background:#020617}

.eliminar{
  color:var(--danger);
  font-weight:bold;
  text-decoration:none;
}

.grid-alumnos{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:20px;
  margin-top:20px;
}

.card-alumno{
  background:#020617;
  border:1px solid var(--border);
  border-radius:16px;
  padding:20px;
}

.card-alumno h3{margin:0 0 8px 0}
.card-alumno .tel{color:var(--text-muted);margin-bottom:10px}
.card-alumno ul{padding-left:18px;color:var(--text-muted)}
.card-alumno .sin{color:var(--warning);font-style:italic}
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
# ASISTENCIA
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    hoy=date.today()
    error=""; ok=""

    if request.method=="POST":
        fecha_str=request.form["fecha"]
        fecha=datetime.strptime(fecha_str,"%Y-%m-%d").date()
        turno=request.form["turno"]

        if fecha.weekday() not in DIAS_HABILITADOS:
            error="Solo martes, miércoles y jueves."
        elif fecha<=hoy:
            error="Los turnos deben sacarse con al menos 24 horas de anticipación."
        elif fecha_str in FERIADOS:
            error="No se puede sacar turno en un feriado."
        else:
            db=get_db(); cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alumno=cur.fetchone()
            if not alumno:
                error="Alumno no registrado."
            else:
                cur.execute("SELECT 1 FROM asistencias WHERE fecha=%s AND turno=%s",(fecha,turno))
                if cur.fetchone():
                    error="Ese turno ya está ocupado."
                else:
                    cur.execute("INSERT INTO asistencias(alumno_id,fecha,turno) VALUES(%s,%s,%s)",(alumno[0],fecha,turno))
                    db.commit()
                    ok=MENSAJE_CONFIRMACION
            db.close()

    opciones="".join(f"<option>{t}</option>" for t in TURNOS)
    return render_template_string(render_pagina(f"""
    <h1>Asistencia al Laboratorio</h1>
    <p style="color:var(--danger)">{error}</p>
    <p style="color:var(--success);white-space:pre-line">{ok}</p>
    <form method="post">
      <input name="telefono" placeholder="Teléfono" required>
      <input type="date" name="fecha" required>
      <select name="turno" required>{opciones}</select>
      <button>Confirmar Turno</button>
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
    for aid,f,t,n,a in rows:
        dias[f][t]=(f"{n} {a}",aid)

    html="<h2>📊 Dashboard</h2><a class='boton' href='/alumnos'>👥 Historial de alumnos</a>"
    for fecha in sorted(dias.keys(),reverse=True):
        html+=f"<h3>📅 {fecha}</h3><table><tr><th>Turno</th><th>Alumno</th><th>Acción</th></tr>"
        for t in TURNOS:
            if t in dias[fecha]:
                alumno,aid=dias[fecha][t]
                html+=f"<tr><td>{t}</td><td>{alumno}</td><td><a class='eliminar' href='/eliminar-asistencia/{aid}'>🗑</a></td></tr>"
            else:
                html+=f"<tr><td>{t}</td><td>Libre</td><td>-</td></tr>"
        html+="</table>"
    return render_template_string(render_pagina(html))

# =========================
# ALUMNOS
# =========================
@app.route("/alumnos")
def alumnos_menu():
    if not es_admin(): return redirect("/login")
    return render_template_string(render_pagina("""
    <h2>📘 Historial de Alumnos</h2>
    <a class="boton" href="/alumnos/Inicial">🟢 Inicial</a>
    <a class="boton" href="/alumnos/Intermedio">🔵 Intermedio</a>
    <a class="boton" href="/alumnos/Avanzado">🟣 Avanzado</a>
    """))

@app.route("/alumnos/<nivel>")
def alumnos_por_nivel(nivel):
    if not es_admin() or nivel not in NIVELES:
        return redirect("/alumnos")

    db=get_db(); cur=db.cursor()
    cur.execute("""
      SELECT a.id,a.nombre,a.apellido,a.telefono,s.fecha,s.turno
      FROM alumnos a
      LEFT JOIN asistencias s ON s.alumno_id=a.id
      WHERE a.nivel=%s
      ORDER BY a.apellido,a.nombre,s.fecha
    """,(nivel,))
    rows=cur.fetchall(); db.close()

    alumnos=defaultdict(list); info={}
    for aid,n,a,tel,f,t in rows:
        info[aid]=(n,a,tel)
        if f: alumnos[aid].append((f,t))

    html=f"<h2>🎓 Nivel {nivel}</h2><a class='boton' href='/exportar/{nivel}'>📥 Descargar Excel</a><div class='grid-alumnos'>"
    for aid,data in info.items():
        n,a,tel=data; hist=alumnos.get(aid,[])
        html+=f"<div class='card-alumno'><h3>{n} {a}</h3><div class='tel'>📞 {tel}</div>"
        if hist:
            html+="<ul>"+"".join(f"<li>{f} – {t}</li>" for f,t in hist)+"</ul>"
        else:
            html+="<div class='sin'>Sin asistencias</div>"
        html+="</div>"
    html+="</div>"
    return render_template_string(render_pagina(html))

@app.route("/exportar/<nivel>")
def exportar_nivel(nivel):
    if not es_admin() or nivel not in NIVELES:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT 
            a.id,
            a.nombre,
            a.apellido,
            a.telefono,
            a.nivel,
            s.fecha,
            s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        WHERE a.nivel = %s
        ORDER BY a.apellido, a.nombre, s.fecha
    """, (nivel,))
    rows = cur.fetchall()
    db.close()

    # Agrupar por alumno
    alumnos = {}

    for aid, nombre, apellido, tel, nivel, fecha, turno in rows:
        if aid not in alumnos:
            alumnos[aid] = {
                "nombre": nombre,
                "apellido": apellido,
                "telefono": tel,
                "nivel": nivel,
                "asistencias": []
            }
        if fecha:
            alumnos[aid]["asistencias"].append(f"{fecha} ({turno})")

    output = StringIO()
    writer = csv.writer(output)

    # Encabezados
    writer.writerow([
        "Nombre",
        "Apellido",
        "Teléfono",
        "Nivel",
        "Cantidad de Asistencias",
        "Detalle de Asistencias"
    ])

    # Filas
    for a in alumnos.values():
        writer.writerow([
            a["nombre"],
            a["apellido"],
            a["telefono"],
            a["nivel"],
            len(a["asistencias"]),
            "; ".join(a["asistencias"])
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment;filename=alumnos_{nivel}.csv"
        }
    )
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

@app.route("/eliminar-asistencia/<int:aid>")
def eliminar_asistencia(aid):
    if not es_admin(): return redirect("/login")
    db=get_db(); cur=db.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s",(aid,))
    db.commit(); db.close()
    return redirect("/dashboard")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
