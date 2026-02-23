from flask import Flask, render_template_string, request, redirect, session, send_file
import sqlite3
import csv
import io

app = Flask(__name__)
app.secret_key = "clave-secreta-lab"

DB_NAME = "database.db"

# -------------------------
# DB
# -------------------------
def get_db():
    return sqlite3.connect(DB_NAME)

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

# -------------------------
# ESTILO APP (CSS)
# -------------------------
STYLE = """
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #0b1220;
    color: #fff;
}

.app {
    max-width: 420px;
    margin: auto;
    padding: 20px;
}

.card {
    background: #ffffff;
    color: #000;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}

h2 {
    text-align: center;
    margin-bottom: 20px;
}

input, select, button {
    width: 100%;
    padding: 14px;
    margin-bottom: 12px;
    font-size: 17px;
    border-radius: 8px;
    border: 1px solid #ccc;
}

button {
    background: #2563eb;
    color: white;
    border: none;
    font-weight: bold;
}

.radio-group label {
    display: block;
    margin-bottom: 6px;
}

.success {
    color: #16a34a;
    text-align: center;
}

.error {
    color: #dc2626;
    text-align: center;
}

.table-wrapper {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

th, td {
    padding: 8px;
    text-align: center;
}

th {
    background: #111827;
    color: white;
}

a {
    color: #2563eb;
    text-decoration: none;
}
</style>
"""

# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "admin123":
            session["admin"] = True
            return redirect("/dashboard")

    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {STYLE}
    </head>
    <body>
        <div class="app">
            <div class="card">
                <h2>Login Admin</h2>
                <form method="post">
                    <input name="user" placeholder="Usuario">
                    <input name="pass" type="password" placeholder="Contraseña">
                    <button>Ingresar</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -------------------------
# REGISTRO
# -------------------------
@app.route("/", methods=["GET", "POST"])
def registro():
    mensaje = ""
    error = ""

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]
        fecha = request.form["fecha"]
        turno = request.form["turno"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM alumnos WHERE telefono = ?", (telefono,))
        alumno = cur.fetchone()

        if alumno:
            alumno_id = alumno[0]
        else:
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (?, ?, ?, ?)
            """, (nombre, apellido, telefono, nivel))
            alumno_id = cur.lastrowid

        cur.execute("""
        SELECT * FROM asistencias
        WHERE alumno_id = ? AND fecha = ?
        """, (alumno_id, fecha))

        if cur.fetchone():
            error = "Ya estás registrado ese día"
        else:
            cur.execute("""
            INSERT INTO asistencias (alumno_id, fecha, turno)
            VALUES (?, ?, ?)
            """, (alumno_id, fecha, turno))
            conn.commit()
            mensaje = "Asistencia registrada"

        conn.close()

    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {STYLE}
    </head>
    <body>
        <div class="app">
            <div class="card">
                <h2>Inscripción Laboratorio</h2>
                <form method="post">
                    <input name="nombre" placeholder="Nombre" required>
                    <input name="apellido" placeholder="Apellido" required>
                    <input name="telefono" placeholder="Teléfono" required>

                    <div class="radio-group">
                        <label><input type="radio" name="nivel" value="Inicial" required> Inicial</label>
                        <label><input type="radio" name="nivel" value="Intermedio"> Intermedio</label>
                        <label><input type="radio" name="nivel" value="Avanzado"> Avanzado</label>
                    </div>

                    <input type="date" name="fecha" required>

                    <select name="turno" required>
                        <option value="">Turno</option>
                        <option>12:00 a 14:00</option>
                        <option>14:00 a 16:00</option>
                        <option>16:00 a 18:00</option>
                    </select>

                    <button>Registrar</button>
                </form>

                <p class="success">{mensaje}</p>
                <p class="error">{error}</p>
            </div>
        </div>
    </body>
    </html>
    """)

# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT asistencias.id, fecha, turno, nombre, apellido, telefono, nivel
    FROM asistencias
    JOIN alumnos ON alumnos.id = asistencias.alumno_id
    ORDER BY fecha
    """)

    data = cur.fetchall()
    conn.close()

    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {STYLE}
    </head>
    <body>
        <div class="app">
            <div class="card">
                <h2>Dashboard</h2>
                <a href="/logout">Cerrar sesión</a>
                <div class="table-wrapper">
                    <table>
                        <tr>
                            <th>Fecha</th>
                            <th>Turno</th>
                            <th>Alumno</th>
                            <th>Nivel</th>
                            <th>Teléfono</th>
                            <th></th>
                        </tr>
                        {% for a in data %}
                        <tr>
                            <td>{{a[1]}}</td>
                            <td>{{a[2]}}</td>
                            <td>{{a[3]}} {{a[4]}}</td>
                            <td>{{a[6]}}</td>
                            <td>
                                <a href="https://wa.me/54{{a[5]}}" target="_blank">
                                    {{a[5]}}
                                </a>
                            </td>
                            <td>
                                <a href="/eliminar_asistencia/{{a[0]}}">🗑</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """, data=data)

# -------------------------
# ELIMINAR
# -------------------------
@app.route("/eliminar_asistencia/<int:id>")
def eliminar_asistencia(id):
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    app.run()
