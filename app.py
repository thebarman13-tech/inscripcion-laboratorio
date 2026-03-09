import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session
from datetime import date, timedelta, datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","clave-secreta")

DATABASE_URL = os.environ.get("DATABASE_URL")

TURNOS = [
"12:00 a 14:00",
"14:00 a 16:00",
"16:00 a 18:00"
]

DIAS_HABILITADOS=(1,2,3)

FERIADOS={
"2026-01-01",
"2026-03-24",
"2026-04-02",
"2026-05-01",
"2026-07-09",
"2026-12-25"
}

USUARIO_ADMIN="DRTECNO"
PASSWORD_ADMIN="laboratorio2026"

# ======================
# CONEXION DB
# ======================

def get_db():
    return psycopg2.connect(DATABASE_URL,sslmode="require")

def es_admin():
    return session.get("admin") == True


# ======================
# HTML BASE
# ======================

BASE_HTML="""
<style>

body{
background:#0f172a;
color:white;
font-family:Arial;
margin:0
}

.header{
background:#020617;
padding:16px;
display:flex;
justify-content:space-between
}

.nav a{
color:white;
margin-left:14px;
text-decoration:none
}

.container{
max-width:1100px;
margin:40px auto;
background:#020617;
padding:30px;
border-radius:14px
}

input,select,button{
width:100%;
padding:12px;
margin-bottom:10px;
border-radius:8px
}

button{
background:#3b82f6;
color:white;
border:none
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:16px
}

.card{
background:#020617;
border:1px solid #1e293b;
padding:16px;
border-radius:10px
}

.boton{
display:inline-block;
padding:10px 16px;
background:#3b82f6;
border-radius:10px;
color:white;
text-decoration:none;
margin:6px 6px 6px 0
}

.eliminar{
color:#ef4444;
text-decoration:none
}

table{
width:100%;
border-collapse:collapse
}

th,td{
border:1px solid #1e293b;
padding:8px;
text-align:center
}

</style>
"""

def render_pagina(html):

    return BASE_HTML+f"""

<div class="header">

<strong>🔧 DRTECNO LAB</strong>

<div class="nav">

<a href="/">Registro</a>
<a href="/asistencia">Asistencia</a>

{"<a href='/dashboard'>Dashboard</a> <a href='/logout'>Salir</a>" if es_admin() else "<a href='/login'>Admin</a>"}

</div>

</div>

<div class="container">

{html}

</div>
"""


# ======================
# LOGIN
# ======================

@app.route("/login",methods=["GET","POST"])
def login():

    error=""

    if request.method=="POST":

        if request.form["user"]==USUARIO_ADMIN and request.form["pass"]==PASSWORD_ADMIN:

            session["admin"]=True
            return redirect("/dashboard")

        else:

            error="Datos incorrectos"

    return render_template_string(render_pagina(f"""

<h2>Login Admin</h2>

<p style='color:red'>{error}</p>

<form method="post">

<input name="user" placeholder="Usuario">
<input name="pass" type="password" placeholder="Password">

<button>Ingresar</button>

</form>

"""))


@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")


# ======================
# REGISTRO ALUMNOS
# ======================

@app.route("/",methods=["GET","POST"])
def registro():

    msg=""

    if request.method=="POST":

        db=get_db()
        cur=db.cursor()

        cur.execute("""
        INSERT INTO alumnos(nombre,apellido,telefono,nivel)
        VALUES(%s,%s,%s,%s)
        """,(request.form["nombre"],request.form["apellido"],request.form["telefono"],request.form["nivel"]))

        db.commit()
        db.close()

        msg="Alumno registrado"

    return render_template_string(render_pagina(f"""

<h2>Registro alumno</h2>

<p>{msg}</p>

<form method="post">

<input name="nombre" placeholder="Nombre" required>
<input name="apellido" placeholder="Apellido" required>
<input name="telefono" placeholder="Teléfono" required>

<select name="nivel">
<option>Inicial</option>
<option>Intermedio</option>
<option>Avanzado</option>
</select>

<button>Registrar</button>

</form>

"""))


# ======================
# TURNOS
# ======================

@app.route("/asistencia",methods=["GET","POST"])
def asistencia():

    hoy=date.today()

    error=""
    ok=""

    db=get_db()
    cur=db.cursor()

    cur.execute("SELECT fecha,turno FROM asistencias")

    ocup=defaultdict(set)

    for f,t in cur.fetchall():

        ocup[str(f)].add(t)

    if request.method=="POST":

        telefono=request.form["telefono"]
        fecha=request.form["fecha"]
        turno=request.form["turno"]

        cur.execute("SELECT id FROM alumnos WHERE telefono=%s",(telefono,))
        alu=cur.fetchone()

        if alu:

            cur.execute("""
            INSERT INTO asistencias(alumno_id,fecha,turno)
            VALUES(%s,%s,%s)
            """,(alu[0],fecha,turno))

            db.commit()

            ok="Turno confirmado"

        else:

            error="Alumno no registrado"

    db.close()

    return render_template_string(render_pagina(f"""

<h2>Reservar asistencia</h2>

<p style='color:red'>{error}</p>
<p style='color:lightgreen'>{ok}</p>

<form method="post">

<input name="telefono" placeholder="Teléfono alumno">

<input type="date" name="fecha">

<select name="turno">
<option>12:00 a 14:00</option>
<option>14:00 a 16:00</option>
<option>16:00 a 18:00</option>
</select>

<button>Confirmar</button>

</form>

"""))


# ======================
# DASHBOARD
# ======================

@app.route("/dashboard")
def dashboard():

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("SELECT COUNT(*) FROM alumnos")
    total=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM asistencias")
    asist=cur.fetchone()[0]

    cur.execute("""
    SELECT s.id,s.fecha,s.turno,a.nombre,a.apellido
    FROM asistencias s
    JOIN alumnos a ON a.id=s.alumno_id
    ORDER BY s.fecha DESC
    """)

    rows=cur.fetchall()

    db.close()

    html=f"""

<h2>Dashboard</h2>

<p>Alumnos registrados: {total}</p>
<p>Asistencias: {asist}</p>

<a class="boton" href="/alumnos/Inicial">Inicial</a>
<a class="boton" href="/alumnos/Intermedio">Intermedio</a>
<a class="boton" href="/alumnos/Avanzado">Avanzado</a>

<table>

<tr>
<th>Fecha</th>
<th>Turno</th>
<th>Alumno</th>
<th></th>
</tr>

"""

    for sid,f,t,n,a in rows:

        html+=f"""
<tr>
<td>{f}</td>
<td>{t}</td>
<td>{n} {a}</td>
<td><a class="eliminar" href="/eliminar_asistencia/{sid}">Eliminar</a></td>
</tr>
"""

    html+="</table>"

    return render_template_string(render_pagina(html))


# ======================
# ALUMNOS POR NIVEL
# ======================

@app.route("/alumnos/<nivel>")
def alumnos_nivel(nivel):

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("""
    SELECT id,nombre,apellido,telefono
    FROM alumnos
    WHERE nivel=%s
    """,(nivel,))

    alumnos=cur.fetchall()

    html=f"<h2>Alumnos nivel {nivel}</h2><div class='grid'>"

    for aid,n,a,tel in alumnos:

        cur.execute("""
        SELECT fecha,turno
        FROM asistencias
        WHERE alumno_id=%s
        ORDER BY fecha DESC
        """,(aid,))

        asist=cur.fetchall()

        historial="<br>".join(f"{f} {t}" for f,t in asist) or "Sin asistencias"

        html+=f"""
<div class="card">

<h3>{n} {a}</h3>

<p>{tel}</p>

<p>{historial}</p>

<a class="eliminar" href="/eliminar_alumno/{aid}">Eliminar alumno</a>

</div>
"""

    html+="</div>"

    db.close()

    return render_template_string(render_pagina(html))


# ======================
# ELIMINAR ALUMNO
# ======================

@app.route("/eliminar_alumno/<int:aid>")
def eliminar_alumno(aid):

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("DELETE FROM asistencias WHERE alumno_id=%s",(aid,))
    cur.execute("DELETE FROM alumnos WHERE id=%s",(aid,))

    db.commit()
    db.close()

    return redirect("/dashboard")


# ======================
# ELIMINAR ASISTENCIA
# ======================

@app.route("/eliminar_asistencia/<int:sid>")
def eliminar_asistencia(sid):

    if not es_admin():
        return redirect("/login")

    db=get_db()
    cur=db.cursor()

    cur.execute("DELETE FROM asistencias WHERE id=%s",(sid,))

    db.commit()
    db.close()

    return redirect("/dashboard")


# ======================
# INICIAR APP
# ======================

if __name__ == "__main__":

    port=int(os.environ.get("PORT",5000))

    app.run(host="0.0.0.0",port=port)
