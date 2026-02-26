import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave-secreta"

DATABASE_URL = os.environ.get("DATABASE_URL")

CUPOS_POR_TURNO = {
    "12:00 a 14:00": 1,
    "14:00 a 16:00": 1,
    "16:00 a 18:00": 1
}

DIAS_HABILITADOS = [1, 2, 3]  # Martes, Miércoles, Jueves

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
.container { max-width:1000px; margin:40px auto; background:white; padding:30px; border-radius:12px; }
h1,h2,h3 { text-align:center; }
input,select,button { width:100%; padding:14px; font-size:18px; margin-bottom:14px; }
button { background:#2563eb; color:white; border:none; border-radius:8px; }
table { width:100%; border-collapse:collapse; margin-top:15px; }
th,td { border:1px solid #ccc; padding:10px; text-align:center; }
.completo { color:red; font-weight:bold; }
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
# ASISTENCIA (BLOQUEO + CUPOS)
# =========================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    mensaje = ""
    fecha = request.form.get("fecha")

    cupos_restantes = {}
    if fecha:
        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        if dia not in DIAS_HABILITADOS:
            mensaje = "Solo se permite asistencia martes, miércoles o jueves"
        else:
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

    if request.method == "POST" and "telefono" in request.form and not mensaje:
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

    opciones = ""
    for turno, maximo in CUPOS_POR_TURNO.items():
        restantes = cupos_restantes.get(turno, maximo)
        if restantes <= 0:
            opciones += f"<option disabled>{turno} (COMPLETO)</option>"
        else:
            opciones += f"<option>{turno} ({restantes}/{maximo})</option>"

    contenido = f"""
    <h1>🧪 Asistencia al Laboratorio</h1>
    <p style="text-align:center;color:red;">{mensaje}</p>
    <form method="post">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" required value="{fecha or ''}">
        <select name="turno" required>{opciones}</select>
        <button>Confirmar turno</button>
    </form>
    """
    return render_template_string(BASE_HTML + header_publico() + f"<div class='container'>{contenido}</div>")

# =========================
# DASHBOARD (CUPOS VISIBLES)
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT fecha, turno, COUNT(*)
    FROM asistencias
    GROUP BY fecha, turno
    ORDER BY fecha
    """)
    datos = cur.fetchall()
    conn.close()

    resumen = defaultdict(dict)
    for fecha, turno, cantidad in datos:
        resumen[fecha][turno] = cantidad

    contenido = "<h1>📊 Dashboard – Cupos por día</h1>"

    for fecha in resumen:
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Turno</th><th>Cupos</th></tr>"
        for turno, maximo in CUPOS_POR_TURNO.items():
            usados = resumen[fecha].get(turno, 0)
            estado = "COMPLETO" if usados >= maximo else f"{usados} / {maximo}"
            clase = "completo" if usados >= maximo else ""
            contenido += f"<tr><td>{turno}</td><td class='{clase}'>{estado}</td></tr>"
        contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
