from flask import Flask, request, redirect, url_for, render_template_string, session, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave-secreta"

DB_PATH = "database.db"

# =====================
# DB
# =====================
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

# =====================
# LOGIN
# =====================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def login_requerido():
    return "admin" in session

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
        error = "Credenciales incorrectas"

    return render_template_string("""
    <h2>Login Dashboard</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required><br><br>
        <input type="password" name="password" placeholder="Contraseña" required><br><br>
        <button>Ingresar</button>
    </form>
    <p style="color:red;">{{ error }}</p>
    """, error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =====================
# REGISTRO
# =====================
@app.route("/", methods=["GET", "POST"])
def registro():
    error = ""

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]
        turno = request.form["turno"]
        fecha = request.form["fecha"]

        dia_semana = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        if dia_semana not in (1, 2, 3):  # martes, miércoles, jueves
            error = "Solo se puede asistir martes, miércoles o jueves."
        else:
            conn = get_db()
            cur = conn.cursor()

            # alumno único
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

            # turno ocupado
            cur.execute("""
            SELECT 1 FROM asistencias
            WHERE fecha=? AND turno=?
            """, (fecha, turno))
            if cur.fetchone():
                error = "Ese turno ya está ocupado."
            else:
                cur.execute("""
                INSERT INTO asistencias (alumno_id, fecha, turno)
                VALUES (?, ?, ?)
                """, (alumno_id, fecha, turno))
                conn.commit()
                conn.close()
                return redirect("/")

            conn.close()

    return render_template_string("""
    <h1>Inscripción Laboratorio</h1>

    {% if error %}
        <p style="color:red;">{{ error }}</p>
    {% endif %}

    <form method="post" onsubmit="return confirmar()">
        <input name="nombre" placeholder="Nombre" required><br><br>
        <input name="apellido" placeholder="Apellido" required><br><br>
        <input name="telefono" placeholder="Teléfono" required><br><br>

        <select name="nivel" required>
            <option value="">Nivel</option>
            <option>Inicial</option>
            <option>Intermedio</option>
            <option>Avanzado</option>
        </select><br><br>

        <input type="date" name="fecha" id="fecha" required><br><br>

        <select name="turno" id="turno" required>
            <option value="">Turno</option>
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select><br><br>

        <button>Confirmar</button>
    </form>

    <br>
    <a href="/login">Ir al Dashboard</a>

    <script>
    function confirmar() {
        let fecha = document.getElementById("fecha").value;
        let turno = document.getElementById("turno").value;

        return confirm(
            "¿Confirma la asistencia al laboratorio el día " + fecha + " a la hora " + turno + "?\\n\\n" +
            "• Recordar llevar herramientas personales.\\n" +
            "• Respetar el horario elegido.\\n" +
            "• Mantener orden y limpieza.\\n" +
            "• Si no puede asistir, avisar por WhatsApp."
        );
    }
    </script>
    """, error=error)

# =====================
# DASHBOARD
# =====================
@app.route("/dashboard")
def dashboard():
    if not login_requerido():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT s.id, s.fecha, a.nombre, a.apellido, a.telefono, a.nivel, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)
    filas = cur.fetchall()
    conn.close()

    datos = {}
    for f in filas:
        datos.setdefault(f[1], []).append(f)

    return render_template_string("""
    <h2>Dashboard</h2>
    <a href="/exportar">Exportar CSV</a> |
    <a href="/logout">Cerrar sesión</a><br><br>

    {% for fecha, items in datos.items() %}
        <h3>📅 {{ fecha }}</h3>
        <table border="1" cellpadding="6">
            <tr>
                <th>Alumno</th>
                <th>Teléfono</th>
                <th>Nivel</th>
                <th>Turno</th>
                <th>Acción</th>
            </tr>
            {% for i in items %}
            <tr style="background-color:#f8d7da;">
                <td>{{ i[2] }} {{ i[3] }}</td>
                <td>{{ i[4] }}</td>
                <td>{{ i[5] }}</td>
                <td>{{ i[6] }}</td>
                <td>
                    <a href="/eliminar/{{ i[0] }}" onclick="return confirm('¿Eliminar asistencia?')">❌</a>
                </td>
            </tr>
            {% endfor %}
        </table><br>
    {% endfor %}
    """, datos=datos)

# =====================
# ELIMINAR
# =====================
@app.route("/eliminar/<int:id>")
def eliminar(id):
    if not login_requerido():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# =====================
# EXPORTAR CSV
# =====================
@app.route("/exportar")
def exportar():
    if not login_requerido():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    """)
    filas = cur.fetchall()
    conn.close()

    def generar():
        yield "Nombre,Apellido,Telefono,Nivel,Fecha,Turno\n"
        for f in filas:
            yield ",".join(f) + "\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=asistencias.csv"}
    )

if __name__ == "__main__":
    app.run()
