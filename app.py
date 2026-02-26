import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "clave-secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

CUPOS_POR_TURNO = {
    "12:00 a 14:00": 1,
    "14:00 a 16:00": 1,
    "16:00 a 18:00": 1
}

# =========================
# DB
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT UNIQUE,
        nivel TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id SERIAL PRIMARY KEY,
        alumno_id INTEGER REFERENCES alumnos(id),
        fecha DATE,
        turno TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# ADMIN
# =========================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def es_admin():
    return "admin" in session

# =========================
# ESTILO
# =========================
BASE_HTML = """
<style>
body { background:#f2f2f2; font-family:Arial; font-size:18px; }
.header { background:#2563eb; color:white; padding:16px; text-align:center; }
.header a { color:white; font-weight:bold; margin:0 15px; text-decoration:none; }
.container { max-width:900px; margin:40px auto; background:white; padding:30px; border-radius:12px; }
h1,h2,h3 { text-align:center; }
input,select,button { width:100%; padding:14px; font-size:18px; margin-bottom:14px; }
button { background:#2563eb; color:white; border:none; border-radius:8px; }
table { width:100%; border-collapse:collapse; margin-top:20px; }
th,td { border:1px solid #ccc; padding:10px; text-align:center; }
.agotado { color:red; font-weight:bold; }
</style>
"""

def header_publico():
    return """
    <div class="header">
        🔧 Laboratorio de Electrónica<br><br>
        <a href="/">🧑 Registro</a>
        <a href="/asistencia">🧪 Asistencia</a>
        <a href="/login">🔐 Admin</a>
    </div>
    """

def header_admin():
    return """
    <div class="header">
        <a href="/dashboard">📊 Dashboard</a>
        <a href="/alumnos">👥 Alumnos</a>
        <a href="/logout">🚪 Salir</a>
    </div>
    """

# =========================
# REGISTRO
# =========================
@app.route("/", methods=["GET", "POST"])
def registro():
    mensaje = ""
    if request.method == "POST":
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (%s,%s,%s,%s)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            conn.commit()
            mensaje = "Alumno registrado correctamente"
            conn.close()
        except:
            mensaje = "Este alumno ya está registrado"

    contenido = f"""
    <h1>🧑 Registro Único de Alumnos</h1>
    <p style="text-align:center;color:green;">{mensaje}</p>
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
        <button>Registrar alumno</button>
    </form>
    <a href="/asistencia"><button style="background:#16a34a;">🧪 Ir a asistencia</button></a>
    """
    return render_template_string(BASE_HTML + header_publico() + f"<div class='container'>{contenido}</div>")

# =========================
# ASISTENCIA (CUPOS VISIBLES)
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    mensaje = ""
    fecha = request.form.get("fecha")

    # calcular cupos por turno
    cupos_restantes = {}
    if fecha:
        conn = get_db()
        cur = conn.cursor()
        for turno, maximo in CUPOS_POR_TURNO.items():
            cur.execute("""
            SELECT COUNT(*) FROM asistencias
            WHERE fecha=%s AND turno=%s
            """, (fecha, turno))
            usados = cur.fetchone()[0]
            cupos_restantes[turno] = maximo - usados
        conn.close()
    else:
        cupos_restantes = CUPOS_POR_TURNO.copy()

    if request.method == "POST" and "telefono" in request.form:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM alumnos WHERE telefono=%s", (request.form["telefono"],))
        alumno = cur.fetchone()

        if not alumno:
            mensaje = "Alumno no registrado"
        else:
            turno = request.form["turno"]

            if cupos_restantes.get(turno, 0) <= 0:
                mensaje = "Cupo completo"
            else:
                cur.execute("""
                SELECT 1 FROM asistencias
                WHERE alumno_id=%s AND fecha=%s
                """, (alumno[0], fecha))

                if cur.fetchone():
                    mensaje = "Ya tiene turno ese día"
                else:
                    cur.execute("""
                    INSERT INTO asistencias (alumno_id, fecha, turno)
                    VALUES (%s,%s,%s)
                    """, (alumno[0], fecha, turno))
                    conn.commit()
                    mensaje = "Turno confirmado correctamente"

        conn.close()

    opciones_turno = ""
    for turno, restantes in cupos_restantes.items():
        if restantes <= 0:
            opciones_turno += f"<option disabled>{turno} (AGOTADO)</option>"
        else:
            opciones_turno += f"<option>{turno} ({restantes} cupos)</option>"

    contenido = f"""
    <h1>🧪 Asistencia al Laboratorio</h1>
    <p style="text-align:center;color:red;">{mensaje}</p>
    <form method="post"
          onsubmit="return confirm('¿Confirma la asistencia al laboratorio en el día y horario elegido?\\n\\n• Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).\\n• Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.\\n• Respetar normas de convivencia del laboratorio (orden y limpieza del puesto de trabajo).\\n• De no poder asistir dar aviso por WhatsApp para liberar el horario.')">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" required value="{fecha or ''}">
        <select name="turno" required>
            {opciones_turno}
        </select>
        <button>Confirmar turno</button>
    </form>
    """
    return render_template_string(BASE_HTML + header_publico() + f"<div class='container'>{contenido}</div>")

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
        error = "Credenciales incorrectas"

    return render_template_string(f"""
    {BASE_HTML}
    <div class="container" style="max-width:500px;">
        <h1>🔐 Login Administrador</h1>
        <p style="color:red;text-align:center;">{error}</p>
        <form method="post">
            <input name="usuario" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button>Ingresar</button>
        </form>
    </div>
    """)

# =========================
# ALUMNOS (ADMIN)
# =========================
@app.route("/alumnos")
def alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, apellido, telefono, nivel FROM alumnos ORDER BY apellido")
    alumnos = cur.fetchall()
    conn.close()

    contenido = "<h1>👥 Alumnos Registrados</h1>"
    contenido += "<a href='/exportar-alumnos'>📥 Descargar Excel</a>"
    contenido += """
    <table>
        <tr>
            <th>Alumno</th>
            <th>Teléfono</th>
            <th>Nivel</th>
            <th>Acción</th>
        </tr>
    """

    for a in alumnos:
        contenido += f"""
        <tr>
            <td>{a[1]} {a[2]}</td>
            <td>{a[3]}</td>
            <td>{a[4]}</td>
            <td>
                <a class="accion"
                   href="/eliminar-alumno/{a[0]}"
                   onclick="return confirm('⚠️ Esto eliminará el alumno y TODAS sus asistencias.\\n\\n¿Confirmar?')">
                   🗑️ Eliminar
                </a>
            </td>
        </tr>
        """

    contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

# =========================
# ELIMINAR ALUMNO (ADMIN)
# =========================
@app.route("/eliminar-alumno/<int:id>")
def eliminar_alumno(id):
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE alumno_id=%s", (id,))
    cur.execute("DELETE FROM alumnos WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect("/alumnos")
# =========================
# ELIMINAR
# =========================
@app.route("/eliminar-asistencia/<int:id>")
def eliminar_asistencia(id):
    if not es_admin():
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/eliminar-alumno/<int:id>")
def eliminar_alumno(id):
    if not es_admin():
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM alumnos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/alumnos")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")
    
# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT s.id, a.nombre, a.apellido, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha
    """)
    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[3]].append(d)

    contenido = "<h1>📊 Dashboard – Asistencias</h1>"
    for fecha, lista in por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Alumno</th><th>Turno</th></tr>"
        for d in lista:
            contenido += f"<tr><td>{d[1]} {d[2]}</td><td>{d[4]}</td></tr>"
        contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

# =========================
# EXPORTAR
# =========================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT nombre, apellido, telefono, nivel FROM alumnos")
    filas = cur.fetchall()
    conn.close()

    def generar():
        yield "Nombre,Apellido,Telefono,Nivel\n"
        for f in filas:
            yield ",".join(f) + "\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=alumnos.csv"}
    )

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
