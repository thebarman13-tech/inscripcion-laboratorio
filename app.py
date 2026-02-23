from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
from datetime import date

app = Flask(__name__)

DB_PATH = "database.db"

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
        telefono TEXT,
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

STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing: border-box; font-family: Arial, Helvetica, sans-serif; }

body {
    margin: 0;
    background: #0b0f1a;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

.app-container {
    width: 100%;
    max-width: 420px;
    background: #111827;
    color: white;
    padding: 24px;
    border-radius: 18px;
}

h1, h2 {
    text-align: center;
    margin-bottom: 20px;
}

input, select, button {
    width: 100%;
    padding: 14px;
    margin-bottom: 14px;
    font-size: 16px;
    border-radius: 10px;
    border: none;
}

input, select {
    background: #1f2933;
    color: white;
}

button {
    background: #2563eb;
    color: white;
    font-weight: bold;
}

button:active {
    transform: scale(0.97);
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

th, td {
    padding: 8px;
    border-bottom: 1px solid #374151;
    text-align: center;
}

th {
    background: #1f2933;
}

@media (max-width: 480px) {
    .app-container {
        border-radius: 0;
        min-height: 100vh;
    }
}
</style>
"""

@app.route("/", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]
        turno = request.form["turno"]
        hoy = date.today().isoformat()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        SELECT id FROM alumnos
        WHERE nombre=? AND apellido=? AND telefono=?
        """, (nombre, apellido, telefono))
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
        SELECT 1 FROM asistencias
        WHERE alumno_id=? AND fecha=?
        """, (alumno_id, hoy))

        if not cur.fetchone():
            cur.execute("""
            INSERT INTO asistencias (alumno_id, fecha, turno)
            VALUES (?, ?, ?)
            """, (alumno_id, hoy, turno))

        conn.commit()
        conn.close()
        return redirect(url_for("registro"))

    return render_template_string("""
    {{ style|safe }}
    <div class="app-container">
        <h1>Inscripción Laboratorio</h1>
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

            <select name="turno" required>
                <option value="">Turno</option>
                <option>12:00 a 14:00</option>
                <option>14:00 a 16:00</option>
                <option>16:00 a 18:00</option>
            </select>

            <button type="submit">Confirmar Turno</button>
        </form>

        <a href="/dashboard" style="color:#93c5fd; text-align:center; display:block; margin-top:10px;">
            Ir al Dashboard
        </a>
    </div>
    """, style=STYLE)

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT a.nombre, a.apellido, a.telefono, a.nivel,
           s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)

    datos = cur.fetchall()
    conn.close()

    return render_template_string("""
    {{ style|safe }}
    <div class="app-container">
        <h2>Dashboard</h2>
        <table>
            <tr>
                <th>Alumno</th>
                <th>Nivel</th>
                <th>Fecha</th>
                <th>Turno</th>
            </tr>
            {% for d in datos %}
            <tr>
                <td>{{ d[0] }} {{ d[1] }}</td>
                <td>{{ d[3] }}</td>
                <td>{{ d[4] }}</td>
                <td>{{ d[5] }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """, datos=datos, style=STYLE)

if __name__ == "__main__":
    app.run()
