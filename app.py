from flask import Flask, request, redirect, render_template_string, session, Response
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
# REGISTRO ÚNICO ALUMNO
# =====================
@app.route("/", methods=["GET", "POST"])
def registrar_alumno():
    mensaje = ""

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
            INSERT INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (?, ?, ?, ?)
            """, (nombre, apellido, telefono, nivel))
            conn.commit()
            mensaje = "Alumno registrado correctamente."
        except sqlite3.IntegrityError:
            mensaje = "Este alumno ya está registrado."

        conn.close()

    return render_template_string("""
    <h1>Registro Único de Alumno</h1>

    <p style="color:green;">{{ mensaje }}</p>

    <form method="post">
        <input name="nombre" placeholder="Nombre" required><br><br>
        <input name="apellido" placeholder="Apellido" required><br><br>
        <input name="telefono" placeholder="Teléfono" required><br><br>

        <select name="nivel" required>
            <option value="">Nivel último curso</option>
            <option>Inicial</option>
            <option>Intermedio</option>
            <option>Avanzado</option>
        </select><br><br>

        <button>Registrar Alumno</button>
    </form>

    <br>
    <a href="/asistencia">Registrar asistencia laboratorio</a><br>
    <a href="/login">Dashboard</a>
    """, mensaje=mensaje)

# =====================
# REGISTRO ASISTENCIA
# =====================
@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""

    if request.method == "POST":
        telefono = request.form["telefono"]
        fecha = request.form["fecha"]
        turno = request.form["turno"]

        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        if dia not in (1, 2, 3):
            error = "Solo martes, miércoles o jueves."
        else:
            conn = get_db()
            cur = conn.cursor()

            cur.execute("SELECT id FROM alumnos WHERE telefono=?", (telefono,))
            alumno = cur.fetchone()

            if not alumno:
                error = "El alumno no está registrado."
            else:
                cur.execute("""
                SELECT 1 FROM asistencias WHERE fecha=? AND turno=?
                """, (fecha, turno))

                if cur.fetchone():
                    error = "Turno ocupado."
                else:
                    cur.execute("""
                    INSERT INTO asistencias (alumno_id, fecha, turno)
                    VALUES (?, ?, ?)
                    """, (alumno[0], fecha, turno))
                    conn.commit()
                    conn.close()
                    return redirect("/asistencia")

            conn.close()

    return render_template_string("""
    <h1>Asistencia Laboratorio</h1>

    {% if error %}
        <p style="color:red;">{{ error }}</p>
    {% endif %}

    <form method="post" onsubmit="return confirmar()">
        <input name="telefono" placeholder="Teléfono del alumno" required><br><br>
        <input type="date" name="fecha" id="fecha" required><br><br>

        <select name="turno" id="turno" required>
            <option value="">Turno</option>
            <option>12:00 a 14:00</option>
            <option>14:00 a 16:00</option>
            <option>16:00 a 18:00</option>
        </select><br><br>

        <button>Confirmar Asistencia</button>
    </form>

    <script>
    function confirmar() {
        return confirm(
            "¿Confirma la asistencia al laboratorio?\n\n" +
            "• Traer herramientas personales\n" +
            "• Respetar el horario\n" +
            "• Mantener orden y limpieza\n" +
            "• Avisar si no puede asistir"
        );
    }
    </script>

    <br>
    <a href="/">Volver</a>
    """)

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
    SELECT a.nombre, a.apellido, a.telefono, a.nivel, s.fecha, s.turno
    FROM asistencias s
    JOIN alumnos a ON a.id = s.alumno_id
    ORDER BY s.fecha DESC
    """)
    datos = cur.fetchall()
    conn.close()

    return render_template_string("""
    <h2>Dashboard</h2>
    <a href="/exportar-alumnos">Exportar alumnos</a> |
    <a href="/logout">Salir</a><br><br>

    <table border="1" cellpadding="6">
        <tr>
            <th>Alumno</th>
            <th>Teléfono</th>
            <th>Nivel</th>
            <th>Fecha</th>
            <th>Turno</th>
        </tr>
        {% for d in datos %}
        <tr>
            <td>{{ d[0] }} {{ d[1] }}</td>
            <td>{{ d[2] }}</td>
            <td>{{ d[3] }}</td>
            <td>{{ d[4] }}</td>
            <td>{{ d[5] }}</td>
        </tr>
        {% endfor %}
    </table>
    """ , datos=datos)

# =====================
# EXPORTAR ALUMNOS
# =====================
@app.route("/exportar-alumnos")
def exportar_alumnos():
    if not login_requerido():
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

if __name__ == "__main__":
    app.run()
