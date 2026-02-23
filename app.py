from flask import Flask, request, redirect, render_template_string, jsonify, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "laboratorio_secret"
DB = "asistencias.db"

# ===== CREDENCIALES ADMIN =====
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

TURNOS = ["12:00 a 14:00", "14:00 a 16:00", "16:00 a 18:00"]

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT UNIQUE,
        nivel TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alumno_id INTEGER,
        fecha TEXT,
        turno TEXT,
        hora TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- CSS ----------------
CSS = """
body { background:#0b0f1a; color:white; font-family:Arial }
.box { background:#111; padding:20px; margin:30px auto; border-radius:10px }
input, button { padding:12px; margin:6px 0; border-radius:6px; width:100% }
button { cursor:pointer; font-size:16px }
.turno { padding:18px; margin:8px 0; font-size:18px; border:none; border-radius:8px }
.disponible { background:#00cc66; color:black }
.ocupado { background:#cc0000; color:white }
a { color:#00aaff }
table { border-collapse:collapse; width:100% }
th, td { padding:8px; border:1px solid #444 }
"""

# ---------------- LOGIN ADMIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        if request.form["user"]==ADMIN_USER and request.form["pass"]==ADMIN_PASS:
            session["admin"]=True
            return redirect("/dashboard")
        else:
            msg="Credenciales incorrectas"

    return render_template_string("""
    <style>{{CSS}}</style>
    <div class="box" style="max-width:350px">
      <h2>Login administrador</h2>
      <form method="post">
        <input name="user" placeholder="Usuario" required>
        <input type="password" name="pass" placeholder="Contraseña" required>
        <button>Ingresar</button>
      </form>
      <p style="color:red">{{msg}}</p>
    </div>
    """, CSS=CSS, msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- REGISTRO ALUMNO ----------------
@app.route("/registro_alumno", methods=["GET","POST"])
def registro_alumno():
    msg=""
    if request.method=="POST":
        try:
            conn=get_db()
            cur=conn.cursor()
            cur.execute("""
                INSERT INTO alumnos (nombre,apellido,telefono,nivel)
                VALUES (?,?,?,?)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            conn.commit()
            msg="Alumno registrado correctamente"
        except sqlite3.IntegrityError:
            msg="El alumno ya existe"
        finally:
            conn.close()

    return render_template_string("""
    <style>{{CSS}}</style>
    <div class="box" style="max-width:400px">
      <h2>Registro único de alumno</h2>
      <form method="post">
        <input name="nombre" placeholder="Nombre" required>
        <input name="apellido" placeholder="Apellido" required>
        <input name="telefono" placeholder="Teléfono" required>
        <input name="nivel" placeholder="Nivel (Inicial / Intermedio / Avanzado)" required>
        <button>Registrar</button>
      </form>
      <p>{{msg}}</p>
      <a href="/">Ir a inscripción</a>
    </div>
    """, CSS=CSS, msg=msg)

# ---------------- API TURNOS ----------------
@app.route("/turnos/<fecha>")
def turnos_fecha(fecha):
    conn=get_db()
    cur=conn.cursor()
    cur.execute("SELECT turno FROM asistencias WHERE fecha=?", (fecha,))
    ocupados=[r["turno"] for r in cur.fetchall()]
    conn.close()
    return jsonify(ocupados)

# ---------------- INSCRIPCIÓN ----------------
@app.route("/", methods=["GET","POST"])
def inscripcion():
    msg=""
    if request.method=="POST":
        telefono=request.form["telefono"]
        fecha=request.form["fecha"]
        turno=request.form["turno"]

        dia=datetime.strptime(fecha,"%Y-%m-%d").weekday()
        if dia not in [1,2,3]:
            msg="Solo martes, miércoles y jueves"
        else:
            conn=get_db()
            cur=conn.cursor()
            cur.execute("SELECT * FROM alumnos WHERE telefono=?", (telefono,))
            alumno=cur.fetchone()

            if not alumno:
                msg="Alumno no registrado"
            else:
                cur.execute("""
                    SELECT 1 FROM asistencias
                    WHERE alumno_id=? AND fecha=?
                """,(alumno["id"],fecha))
                if cur.fetchone():
                    msg="El alumno ya tiene turno ese día"
                else:
                    cur.execute("""
                        INSERT INTO asistencias (alumno_id,fecha,turno,hora)
                        VALUES (?,?,?,?)
                    """,(alumno["id"],fecha,turno,datetime.now().strftime("%H:%M")))
                    conn.commit()
                    msg="Inscripción realizada"
            conn.close()

    return render_template_string("""
    <style>{{CSS}}</style>
    <div class="box" style="max-width:450px">
      <h2>Inscripción laboratorio</h2>
      <form method="post">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" id="fecha" name="fecha" required>
        <div id="turnos"></div>
        <input type="hidden" name="turno" id="turno" required>
        <button>Confirmar inscripción</button>
      </form>
      <p>{{msg}}</p>
      <a href="/registro_alumno">Registrar alumno</a> |
      <a href="/login">Dashboard</a>
    </div>

<script>
const turnos={{turnos|tojson}};
const cont=document.getElementById("turnos");
const fecha=document.getElementById("fecha");
const turnoInput=document.getElementById("turno");

fecha.addEventListener("change",async()=>{
 cont.innerHTML="";
 turnoInput.value="";
 const d=new Date(fecha.value+"T00:00").getDay();
 if(![2,3,4].includes(d)){
   cont.innerHTML="<p style='color:#aaa'>Solo martes, miércoles y jueves</p>";
   return;
 }
 const res=await fetch("/turnos/"+fecha.value);
 const ocupados=await res.json();
 turnos.forEach(t=>{
   const b=document.createElement("button");
   b.type="button";
   b.className="turno "+(ocupados.includes(t)?"ocupado":"disponible");
   b.innerText=t;
   if(!ocupados.includes(t)){
     b.onclick=()=>{turnoInput.value=t};
   }
   cont.appendChild(b);
 });
});
</script>
""", CSS=CSS, msg=msg, turnos=TURNOS)

# ---------------- DASHBOARD (PROTEGIDO) ----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    conn=get_db()
    cur=conn.cursor()

    # Asistencias
    cur.execute("""
        SELECT a.id, a.fecha, a.turno,
               al.nombre, al.apellido, al.telefono, al.nivel
        FROM asistencias a
        JOIN alumnos al ON al.id=a.alumno_id
        ORDER BY a.fecha, a.turno
    """)
    asistencias=cur.fetchall()

    # Alumnos únicos + contador
    cur.execute("""
        SELECT al.nombre, al.apellido, al.telefono, al.nivel,
        COUNT(a.id) as total
        FROM alumnos al
        LEFT JOIN asistencias a ON a.alumno_id=al.id
        GROUP BY al.id
        ORDER BY al.apellido
    """)
    alumnos=cur.fetchall()
    conn.close()

    return render_template_string("""
    <style>{{CSS}}</style>
    <div class="box" style="max-width:1000px">
      <h2>Dashboard</h2>
      <a href="/logout">Cerrar sesión</a>

      <h3>📅 Asistencias</h3>
      <table>
        <tr><th>Fecha</th><th>Turno</th><th>Alumno</th><th>Nivel</th><th>Teléfono</th></tr>
        {% for a in asistencias %}
        <tr>
          <td>{{a.fecha}}</td>
          <td>{{a.turno}}</td>
          <td>{{a.nombre}} {{a.apellido}}</td>
          <td>{{a.nivel}}</td>
          <td><a href="https://wa.me/54{{a.telefono}}" target="_blank">{{a.telefono}}</a></td>
        </tr>
        {% endfor %}
      </table>

      <h3 style="margin-top:30px">📚 Base de datos de alumnos</h3>
      <table>
        <tr><th>Alumno</th><th>Nivel</th><th>Teléfono</th><th>Asistencias</th></tr>
        {% for al in alumnos %}
        <tr>
          <td>{{al.nombre}} {{al.apellido}}</td>
          <td>{{al.nivel}}</td>
          <td><a href="https://wa.me/54{{al.telefono}}" target="_blank">{{al.telefono}}</a></td>
          <td>{{al.total}}</td>
        </tr>
        {% endfor %}
      </table>
    </div>
    """, CSS=CSS, asistencias=asistencias, alumnos=alumnos)

# ---------------- MAIN ----------------
if __name__=="__main__":
    app.run(debug=True)
