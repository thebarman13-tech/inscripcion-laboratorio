from flask import Flask, request, redirect, render_template_string, session
import sqlite3
from datetime import datetime
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = "clave-secreta"

DB_PATH = "database.db"

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
# ESTILOS (ARREGLADOS)
# =========================
BASE_HTML = """
<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #f2f2f2;
    font-family: Arial, Helvetica, sans-serif;
}

.header {
    position: fixed;
    top: 0;
    width: 100%;
    background: #1e3a8a;
    color: white;
    padding: 15px;
    text-align: center;
    z-index: 1000;
}

.header a {
    color: white;
    margin: 0 15px;
    font-size: 18px;
    font-weight: bold;
    text-decoration: none;
}

.container {
    max-width: 900px;
    margin: 120px auto 40px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 0 15px rgba(0,0,0,0.2);
}

h1, h2, h3 {
    text-align: center;
}

input, select, button {
    width: 100%;
    padding: 16px;
    font-size: 18px;
    margin-bottom: 16px;
    border-radius: 8px;
}

button {
    background: #2563eb;
    color: white;
    border: none;
    cursor: pointer;
}

button:hover {
    background: #1e40af;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

th, td {
    padding: 12px;
    border: 1px solid #ccc;
    text-align: center;
}
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
        <a href="/alumnos">🧑 Alumnos</a>
        <a href="/logout">🚪 Salir</a>
    </div>

# =========================
# RUTAS PÚBLICAS
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
    if request.method == "POST":
        fecha = request.form["fecha"]
        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()

        if dia not in (1, 2, 3):
            error = "Solo martes, miércoles o jueves."
        else:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM alumnos WHERE telefono=?", (request.form["telefono"],))
            alumno = cur.fetchone()

            if not alumno:
                error = "Alumno no registrado."
            else:
                cur.execute("""
                SELECT 1 FROM asistencias
                WHERE alumno_id=? AND fecha=?
                """, (alumno[0], fecha))

                if cur.fetchone():
                    error = "Este alumno ya tiene turno ese día."
                else:
                    cur.execute("""
                    INSERT INTO asistencias (alumno_id, fecha, turno)
                    VALUES (?, ?, ?)
                    """, (alumno[0], fecha, request.form["turno"]))
                    conn.commit()
            conn.close()

    return render_template_string(f"""
    {BASE_HTML}{header_publico()}
    <div class="container">
        <h1>Asistencia al Laboratorio</h1>
        <p style="color:red;text-align:center;">{error}</p>
        <form method="post"
        onsubmit="return confirm('¿Confirma la asistencia?\\n\\n• Llevar herramientas\\n• Respetar horario\\n• Mantener orden y limpieza\\n• Avisar si no puede asistir')">
            <input name="telefono" placeholder="Teléfono" required>
            <input type="date" name="fecha" required>
            <select name="turno" required>
                <option value="">Turno</option>
                <option>12:00 a 14:00</option>
                <option>14:00 a 16:00</option>
                <option>16:00 a 18:00</option>
            </select>
            <button>Confirmar Asistencia</button>
        </form>
    </div>
    """)

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
    {BASE_HTML}{header_publico()}
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
# DASHBOARD ASISTENCIAS
# =========================
@app.route("/dashboard")
def dashboard():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT s.id, a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha ASC
    """)
    datos = cur.fetchall()
    conn.close()

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[5]].append(d)

    contenido = "<h1>Asistencias al Laboratorio</h1>"

    for fecha, lista in por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += "<tr><th>Alumno</th><th>Teléfono</th><th>Nivel</th><th>Turno</th><th>Acción</th></tr>"
        for d in lista:
            contenido += f"""
            <tr>
                <td>{d[1]} {d[2]}</td>
                <td>{d[3]}</td>
                <td>{d[4]}</td>
                <td>{d[6]}</td>
                <td><a href="/eliminar-asistencia/{d[0]}" style="color:red;">🗑️</a></td>
            </tr>
            """
        contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

# =========================
# ALUMNOS REGISTRADOS
# =========================
@app.route("/alumnos")
def alumnos():
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, apellido, telefono, nivel FROM alumnos")
    alumnos = cur.fetchall()
    conn.close()

    contenido = "<h1>Alumnos Registrados</h1><table>"
    contenido += "<tr><th>Nombre</th><th>Teléfono</th><th>Nivel</th><th>Acción</th></tr>"
    for a in alumnos:
        contenido += f"""
        <tr>
            <td>{a[1]} {a[2]}</td>
            <td>{a[3]}</td>
            <td>{a[4]}</td>
            <td><a href="/eliminar-alumno/{a[0]}" style="color:red;">🗑️</a></td>
        </tr>
        """
    contenido += "</table>"

    return render_template_string(BASE_HTML + header_admin() + f"<div class='container'>{contenido}</div>")

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
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
