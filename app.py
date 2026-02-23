from flask import Flask, request, redirect, render_template_string, session, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave-secreta"

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

USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "1234"

def login_requerido():
    return "admin" in session

ESTILO = """
<style>
body {
    margin: 0;
    padding: 0;
    background: #f2f2f2;
    font-family: Arial, Helvetica, sans-serif;
}
.container {
    max-width: 600px;
    margin: 40px auto;
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgba(0,0,0,0.15);
}
h1, h2 {
    text-align: center;
}
input, select, button {
    width: 100%;
    padding: 12px;
    margin-bottom: 12px;
    font-size: 16px;
}
button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
}
a {
    display: block;
    text-align: center;
    margin-top: 10px;
}
</style>
"""

@app.route("/", methods=["GET", "POST"])
def registrar_alumno():
    mensaje = ""
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        try:
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
        except sqlite3.IntegrityError:
            mensaje = "Este alumno ya está registrado."
        conn.close()

    return render_template_string(f"""
    {ESTILO}
    <div class="container">
        <h1>Registro de Alumno</h1>
        <p style="color:green;">{mensaje}</p>
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
            <button>Registrar</button>
        </form>
        <a href="/asistencia">Registrar asistencia</a>
        <a href="/login">Dashboard</a>
    </div>
    """)

@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    error = ""
    if request.method == "POST":
        fecha = request.form["fecha"]
        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        if dia not in (1,2,3):
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
    {ESTILO}
    <div class="container">
        <h1>Asistencia Laboratorio</h1>
        <p style="color:red;">{error}</p>
        <form method="post">
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
        <a href="/">Volver</a>
    </div>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
        error = "Credenciales incorrectas"

    return render_template_string(f"""
    {ESTILO}
    <div class="container">
        <h2>Login Dashboard</h2>
        <p style="color:red;">{error}</p>
        <form method="post">
            <input name="usuario" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button>Ingresar</button>
        </form>
    </div>
    """)

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

    filas = ""
    for d in datos:
        filas += f"<tr><td>{d[0]} {d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td></tr>"

    return render_template_string(f"""
    {ESTILO}
    <div class="container">
        <h2>Dashboard</h2>
        <table border="1" width="100%" cellpadding="6">
            <tr><th>Alumno</th><th>Teléfono</th><th>Nivel</th><th>Fecha</th><th>Turno</th></tr>
            {filas}
        </table>
        <a href="/exportar-alumnos">Exportar alumnos</a>
        <a href="/logout">Cerrar sesión</a>
    </div>
    """)

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

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run()
