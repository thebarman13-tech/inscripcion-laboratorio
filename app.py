import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from datetime import date, timedelta
from collections import defaultdict
import csv
import io

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

DIAS_HABILITADOS = (1,2,3)

FERIADOS = {
    "2026-01-01","2026-03-24","2026-04-02",
    "2026-05-01","2026-07-09","2026-12-25"
}

USUARIO_ADMIN="DRTECNO"
PASSWORD_ADMIN="laboratorio2026"

MENSAJE_CONFIRMACION = """
✅ Turno confirmado.

Recordar:
• Llevar herramientas personales.
• Respetar el horario elegido.
• Mantener orden y limpieza.
• Avisar si no puede asistir.
"""

# =========================
# UTILIDADES
# =========================

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def es_admin():
    return session.get("admin") is True

# =========================
# ESTILO BASE
# =========================

BASE_HTML="""
<style>

body{margin:0;background:#0f172a;color:#e5e7eb;font-family:Arial}

.header{
position:fixed;
top:0;
width:100%;
background:#020617;
border-bottom:1px solid #1e293b
}

.header-inner{
max-width:1200px;
margin:auto;
padding:16px;
display:flex;
justify-content:space-between
}

.nav a{
color:#e5e7eb;
margin-left:18px;
text-decoration:none
}

.container{
max-width:1200px;
margin:110px auto 40px;
background:#020617;
padding:30px;
border-radius:16px
}

input,select,button{
width:100%;
padding:14px;
margin-bottom:14px;
border-radius:10px
}

button{
background:#3b82f6;
border:none;
color:white;
font-weight:600
}

.calendario{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:16px;
margin-bottom:30px
}

.dia{
border:1px solid #1e293b;
border-radius:14px;
padding:14px
}

.turno-btn{
width:100%;
padding:10px;
margin-bottom:8px;
border-radius:8px;
font-weight:600
}

.libre{
background:#052e16;
color:#22c55e
}

.ocupado{
background:#450a0a;
color:#ef4444
}

.grid-cards{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:16px;
margin-top:20px
}

.card{
background:#020617;
border:1px solid #1e293b;
border-radius:14px;
padding:16px
}

.card h4{margin:0 0 8px}
.card small{color:#94a3b8}

table{
width:100%;
border-collapse:collapse;
margin-top:20px
}

th,td{
border:1px solid #1e293b;
padding:8px;
text-align:center
}

.boton{
display:inline-block;
padding:10px 16px;
background:#3b82f6;
color:white;
border-radius:10px;
text-decoration:none;
margin:6px 6px 6px 0
}

.eliminar{
display:inline-block;
margin-top:10px;
color:#ef4444;
text-decoration:none;
font-weight:600
}

</style>

<script>
function seleccionarTurno(fecha,turno){
document.querySelector("input[name='fecha']").value=fecha
document.querySelector("select[name='turno']").value=turno
window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})
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

<div class="container">
{contenido}
</div>
"""

# =========================
# REGISTRO ALUMNO
# =========================

@app.route("/",methods=["GET","POST"])
def registro():

    msg=""

    if request.method=="POST":

        try:

            db=get_db()
            cur=db.cursor()

            cur.execute("""
            INSERT INTO alumnos(nombre,apellido,telefono,nivel)
            VALUES(%s,%s,%s,%s)
            """,(request.form["nombre"],request.form["apellido"],request.form["telefono"],request.form["nivel"]))

            db.commit()
            msg="Alumno registrado correctamente."

        except:
            msg="El alumno ya existe."

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
<option>Inicial</option>
<option>Intermedio</option>
<option>Avanzado</option>
</select>

<button>Registrar</button>

</form>

"""))

# =========================
# ASISTENCIA
# =========================

@app.route("/asistencia",methods=["GET","POST"])
def asistencia():

    hoy=date.today()

    error=""
    ok=""

    dias=[]

    d=hoy+timedelta(days=1)

    while len(dias)<7:

        if d.weekday() in DIAS_HABILITADOS and d.isoformat() not in FERIADOS:
            dias.append(d)

        d+=timedelta(days=1)

    ocup=defaultdict(set)

    db=get_db()
    cur=db.cursor()

    cur.execute("SELECT fecha,turno FROM asistencias")

    for f,t in cur.fetchall():
        ocup[str(f)].add(t)

    db.close()

    if request.method=="POST":

        fecha=request.form["fecha"]
        turno=request.form["turno"]
        motivo=request.form["motivo"]

        if fecha in FERIADOS:

            error="No se puede reservar en feriado."

        elif turno in ocup[fecha]:

            error="Turno ocupado."

        else:

            db=get_db()
            cur=db.cursor()

            cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(request.form["telefono"],))

            alu=cur.fetchone()

            if alu:

                cur.execute("""
                INSERT INTO asistencias(alumno_id,fecha,turno,motivo)
                VALUES(%s,%s,%s,%s)
                """,(alu[0],fecha,turno,motivo))

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

                cal+=f"<button class='turno-btn libre' onclick=\\"seleccionarTurno('{d}','{t}')\\">🟢 {t}</button>"

        cal+="</div>"

    return render_template_string(render_pagina(f"""

<h2>Disponibilidad de Turnos</h2>

<div class="calendario">

{cal}

</div>

<p style="color:red">{error}</p>
<p style="color:lightgreen;white-space:pre-line">{ok}</p>

<form method="post">

<input name="telefono" placeholder="Teléfono" required>

<input type="date" name="fecha" required>

<select name="turno">
{''.join(f"<option>{t}</option>" for t in TURNOS)}
</select>

<select name="motivo" required>

<option value="">Motivo de la asistencia</option>
<option>Problema en placa</option>
<option>Software</option>
<option>Cambio de piezas</option>
<option>Diagnóstico</option>
<option>Otro</option>

</select>

<button>Confirmar Asistencia</button>

</form>

"""))

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("""

    SELECT
    s.id,
    s.fecha,
    s.turno,
    s.motivo,
    a.nombre,
    a.apellido

    FROM asistencias s

    JOIN alumnos a
    ON a.id=s.alumno_id

    ORDER BY s.fecha DESC

    """)

    rows=cur.fetchall()

    db.close()

    dias=defaultdict(dict)

    for sid,f,t,m,n,a in rows:

        dias[f][t]=(f"{n} {a}",m,sid)

    html="""

<h2>Dashboard</h2>

<a class="boton" href="/alumnos/Inicial">📘 Inicial</a>
<a class="boton" href="/alumnos/Intermedio">📗 Intermedio</a>
<a class="boton" href="/alumnos/Avanzado">📕 Avanzado</a>

"""

    for fecha in sorted(dias.keys(),reverse=True):

        html+=f"<h3>{fecha}</h3>"

        html+="<table>"
        html+="<tr><th>Turno</th><th>Alumno</th><th>Motivo</th><th></th></tr>"

        for t in TURNOS:

            if t in dias[fecha]:

                alumno,motivo,sid=dias[fecha][t]

                html+=f"<tr><td>{t}</td><td>{alumno}</td><td>{motivo}</td><td><a class='eliminar' href='/eliminar/{sid}'>🗑</a></td></tr>"

            else:

                html+=f"<tr><td>{t}</td><td>Libre</td><td>-</td><td>-</td></tr>"

        html+="</table>"

    return render_template_string(render_pagina(html))

# =========================
# ELIMINAR ASISTENCIA
# =========================

@app.route("/eliminar/<int:sid>")
def eliminar(sid):

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("DELETE FROM asistencias WHERE id=%s",(sid,))

    db.commit()
    db.close()

    return redirect("/dashboard")

# =========================
# LOGIN
# =========================

@app.route("/login",methods=["GET","POST"])
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

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.pop("admin",None)

    return redirect("/login")

# =========================

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
