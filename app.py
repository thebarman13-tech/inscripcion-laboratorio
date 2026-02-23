from flask import Flask, request, redirect, session, send_file, render_template_string
import sqlite3
from datetime import date
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "clave-secreta-segura"

DB = "database.db"

# -------------------- ESTILO --------------------

STYLE = """
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #0b1220;
    color: white;
}
.app {
    max-width: 420px;
    margin: auto;
    padding: 20px;
}
.card {
    background: white;
    color: black;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}
h2 { text-align: center; }
input, select, button {
    width: 100%;
    padding: 14px;
    font-size: 16px;
    margin-bottom: 12px;
    border-radius: 10px;
    border: 1px solid #ccc;
}
button {
    background: #2563eb;
    color: white;
    border: none;
    font-weight: bold;
}
.levels label {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
}
.levels input {
    margin-right: 10px;
}
.level-Inicial { background:#dbeafe; }
.level-Intermedio { background:#fde68a; }
.level-Avanzado { background:#fecaca; }
table {
    width: 100%;
    font-size: 14px;
    border-collapse: collapse;
}
th, td {
    padding: 6px;
    border-bottom: 1px solid #ddd;
}
a { text-decoration: none; }
</style>
"""

# -------------------- DB --------------------

def get_db():
    return sqlite3.connect(DB)

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
        turno TEXT,
        FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
        UNIQUE(alumno_id, fecha)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------- HOME --------------------

@app.route("/")
def home():
    return render_template_string("""
    {{ style|safe }}
    <div class="app">
        <div class="card">
            <h2>Inscripciones</h2>
            <a href="/alumno"><button>📚 Inscripción Alumno</button></a>
            <a href="/laboratorio"><button>🧪 Inscripción Laboratorio</button></a>
            <a href="/login"><button>🔐 Dashboard</button></a>
        </div>
    </div>
    """, style=STYLE)

# -------------------- ALUMNO --------------------

@app.route("/alumno", methods=["GET","POST"])
def alumno():
    if request.method == "POST":
        nombre = request.form["nombre"].title()
        apellido = request.form["apellido"].title()
        telefono = request.form["telefono"]
        nivel = request.form["nivel"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO alumnos (nombre, apellido, telefono, nivel)
            VALUES (?,?,?,?)
        """,(nombre,apellido,telefono,nivel))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template_string("""
    {{ style|safe }}
    <div class="app">
        <div class="card">
            <h2>Inscripción única alumno</h2>
            <form method="post">
                <input name="nombre" placeholder="Nombre" required>
                <input name="apellido" placeholder="Apellido" required>
                <input name="telefono" placeholder="Teléfono" required>

                <div class="levels">
                    <label><input type="radio" name="nivel" value="Inicial" required> Inicial</label>
                    <label><input type="radio" name="nivel" value="Intermedio"> Intermedio</label>
                    <label><input type="radio" name="nivel" value="Avanzado"> Avanzado</label>
                </div>

                <button>Registrar alumno</button>
            </form>
        </div>
    </div>
    """, style=STYLE)

# -------------------- LABORATORIO --------------------

@app.route("/laboratorio", methods=["GET","POST"])
def laboratorio():
    mensaje = ""

    if request.method == "POST":
        telefono = request.form["telefono"]
        turno = request.form["turno"]
        hoy = str(date.today())

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM alumnos WHERE telefono=?", (telefono,))
        alumno = cur.fetchone()

        if not alumno:
            mensaje = "Alumno no registrado"
        else:
            try:
                cur.execute("""
                    INSERT INTO asistencias (alumno_id, fecha, turno)
                    VALUES (?,?,?)
                """,(alumno[0],hoy,turno))
                conn.commit()
                mensaje = "Asistencia registrada"
            except:
                mensaje = "Ya registrado hoy"

        conn.close()

    return render_template_string("""
    {{ style|safe }}
    <div class="app">
        <div class="card">
            <h2>Inscripción Laboratorio</h2>
            <form method="post">
                <input name="telefono" placeholder="Teléfono" required>
                <select name="turno" required>
                    <option value="">Turno</option>
                    <option>10 a 12</option>
                    <option>14 a 16</option>
                    <option>16 a 18</option>
                </select>
                <button>Registrar</button>
            </form>
            <p>{{mensaje}}</p>
        </div>
    </div>
    """, style=STYLE, mensaje=mensaje)

# -------------------- LOGIN --------------------

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["user"]=="admin" and request.form["pass"]=="1234":
            session["admin"]=True
            return redirect("/dashboard")
    return render_template_string("""
    {{ style|safe }}
    <div class="app">
        <div class="card">
            <h2>Login</h2>
            <form method="post">
                <input name="user" placeholder="Usuario">
                <input type="password" name="pass" placeholder="Contraseña">
                <button>Entrar</button>
            </form>
        </div>
    </div>
    """, style=STYLE)

# -------------------- DASHBOARD --------------------

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    df = pd.read_sql("""
        SELECT a.id, al.nombre, al.apellido, al.telefono, al.nivel,
               a.fecha, a.turno
        FROM asistencias a
        JOIN alumnos al ON a.alumno_id = al.id
        ORDER BY a.fecha DESC
    """, conn)
    conn.close()

    rows = ""
    for _,r in df.iterrows():
        rows += f"""
        <tr class='level-{r.nivel}'>
            <td>{r.nombre}</td>
            <td>{r.apellido}</td>
            <td>{r.telefono}</td>
            <td>{r.nivel}</td>
            <td>{r.fecha}</td>
            <td>{r.turno}</td>
            <td><a href="/delete/{r.id}">❌</a></td>
        </tr>
        """

    return render_template_string("""
    {{ style|safe }}
    <div class="app">
        <div class="card">
            <h2>Dashboard</h2>
            <a href="/export"><button>⬇ Exportar Excel</button></a>
            <table>
                <tr>
                    <th>Nombre</th><th>Apellido</th><th>Tel</th>
                    <th>Nivel</th><th>Fecha</th><th>Turno</th><th></th>
                </tr>
                {{rows|safe}}
            </table>
        </div>
    </div>
    """, style=STYLE, rows=rows)

# -------------------- DELETE --------------------

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# -------------------- EXPORT --------------------

@app.route("/export")
def export():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    df = pd.read_sql("""
        SELECT al.nombre, al.apellido, al.telefono, al.nivel,
               a.fecha, a.turno
        FROM asistencias a
        JOIN alumnos al ON a.alumno_id = al.id
    """, conn)
    conn.close()

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="asistencias.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --------------------

if __name__ == "__main__":
    app.run()
