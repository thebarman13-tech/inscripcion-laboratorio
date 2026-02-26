from flask import Flask, request, redirect, render_template_string, session
import sqlite3
from datetime import datetime
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = "clave-secreta"

# =========================
# CONFIGURACIÓN
# =========================
DB_PATH = "/data/database.db"

CUPOS_POR_TURNO = {
    "12:00 a 14:00": 1,
    "14:00 a 16:00": 1,
    "16:00 a 18:00": 1
}

# =========================
# BASE DE DATOS
# =========================
def get_db():
    return sqlite3.connect(DB_PATH)

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
        turno TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# LOGIN
# =========================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def es_admin():
    return session.get("admin")

# =========================
# ESTILOS (igual que ahora)
# =========================
BASE_HTML = """
<style>
* { box-sizing: border-box; }
body { margin:0; background:#f2f2f2; font-family:Arial; }
.header {
    position:fixed; top:0; width:100%;
    background:#1e3a8a; color:white;
    padding:15px; text-align:center; z-index:1000;
}
.header a { color:white; margin:0 15px; font-size:18px; font-weight:bold; text-decoration:none; }
.container {
    max-width:900px; margin:120px auto 40px;
    background:white; padding:30px;
    border-radius:12px; box-shadow:0 0 15px rgba(0,0,0,.2);
}
h1,h2,h3 { text-align:center; }
input,select,button {
    width:100%; padding:16px; font-size:18px;
    margin-bottom:16px; border-radius:8px;
}
button { background:#2563eb; color:white; border:none; cursor:pointer; }
button:hover { background:#1e40af; }
table { width:100%; border-collapse:collapse; margin-top:15px; }
th,td { padding:12px; border:1px solid #ccc; text-align:center; }
.completo { color:red; font-weight:bold; }
</style>
"""

def header_publico():
    return """
    <div class="header">
        🔧 Laboratorio de Electrónica<br><br>
        <a href="/registro">🧑 Registro</a>
        <a href="/asistencia">🧪 Asistencia</a>
        <a href="/login">🔐 Admin</a>
    </div>
    """

def header_admin():
    return """
    <div class="header">
        📊 Dashboard Administrador<br><br>
        <a href="/dashboard">🧪 Asistencias</a>
        <a href="/logout">🚪 Salir</a>
    </div>
    """

# =========================
# RUTAS
# =========================
@app.route("/")
def index():
    return redirect("/registro")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    mensaje = ""
    if request.method == "POST":
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (?, ?, ?, ?)
            """, (
                request.form["nombre"],
                request.form["apellido"],
                request.form["telefono"],
                request.form["nivel"]
            ))
            conn.commit()
            mensaje = "Alumno registrado correctamente."
        except:
            mensaje = "El alumno ya está registrado."
        finally:
            conn.close()

    return render_template_string(f"""
    {BASE_HTML}{header_publico()}
    <div class="container">
        <h1>Registro Único de Alumno</h1>
        <p style="color:green;text-align:center;">{mensaje}</p>
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
    </div>
    """)

@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""
    fecha = request.form.get("fecha")

    conn = get_db()
    cur = conn.cursor()
    cupos = defaultdict(int)

    if fecha:
        cur.execute("""
        SELECT turno, COUNT(*) FROM asistencias
        WHERE fecha=? GROUP BY turno
        """, (fecha,))
        for t, c in cur.fetchall():
            cupos[t] = c

    if request.method == "POST":
        turno = request.form["turno"]
        if cupos[turno] >= CUPOS_POR_TURNO[turno]:
            error = "Ese turno está completo."
        else:
            cur.execute("SELECT id FROM alumnos WHERE telefono=?", (request.form["telefono"],))
            alumno = cur.fetchone()
            if not alumno:
                error = "Alumno no registrado."
            else:
                cur.execute("""
                INSERT INTO asistencias (alumno_id, fecha, turno)
                VALUES (?, ?, ?)
                """, (alumno[0], fecha, turno))
                conn.commit()
    conn.close()

    opciones = ""
    for turno, maximo in CUPOS_POR_TURNO.items():
        usados = cupos[turno]
        if usados >= maximo:
            opciones += f"<option disabled>{turno} (COMPLETO)</option>"
        else:
            opciones += f"<option>{turno} ({maximo-usados} libres)</option>"

    return render_template_string(f"""
    {BASE_HTML}{header_publico()}
    <div class="container">
        <h1>Asistencia al Laboratorio</h1>
        <p style="color:red;text-align:center;">{error}</p>
        <form method="post">
            <input name="telefono" placeholder="Teléfono" required>
            <input type="date" name="fecha" required>
            <select name="turno" required>
                <option value="">Turno</option>
                {opciones}
            </select>
            <button>Confirmar Asistencia</button>
        </form>
    </div>
    """)

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
    SELECT a.nombre, a.apellido, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha ASC
    """)
    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[2]].append(d)

    contenido = "<h1>Asistencias por Día</h1>"
    for fecha, lista in por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Alumno</th><th>Turno</th></tr>"
        for l in lista:
            contenido += f"<tr><td>{l[0]} {l[1]}</td><td>{l[3]}</td></tr>"
        contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

# =========================
# LOGIN / LOGOUT
# =========================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
