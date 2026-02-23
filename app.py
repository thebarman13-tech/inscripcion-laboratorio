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

/* ---------- MODAL ---------- */

.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0; top: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.7);
}
.modal-content {
    background: white;
    color: black;
    margin: 10% auto;
    padding: 20px;
    border-radius: 14px;
    max-width: 420px;
}
.modal-content h3 {
    margin-top: 0;
}
.modal-buttons {
    display: flex;
    gap: 10px;
}
.modal-buttons button {
    flex: 1;
}
.cancel {
    background: #9ca3af;
}
.confirm {
    background: #16a34a;
}
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
    {{style|safe}}
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
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO alumnos (nombre,apellido,telefono,nivel)
        VALUES (?,?,?,?)
        """, (
            request.form["nombre"].title(),
            request.form["apellido"].title(),
            request.form["telefono"],
            request.form["nivel"]
        ))
        conn.commit()
        conn.close()
        return redirect("/")

    return render_template_string("""
    {{style|safe}}
    <div class="app">
        <div class="card">
            <h2>Inscripción única alumno</h2>
            <form method="post">
                <input name="nombre" placeholder="Nombre" required>
                <input name="apellido" placeholder="Apellido" required>
                <input name="telefono" placeholder="Teléfono" required>

                <label><input type="radio" name="nivel" value="Inicial" required> Inicial</label>
                <label><input type="radio" name="nivel" value="Intermedio"> Intermedio</label>
                <label><input type="radio" name="nivel" value="Avanzado"> Avanzado</label>

                <button>Registrar alumno</button>
            </form>
        </div>
    </div>
    """, style=STYLE)

# -------------------- LABORATORIO (CON MODAL) --------------------

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
    {{style|safe}}
    <div class="app">
        <div class="card">
            <h2>Inscripción Laboratorio</h2>

            <form id="formLab" method="post">
                <input name="telefono" id="telefono" placeholder="Teléfono" required>
                <select name="turno" id="turno" required>
                    <option value="">Turno</option>
                    <option>10 a 12</option>
                    <option>14 a 16</option>
                    <option>16 a 18</option>
                </select>
                <button type="button" onclick="openModal()">Registrar</button>
            </form>

            <p>{{mensaje}}</p>
        </div>
    </div>

    <!-- MODAL -->
    <div class="modal" id="modal">
        <div class="modal-content">
            <h3>Confirmación</h3>
            <p id="textoConfirmacion"></p>
            <div class="modal-buttons">
                <button class="cancel" onclick="closeModal()">Cancelar</button>
                <button class="confirm" onclick="confirmar()">Confirmar</button>
            </div>
        </div>
    </div>

    <script>
    function openModal(){
        let turno = document.getElementById("turno").value;
        if(!turno){ alert("Seleccione un turno"); return; }

        let hoy = new Date().toLocaleDateString();
        document.getElementById("textoConfirmacion").innerHTML = `
        ¿Confirma la asistencia al laboratorio el día <b>${hoy}</b> a la hora <b>${turno}</b>?<br><br>
        • Recordar llevar las herramientas de uso personal.<br>
        • Respetar el horario elegido.<br>
        • Respetar normas del laboratorio.<br>
        • Avisar por WhatsApp si no puede asistir.
        `;
        document.getElementById("modal").style.display = "block";
    }

    function closeModal(){
        document.getElementById("modal").style.display = "none";
    }

    function confirmar(){
        document.getElementById("formLab").submit();
    }
    </script>
    """, style=STYLE, mensaje=mensaje)

# --------------------

if __name__ == "__main__":
    app.run()
