from flask import Flask, request, redirect, render_template_string, session, Response
import sqlite3
from datetime import datetime
from collections import defaultdict

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
    return "admin" in session

# =========================
# ESTILO + HEADER CENTRADO
# =========================
BASE_HTML = """
<style>
body {
    margin: 0;
    padding: 0;
    background: #f2f2f2;
    font-family: Arial, Helvetica, sans-serif;
}

/* HEADER CENTRADO */
.header {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: #2563eb;
    color: white;
    padding: 14px 22px;
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 1000;
}

.header-title {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 8px;
}

.header div {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
}

.header a {
    color: white;
    text-decoration: none;
    font-weight: bold;
    padding: 6px 10px;
    border-radius: 4px;
    transition: background 0.2s;
}

.header a:hover {
    background: rgba(255,255,255,0.2);
}

/* CONTENEDOR PRINCIPAL */
.container {
    max-width: 650px;
    margin: 140px auto 40px auto;
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgba(0,0,0,0.15);
}

h1, h2, h3 {
    text-align: center;
}

/* FORMULARIOS */
input, select, button {
    width: 100%;
    padding: 12px;
    margin-bottom: 12px;
    font-size: 16px;
    box-sizing: border-box;
}

button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

button:hover {
    background: #1e40af;
}

/* TABLAS */
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

th, td {
    padding: 8px;
    border: 1px solid #ccc;
    text-align: center;
}

/* MEDIA QUERY MÓVILES */
@media (max-width: 500px) {
    .container {
        margin: 160px 10px 40px 10px;
        padding: 20px;
        width: auto;
    }
}
</style>
"""

def render_pagina(contenido):
    admin = es_admin()
    header = f"""
    <div class="header">
        <div class="header-title">🔧 Laboratorio Electrónica</div>
        <div>
            {"<a href='/dashboard'>📊 Dashboard</a><a href='/exportar-alumnos'>📥 Exportar</a><a href='/logout'>🚪 Salir</a>"
             if admin else
             "<a href='/'>🧑 Registro</a><a href='/asistencia'>🧪 Asistencia</a>"}
        </div>
    </div>
    """
    return BASE_HTML + header + f"<div class='container'>{contenido}</div>"

# =========================
# REGISTRO ALUMNO (SOLO DATOS PERSONALES)
# =========================
@app.route("/", methods=["GET", "POST"])
def registrar_alumno():
    mensaje = ""
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]

        try:
            conn = get_db()
            cur = conn.cursor()

            # Insertar alumno solo con datos personales
            cur.execute("""
                INSERT INTO alumnos (nombre, apellido, telefono, nivel)
                VALUES (?, ?, ?, ?)
            """, (nombre, apellido, telefono, nivel))
            conn.commit()
            mensaje = "Alumno registrado correctamente."
        except sqlite3.IntegrityError:
            mensaje = "Este alumno ya está registrado."
        finally:
            conn.close()

    contenido = f"""
    <h1>Registro Único de Alumno</h1>
    <p style="color:green;">{mensaje}</p>
    <form method="post">
        <input name="nombre" placeholder="Nombre" required>
        <input name="apellido" placeholder="Apellido" required>
        <input name="telefono" placeholder="Teléfono" required>
        <select name="nivel" required>
            <option value="">Nivel último curso</option>
            <option>Inicial</option>
            <option>Intermedio</option>
            <option>Avanzado</option>
        </select>
        <button>Registrar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

# =========================
# ASISTENCIA
# =========================
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
                # Validar que no tenga asistencia ese día
                cur.execute("""
                SELECT 1 FROM asistencias
                WHERE alumno_id=? AND fecha=?
                """, (alumno[0], fecha))

                if cur.fetchone():
                    error = "Este alumno ya tiene un turno ese día."
                else:
                    # Validar turno único
                    cur.execute("""
                    SELECT 1 FROM asistencias
                    WHERE fecha=? AND turno=?
                    """, (fecha, request.form["turno"]))
                    if cur.fetchone():
                        error = "Ya hay un alumno registrado en este turno."
                    else:
                        cur.execute("""
                        INSERT INTO asistencias (alumno_id, fecha, turno)
                        VALUES (?, ?, ?)
                        """, (alumno[0], fecha, request.form["turno"]))
                        conn.commit()
            conn.close()

    contenido = f"""
    <h1>Asistencia Laboratorio</h1>
    <p style="color:red;">{error}</p>
    <form method="post"
          onsubmit="return confirm('¿Confirma la asistencia al laboratorio en el día y horario elegido?\\n\\n• Recordar llevar las herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).\\n• Respetar el horario elegido ya que luego hay otro alumno en el siguiente turno.\\n• Respetar normas de convivencia del laboratorio (orden y limpieza del puesto de trabajo).\\n• De no poder asistir dar aviso por WhatsApp para liberar el horario.')">
        <input name="telefono" placeholder="Teléfono" required>
        <input type="date" name="fecha" required>
        <select name="turno" required>
            <option value="">Turno</option>
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select>
        <button>Confirmar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

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

    contenido = f"""
    <h2>Login Dashboard</h2>
    <p style="color:red;">{error}</p>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required>
        <input type="password" name="password" placeholder="Contraseña" required>
        <button>Ingresar</button>
    </form>
    """
    return render_template_string(render_pagina(contenido))

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
    SELECT s.id, a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)
    datos = cur.fetchall()
    conn.close()

    asistencias_por_dia = defaultdict(list)
    for d in datos:
        asistencias_por_dia[d[5]].append(d)

    contenido = "<h2>Dashboard</h2>"

    for fecha, lista in asistencias_por_dia.items():
        contenido += f"<h3>📅 {fecha}</h3><table>"
        contenido += """
        <tr>
            <th>Alumno</th>
            <th>Teléfono</th>
            <th>Nivel</th>
            <th>Turno</th>
            <th>Acciones</th>
        </tr>
        """
        for d in lista:
            contenido += f"""
            <tr>
                <td>{d[1]} {d[2]}</td>
                <td>{d[3]}</td>
                <td>{d[4]}</td>
                <td>{d[6]}</td>
                <td>
                    <a href="/eliminar-asistencia/{d[0]}"
                       onclick="return confirm('¿Seguro que desea eliminar esta asistencia?')"
                       style="color:red;font-weight:bold;">
                       🗑️ Eliminar
                    </a>
                </td>
            </tr>
            """
        contenido += "</table>"

    return render_template_string(render_pagina(contenido))

# =========================
# ELIMINAR ASISTENCIA
# =========================
@app.route("/eliminar-asistencia/<int:asistencia_id>")
def eliminar_asistencia(asistencia_id):
    if not es_admin():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=?", (asistencia_id,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# =========================
# EXPORTAR ALUMNOS
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

if __name__ == "__main__":
    app.run()
