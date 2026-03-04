import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import date, datetime, timedelta
from collections import defaultdict
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta")
DATABASE_URL = os.environ.get("DATABASE_URL")

# =========================
# CONFIG
# =========================
TURNOS = [
    "12:00 a 14:00",
    "14:00 a 16:00",
    "16:00 a 18:00",
]

DIAS_HABILITADOS = (1, 2, 3)  # mar, mie, jue

FERIADOS = {
    "2026-01-01", "2026-03-24", "2026-04-02",
    "2026-05-01", "2026-07-09", "2026-12-25"
}

USUARIO_ADMIN = "DRTECNO"
PASSWORD_ADMIN = "laboratorio2026"

MENSAJE_CONFIRMACION = """
✅ Turno confirmado.

Recordar:
• Llevar herramientas personales.
• Respetar el horario elegido.
• Mantener orden y limpieza.
• Avisar por WhatsApp si no puede asistir.
"""

# =========================
# UTILS
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def es_admin():
    return session.get("admin") is True

# =========================
# BASE HTML
# =========================
BASE_HTML = """
<style>
body{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial}
.header{position:fixed;top:0;width:100%;background:#020617;border-bottom:1px solid #1e293b}
.header-inner{max-width:1200px;margin:auto;padding:16px;display:flex;justify-content:space-between}
.nav a{color:#e5e7eb;margin-left:18px;text-decoration:none}
.container{max-width:1200px;margin:110px auto 40px;background:#020617;padding:30px;border-radius:16px}
input,select,button{width:100%;padding:14px;margin-bottom:14px;border-radius:10px}
button{background:#3b82f6;border:none;color:white;font-weight:600}
.calendario{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:30px}
.dia{border:1px solid #1e293b;border-radius:14px;padding:14px}
.turno-btn{width:100%;padding:10px;margin-bottom:8px;border-radius:8px;font-weight:600}
.libre{background:#052e16;color:#22c55e}
.ocupado{background:#450a0a;color:#ef4444}
table{width:100%;border-collapse:collapse}
th,td{border:1px solid #1e293b;padding:8px;text-align:center}
.boton{display:inline-block;padding:10px 16px;background:#3b82f6;color:white;border-radius:10px;text-decoration:none;margin:6px 0}
.eliminar{color:#ef4444;text-decoration:none}
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
            msg="Alumno registrado."
        except:
            msg="Alumno ya existente."
        finally:
            db.close()

    return render_template_string(render_pagina(f"""
    <h2>Registro Único</h2>
    <p>{msg}</p>
    <form method="post">
      <input name="nombre" placeholder="Nombre" required>
      <input name="apellido" placeholder="Apellido" required>
      <input name="telefono" placeholder="Teléfono" required>
      <select name="nivel" required>
        <option>Inicial</option>
        <option>Intermedio</option>
        <option>Avanzado</option>
      </select>
      <button>Registrar</button>
    </form>
    """))

# =========================
# ASISTENCIA (CALENDARIO)
# =========================
@app.route("/asistencia", methods=["GET","POST"])
def asistencia():
    hoy = date.today()
    error=""
    ok=""

    dias=[]
    d=hoy+timedelta(days=1)
    while len(dias)<7:
        if d.weekday() in DIAS_HABILITADOS and d.isoformat() not in FERIADOS:
            dias.append(d)
        d+=timedelta(days=1)

    ocup=defaultdict(set)
    db=get_db(); cur=db.cursor()
    cur.execute("SELECT fecha,turno FROM asistencias")
    for f,t in cur.fetchall():
        ocup[str(f)].add(t)
    db.close()

    if request.method=="POST":
        fecha=request.form["fecha"]
        turno=request.form["turno"]

        if fecha in FERIADOS:
            error="Feriado."
        elif turno in ocup[fecha]:
            error="Turno ocupado."
        else:
            db=get_db(); cur=db.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))
            alu=cur.fetchone()
            if alu:
                cur.execute("INSERT INTO asistencias(alumno_id,fecha,turno) VALUES(%s,%s,%s)",(alu[0],fecha,turno))
                db.commit()
                ok=MENSAJE_CONFIRMACION
            else:
                error="Alumno no registrado."
            db.close()

    cal=""
    for d in dias:
        cal+=f"<div class='dia'><h4>{d.strftime('%a %d/%m')}</h4>"
        for t in TURNOS:
            if t in ocup[str(d)]:
                cal+=f"<button class='turno-btn ocupado' disabled>🔴 {t}</button>"
            else:
                cal+=f"<button class='turno-btn libre' onclick=\"seleccionarTurno('{d}','{t}')\">🟢 {t}</button>"
        cal+="</div>"

    return render_template_string(render_pagina(f"""
    <h2>Turnos</h2>
    <div class="calendario">{cal}</div>
    <p style="color:red">{error}</p>
    <p style="color:lightgreen;white-space:pre-line">{ok}</p>
    <form method="post">
      <input name="telefono" placeholder="Teléfono" required>
      <input type="date" name="fecha" required>
      <select name="turno">{''.join(f"<option>{t}</option>" for t in TURNOS)}</select>
      <button>Confirmar</button>
    </form>
    """))

# =========================
# DASHBOARD (RESTAURADO)
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin(): return redirect("/login")

    return render_template_string(render_pagina("""
    <h2>Dashboard</h2>
    <a class="boton" href="/dashboard/asistencias">📅 Asistencias</a><br>
    <a class="boton" href="/alumnos/Inicial">📘 Alumnos Inicial</a><br>
    <a class="boton" href="/alumnos/Intermedio">📗 Alumnos Intermedio</a><br>
    <a class="boton" href="/alumnos/Avanzado">📕 Alumnos Avanzado</a>
    """))

# =========================
# ALUMNOS POR NIVEL
# =========================
@app.route("/alumnos/<nivel>")
def alumnos_por_nivel(nivel):
    if not es_admin(): return redirect("/login")

    db=get_db(); cur=db.cursor()
    cur.execute("""
      SELECT id,nombre,apellido,telefono
      FROM alumnos WHERE nivel=%s
      ORDER BY apellido,nombre
    """,(nivel,))
    alumnos=cur.fetchall()

    html=f"<h2>Alumnos {nivel}</h2>"
    html+=f"<a class='boton' href='/exportar/{nivel}'>⬇ Exportar CSV</a><hr>"

    for aid,n,a,t in alumnos:
        cur.execute("SELECT fecha,turno FROM asistencias WHERE alumno_id=%s ORDER BY fecha",(aid,))
        asist=cur.fetchall()
        hist="; ".join(f"{f} ({tu})" for f,tu in asist) or "Sin asistencias"
        html+=f"<p><b>{a} {n}</b> 📞 {t}<br>{hist}</p><hr>"

    db.close()
    return render_template_string(render_pagina(html))

# =========================
# EXPORT CSV
# =========================
@app.route("/exportar/<nivel>")
def exportar(nivel):
    if not es_admin(): return redirect("/login")

    db=get_db(); cur=db.cursor()
    cur.execute("""
      SELECT nombre,apellido,telefono,nivel,id
      FROM alumnos WHERE nivel=%s
      ORDER BY apellido,nombre
    """,(nivel,))
    rows=cur.fetchall()

    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["Nombre","Apellido","Teléfono","Nivel","Asistencias"])

    for n,a,t,niv,aid in rows:
        cur.execute("SELECT fecha,turno FROM asistencias WHERE alumno_id=%s",(aid,))
        asist="; ".join(f"{f} {tu}" for f,tu in cur.fetchall())
        writer.writerow([n,a,t,niv,asist])

    db.close()
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":f"attachment;filename=alumnos_{nivel}.csv"})

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
