
---

## CÓDIGO COMPLETO MEJORADO (Flask + Dark Mode + Chatbot WhatsApp):

```python
import os
import psycopg2
from flask import Flask, request, redirect, render_template_string, session, Response, jsonify
from datetime import datetime, date, timedelta
from collections import defaultdict
import csv
from io import StringIO
import requests
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-secreta-segura-cambiar-en-produccion")
DATABASE_URL = os.environ.get("DATABASE_URL")
WHATSAPP_ADMIN = os.environ.get("WHATSAPP_ADMIN", "5491123456789")  # Número del admin

# =========================
# CONFIGURACIÓN
# =========================
TURNOS = [
    "12:00 a 14:00",
    "14:00 a 16:00", 
    "16:00 a 18:00",
]

DIAS_HABILITADOS = (1, 2, 3)  # martes, miércoles, jueves

USUARIO_ADMIN = "DRTECNO"
PASSWORD_ADMIN = "laboratorio2026"

NIVELES = ["Inicial", "Intermedio", "Avanzado"]

FERIADOS = {
    "2026-01-01",
    "2026-03-24", 
    "2026-04-02",
    "2026-05-01",
    "2026-07-09",
    "2026-12-25",
}

MENSAJE_CONFIRMACION = """
✅ Turno confirmado.

Recordar:
• Llevar herramientas de uso personal (pinzas, flux, estaño, pegamento, etc).
• Respetar el horario elegido.
• Mantener orden y limpieza del puesto de trabajo.
• Si no puede asistir, avisar por WhatsApp para liberar el turno.
"""

# =========================
# UTILIDADES
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def es_admin():
    return session.get("admin") is True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not es_admin():
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def enviar_notificacion_whatsapp(datos_alumno, fecha, turno):
    """Genera link de WhatsApp para notificación al admin"""
    mensaje = f"""🔔 *NUEVA ASISTENCIA CONFIRMADA - LABORATORIO*

👤 *Alumno:* {datos_alumno['nombre']} {datos_alumno['apellido']}
📞 *Teléfono:* {datos_alumno['telefono']}
📅 *Fecha:* {fecha}
⏰ *Turno:* {turno}
📊 *Nivel:* {datos_alumno['nivel']}

🛠 *Recordar herramientas personales*
• Pinzas
• Flux
• Estaño
• Pegamento

_Confirmado automáticamente desde el sistema_"""
    
    # Codificar mensaje para URL
    mensaje_codificado = requests.utils.quote(mensaje)
    link = f"https://wa.me/{WHATSAPP_ADMIN}?text={mensaje_codificado}"
    return link

def validar_telefono(telefono):
    """Valida formato de teléfono argentino"""
    patron = r'^[0-9]{10,13}$'
    return re.match(patron, telefono) is not None

# =========================
# CSS DARK MODE
# =========================
DARK_CSS = """
<style>
    /* Variables CSS */
    :root {
        --bg-primary: #0A0A0A;
        --bg-secondary: #1E1E1E;
        --bg-card: #2A2A2A;
        --bg-hover: #333333;
        --text-primary: #FFFFFF;
        --text-secondary: #B0B0B0;
        --border-color: #3A3A3A;
        --border-hover: #4A4A4A;
        --blue-primary: #3B82F6;
        --blue-hover: #2563EB;
        --green-success: #22C55E;
        --green-hover: #16A34A;
        --red-error: #EF4444;
        --red-hover: #DC2626;
        --orange-warning: #F97316;
        --yellow: #EAB308;
        --purple: #A855F7;
        --whatsapp: #25D366;
        --shadow-sm: 0 2px 4px rgba(0,0,0,0.3);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
        --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);
    }

    /* Reset y estilos base */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        transition: all 0.3s ease;
    }

    body {
        margin: 0;
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: var(--text-primary);
        line-height: 1.6;
        min-height: 100vh;
    }

    /* Header glassmorphism */
    .header {
        position: fixed;
        top: 0;
        width: 100%;
        background: rgba(30, 30, 30, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-color);
        z-index: 1000;
        padding: 16px 0;
    }

    .header-inner {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header-logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .header-logo span {
        color: var(--blue-primary);
    }

    .header-nav {
        display: flex;
        gap: 20px;
    }

    .header-nav a {
        color: var(--text-secondary);
        text-decoration: none;
        font-weight: 500;
        padding: 8px 12px;
        border-radius: 8px;
        transition: all 0.3s;
    }

    .header-nav a:hover {
        color: var(--text-primary);
        background: var(--bg-hover);
    }

    .header-nav a.active {
        color: var(--blue-primary);
        background: rgba(59, 130, 246, 0.1);
    }

    /* Contenedor principal */
    .container {
        max-width: 1200px;
        margin: 100px auto 40px;
        padding: 0 20px;
    }

    /* Tarjetas */
    .card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 24px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border-color);
        transition: all 0.3s;
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
        border-color: var(--border-hover);
    }

    .card-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 20px;
        color: var(--text-primary);
    }

    /* Formularios */
    .form-group {
        margin-bottom: 20px;
    }

    .form-label {
        display: block;
        margin-bottom: 8px;
        color: var(--text-secondary);
        font-weight: 500;
    }

    .form-control {
        width: 100%;
        padding: 12px 16px;
        background: var(--bg-secondary);
        border: 2px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
        font-size: 1rem;
        transition: all 0.3s;
    }

    .form-control:focus {
        outline: none;
        border-color: var(--blue-primary);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }

    .form-control::placeholder {
        color: #666;
    }

    select.form-control {
        cursor: pointer;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20' stroke='%23B0B0B0'%3E%3Cpath stroke-linecap='round' stroke-linecap='round' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
        background-size: 20px;
        padding-right: 40px;
    }

    /* Botones */
    .btn {
        display: inline-block;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.3s;
        margin: 5px;
    }

    .btn-primary {
        background: var(--blue-primary);
        color: white;
    }

    .btn-primary:hover {
        background: var(--blue-hover);
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
    }

    .btn-success {
        background: var(--green-success);
        color: black;
    }

    .btn-success:hover {
        background: var(--green-hover);
        transform: translateY(-1px);
    }

    .btn-danger {
        background: var(--red-error);
        color: white;
    }

    .btn-danger:hover {
        background: var(--red-hover);
    }

    .btn-warning {
        background: var(--orange-warning);
        color: black;
    }

    .btn-outline {
        background: transparent;
        border: 2px solid var(--border-color);
        color: var(--text-primary);
    }

    .btn-outline:hover {
        border-color: var(--blue-primary);
        color: var(--blue-primary);
    }

    .btn-whatsapp {
        background: var(--whatsapp);
        color: white;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .btn-whatsapp:hover {
        background: #20B038;
        transform: translateY(-1px);
    }

    /* Tablas */
    .table-container {
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }

    .table {
        width: 100%;
        border-collapse: collapse;
        background: var(--bg-card);
    }

    .table th {
        background: var(--bg-secondary);
        color: var(--text-primary);
        font-weight: 600;
        padding: 16px;
        text-align: left;
        border-bottom: 2px solid var(--border-color);
    }

    .table td {
        padding: 14px 16px;
        border-bottom: 1px solid var(--border-color);
        color: var(--text-secondary);
    }

    .table tbody tr:hover {
        background: var(--bg-hover);
    }

    .table tbody tr:hover td {
        color: var(--text-primary);
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .badge-inicial {
        background: var(--green-success);
        color: black;
    }

    .badge-intermedio {
        background: var(--blue-primary);
        color: white;
    }

    .badge-avanzado {
        background: var(--purple);
        color: white;
    }

    /* Alertas */
    .alert {
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid transparent;
    }

    .alert-success {
        background: rgba(34, 197, 94, 0.1);
        border-left-color: var(--green-success);
        color: var(--green-success);
    }

    .alert-error {
        background: rgba(239, 68, 68, 0.1);
        border-left-color: var(--red-error);
        color: var(--red-error);
    }

    .alert-warning {
        background: rgba(249, 115, 22, 0.1);
        border-left-color: var(--orange-warning);
        color: var(--orange-warning);
    }

    /* CHATBOT WHATSAPP */
    .chat-widget {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 1000;
    }

    .chat-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: var(--whatsapp);
        border: none;
        cursor: pointer;
        box-shadow: var(--shadow-lg);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s;
        animation: pulse 2s infinite;
    }

    .chat-button:hover {
        transform: scale(1.1);
        box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
    }

    .chat-button svg {
        width: 30px;
        height: 30px;
        fill: white;
    }

    .chat-window {
        position: absolute;
        bottom: 80px;
        right: 0;
        width: 350px;
        background: var(--bg-card);
        border-radius: 15px;
        overflow: hidden;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border-color);
        display: none;
    }

    .chat-window.open {
        display: block;
        animation: slideIn 0.3s ease;
    }

    .chat-header {
        background: var(--whatsapp);
        padding: 15px 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .chat-header-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }

    .chat-header-info h3 {
        font-size: 1rem;
        margin: 0;
        color: white;
    }

    .chat-header-info p {
        font-size: 0.8rem;
        margin: 0;
        color: rgba(255,255,255,0.9);
    }

    .chat-messages {
        height: 300px;
        overflow-y: auto;
        padding: 20px;
        background: var(--bg-secondary);
    }

    .chat-message {
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
    }

    .chat-message.bot {
        align-items: flex-start;
    }

    .chat-message.user {
        align-items: flex-end;
    }

    .message-content {
        max-width: 80%;
        padding: 10px 15px;
        border-radius: 15px;
        font-size: 0.9rem;
    }

    .bot .message-content {
        background: var(--bg-card);
        color: var(--text-primary);
        border-bottom-left-radius: 5px;
    }

    .user .message-content {
        background: var(--blue-primary);
        color: white;
        border-bottom-right-radius: 5px;
    }

    .chat-options {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 8px;
    }

    .chat-option-btn {
        background: var(--bg-hover);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        padding: 8px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s;
    }

    .chat-option-btn:hover {
        background: var(--blue-primary);
        border-color: var(--blue-primary);
    }

    .chat-input-area {
        padding: 15px;
        background: var(--bg-card);
        border-top: 1px solid var(--border-color);
        display: flex;
        gap: 10px;
    }

    .chat-input {
        flex: 1;
        padding: 10px;
        border: 1px solid var(--border-color);
        border-radius: 20px;
        background: var(--bg-secondary);
        color: var(--text-primary);
    }

    .chat-send {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--whatsapp);
        border: none;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Loading spinner */
    .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid var(--border-color);
        border-top-color: var(--blue-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    /* Grid y utilidades */
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }

    .flex {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }

    .text-center {
        text-align: center;
    }

    .mt-4 {
        margin-top: 40px;
    }

    .mb-2 {
        margin-bottom: 20px;
    }

    /* Animaciones */
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(37, 211, 102, 0.7);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(37, 211, 102, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(37, 211, 102, 0);
        }
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* Responsive */
    @media (max-width: 768px) {
        .header-nav {
            gap: 10px;
        }
        
        .header-nav a {
            padding: 6px 10px;
            font-size: 0.9rem;
        }
        
        .chat-window {
            width: 300px;
            right: 0;
        }
        
        .grid {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 480px) {
        .header-inner {
            flex-direction: column;
            gap: 10px;
        }
        
        .chat-window {
            width: calc(100vw - 40px);
            right: -15px;
        }
    }
</style>
"""

# =========================
# CHATBOT HTML/JS
# =========================
CHATBOT_HTML = """
<!-- CHATBOT WHATSAPP -->
<div class="chat-widget">
    <button class="chat-button" onclick="toggleChat()">
        <svg viewBox="0 0 24 24">
            <path d="M19.05 4.91A9.816 9.816 0 0 0 12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01zm-7.01 15.24c-1.48 0-2.93-.4-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.32a8.23 8.23 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.24-8.24 2.2 0 4.27.86 5.82 2.42a8.183 8.183 0 0 1 2.41 5.83c.02 4.54-3.68 8.24-8.22 8.24z"/>
            <path d="M16.2 13.3c-.25-.12-1.47-.72-1.7-.8-.23-.08-.4-.12-.56.12-.16.25-.64.8-.78.96-.14.17-.29.19-.54.07-.25-.13-1.06-.39-2.02-1.25-.75-.67-1.26-1.5-1.41-1.75-.15-.25-.02-.38.11-.51.11-.11.25-.29.37-.44.12-.15.16-.25.25-.42.08-.17.04-.31-.02-.44-.06-.12-.56-1.35-.77-1.85-.2-.49-.4-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.23.25-.87.85-.87 2.08 0 1.22.89 2.4 1.02 2.57.13.17 1.73 2.65 4.2 3.62.59.23 1.05.37 1.41.48.59.17 1.13.15 1.56.09.48-.07 1.47-.6 1.68-1.18.21-.58.21-1.07.15-1.18-.06-.12-.22-.19-.47-.31z"/>
        </svg>
    </button>
    
    <div class="chat-window" id="chatWindow">
        <div class="chat-header">
            <div class="chat-header-avatar">🤖</div>
            <div class="chat-header-info">
                <h3>Laboratorio Electrónica</h3>
                <p>Online • Responde al instante</p>
            </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="chat-message bot">
                <div class="message-content">
                    👋 ¡Hola! Soy el asistente virtual del laboratorio. ¿En qué puedo ayudarte?
                </div>
                <div class="chat-options" id="initialOptions">
                    <button class="chat-option-btn" onclick="handleOption('agendar')">📅 Agendar asistencia</button>
                    <button class="chat-option-btn" onclick="handleOption('horarios')">🕒 Consultar horarios</button>
                    <button class="chat-option-btn" onclick="handleOption('whatsapp')">📞 Contactar por WhatsApp</button>
                </div>
            </div>
        </div>
        
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chatInput" placeholder="Escribí tu mensaje..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button class="chat-send" onclick="sendMessage()">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            </button>
        </div>
    </div>
</div>

<script>
let chatState = 'menu';
let reservaData = {};

function toggleChat() {
    const chatWindow = document.getElementById('chatWindow');
    chatWindow.classList.toggle('open');
}

function addMessage(text, isUser = false, showOptions = null) {
    const messages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user' : 'bot'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    messageDiv.appendChild(contentDiv);
    
    if (showOptions) {
        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'chat-options';
        optionsDiv.id = 'dynamicOptions';
        showOptions.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'chat-option-btn';
            btn.textContent = opt.text;
            btn.onclick = () => eval(opt.action);
            optionsDiv.appendChild(btn);
        });
        messageDiv.appendChild(optionsDiv);
    }
    
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
}

function handleOption(option) {
    if (option === 'agendar') {
        addMessage('¡Perfecto! Vamos a agendar tu asistencia al laboratorio.', false);
        addMessage('📞 Por favor, ingresá tu número de teléfono (solo números, sin espacios):', false);
        chatState = 'esperando_telefono';
    } else if (option === 'horarios') {
        addMessage('🕒 Los horarios disponibles son:', false);
        addMessage('• 12:00 a 14:00\n• 14:00 a 16:00\n• 16:00 a 18:00\n\n📅 Días: Martes, Miércoles y Jueves', false);
        addMessage('¿Querés agendar un turno?', false, [
            {text: '✅ Sí, agendar', action: 'handleOption(\'agendar\')'},
            {text: '❌ No, gracias', action: 'closeChat()'}
        ]);
    } else if (option === 'whatsapp') {
        window.open('/whatsapp-contact', '_blank');
    }
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addMessage(message, true);
    input.value = '';
    
    // Procesar según el estado
    if (chatState === 'esperando_telefono') {
        // Validar teléfono
        if (!/^[0-9]{10,13}$/.test(message)) {
            addMessage('❌ El número debe tener entre 10 y 13 dígitos. Intentá de nuevo:', false);
            return;
        }
        reservaData.telefono = message;
        addMessage('✅ Teléfono registrado. Ahora seleccioná una fecha:', false);
        
        // Mostrar fechas disponibles (próximos 7 días hábiles)
        fetch('/fechas-disponibles')
            .then(res => res.json())
            .then(data => {
                const options = data.fechas.map(f => ({
                    text: f,
                    action: `handleDate('${f}')`
                }));
                addMessage('Fechas disponibles:', false, options);
                chatState = 'esperando_fecha';
            });
    }
}

function handleDate(fecha) {
    reservaData.fecha = fecha;
    addMessage(`📅 Fecha seleccionada: ${fecha}`, false);
    addMessage('Seleccioná el turno:', false, [
        {text: '🕐 12:00 a 14:00', action: `handleTurno('12:00 a 14:00')`},
        {text: '🕐 14:00 a 16:00', action: `handleTurno('14:00 a 16:00')`},
        {text: '🕐 16:00 a 18:00', action: `handleTurno('16:00 a 18:00')`}
    ]);
    chatState = 'esperando_turno';
}

function handleTurno(turno) {
    reservaData.turno = turno;
    addMessage(`⏰ Turno seleccionado: ${turno}`, false);
    addMessage('Por último, ingresá tu nombre completo:', false);
    chatState = 'esperando_nombre';
}

function handleNombre(nombre) {
    reservaData.nombre = nombre;
    addMessage(`👤 Nombre: ${nombre}`, false);
    addMessage('Y tu apellido:', false);
    chatState = 'esperando_apellido';
}

function handleApellido(apellido) {
    reservaData.apellido = apellido;
    
    // Enviar reserva al servidor
    fetch('/reservar-whatsapp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(reservaData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            addMessage('✅ ¡Turno confirmado!', false);
            addMessage(`📱 Se ha enviado una notificación al administrador por WhatsApp.`, false);
            addMessage(MENSAJE_CONFIRMACION, false);
            
            // Ofrecer contacto directo
            addMessage('¿Querés contactar directamente por WhatsApp?', false, [
                {text: '📱 Sí, abrir WhatsApp', action: 'window.open(\'' + data.whatsapp_link + '\', \'_blank\')'},
                {text: '❌ No, gracias', action: 'closeChat()'}
            ]);
        } else {
            addMessage('❌ Error al confirmar el turno. Intentá de nuevo.', false);
        }
    });
    
    chatState = 'menu';
}

function closeChat() {
    document.getElementById('chatWindow').classList.remove('open');
}

// Escuchar mensajes del input
document.getElementById('chatInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        const message = this.value.trim();
        if (chatState === 'esperando_nombre') {
            handleNombre(message);
        } else if (chatState === 'esperando_apellido') {
            handleApellido(message);
        } else {
            sendMessage();
        }
    }
});
</script>
"""

# =========================
# HTML BASE MEJORADO
# =========================
BASE_HTML = DARK_CSS + """
<div class="header">
    <div class="header-inner">
        <div class="header-logo">
            🔧 <span>LAB</span>Electrónica
        </div>
        <div class="header-nav">
            <a href="/" class="{}">🧑 Registro</a>
            <a href="/asistencia" class="{}">🧪 Asistencia</a>
            {}
            {}
        </div>
    </div>
</div>
"""

def render_pagina(contenido, active_page=""):
    # Determinar clase activa para el menú
    clases = {
        "/": "active" if active_page == "registro" else "",
        "/asistencia": "active" if active_page == "asistencia" else "",
    }
    
    # Links de admin
    if es_admin():
        admin_links = '<a href="/dashboard">📊 Dashboard</a><a href="/logout">🚪 Salir</a>'
        login_link = ""
    else:
        admin_links = ""
        login_link = '<a href="/login">🔐 Admin</a>'
    
    header_html = BASE_HTML.format(
        clases["/"],
        clases["/asistencia"],
        admin_links,
        login_link
    )
    
    return header_html + f'<div class="container">{contenido}</div>' + CHATBOT_HTML

# =========================
# RUTAS
# =========================

@app.route("/", methods=["GET", "POST"])
def registro():
    msg = ""
    error = ""
    
    if request.method == "POST":
        telefono = request.form["telefono"]
        
        if not validar_telefono(telefono):
            error = "El teléfono debe tener entre 10 y 13 dígitos"
        else:
            try:
                db = get_db()
                cur = db.cursor()
                cur.execute("""
                    INSERT INTO alumnos (nombre, apellido, telefono, nivel)
                    VALUES (%s,%s,%s,%s)
                """, (
                    request.form["nombre"],
                    request.form["apellido"],
                    telefono,
                    request.form["nivel"]
                ))
                db.commit()
                msg = "✅ Alumno registrado correctamente."
            except psycopg2.errors.UniqueViolation:
                error = "❌ El alumno ya está registrado."
            finally:
                db.close()
    
    niveles_options = "".join(f'<option value="{n}">{n}</option>' for n in NIVELES)
    
    contenido = f"""
    <div class="card">
        <h1 class="card-title">📝 Registro Único de Alumno</h1>
        
        {f'<div class="alert alert-success">{msg}</div>' if msg else ''}
        {f'<div class="alert alert-error">{error}</div>' if error else ''}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">Nombre</label>
                <input class="form-control" name="nombre" placeholder="Ej: Juan" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Apellido</label>
                <input class="form-control" name="apellido" placeholder="Ej: Pérez" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Teléfono</label>
                <input class="form-control" name="telefono" placeholder="Ej: 1123456789" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Nivel</label>
                <select class="form-control" name="nivel" required>
                    <option value="">Seleccioná tu nivel</option>
                    {niveles_options}
                </select>
            </div>
            
            <button type="submit" class="btn btn-primary">Registrar Alumno</button>
        </form>
    </div>
    """
    
    return render_template_string(render_pagina(contenido, "registro"))

@app.route("/asistencia", methods=["GET", "POST"])
def asistencia():
    hoy = date.today()
    error = ""
    ok = ""
    whatsapp_link = ""

    if request.method == "POST":
        fecha_str = request.form["fecha"]
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        turno = request.form["turno"]
        telefono = request.form["telefono"]

        if not validar_telefono(telefono):
            error = "El teléfono debe tener entre 10 y 13 dígitos"
        elif fecha.weekday() not in DIAS_HABILITADOS:
            error = "❌ Solo martes, miércoles y jueves."
        elif fecha <= hoy:
            error = "❌ Los turnos deben sacarse con al menos 24 horas de anticipación."
        elif fecha_str in FERIADOS:
            error = "❌ No se puede sacar turno en un feriado."
        else:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id, nombre, apellido, nivel FROM alumnos WHERE telefono=%s", (telefono,))
            alumno = cur.fetchone()

            if not alumno:
                error = "❌ Alumno no registrado."
            else:
                cur.execute("SELECT 1 FROM asistencias WHERE fecha=%s AND turno=%s", (fecha, turno))
                if cur.fetchone():
                    error = "❌ Ese turno ya está ocupado."
                else:
                    cur.execute("""
                        INSERT INTO asistencias (alumno_id, fecha, turno)
                        VALUES (%s,%s,%s) RETURNING id
                    """, (alumno[0], fecha, turno))
                    asistencia_id = cur.fetchone()[0]
                    db.commit()
                    
                    # Generar notificación WhatsApp
                    datos_alumno = {
                        'nombre': alumno[1],
                        'apellido': alumno[2],
                        'telefono': telefono,
                        'nivel': alumno[3]
                    }
                    whatsapp_link = enviar_notificacion_whatsapp(datos_alumno, fecha_str, turno)
                    ok = MENSAJE_CONFIRMACION + f"\n\n📱 Se ha notificado al administrador por WhatsApp."
            db.close()

    opciones = "".join(f"<option>{t}</option>" for t in TURNOS)
    
    # Generar fechas mínima y máxima
    min_date = (hoy + timedelta(days=1)).isoformat()
    max_date = (hoy + timedelta(days=30)).isoformat()

    contenido = f"""
    <div class="card">
        <h1 class="card-title">🧪 Asistencia al Laboratorio</h1>
        
        {f'<div class="alert alert-error">{error}</div>' if error else ''}
        {f'<div class="alert alert-success" style="white-space: pre-line">{ok}</div>' if ok else ''}
        
        {f'<a href="{whatsapp_link}" target="_blank" class="btn btn-whatsapp">📱 Ver notificación enviada al admin</a>' if whatsapp_link else ''}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">📞 Teléfono</label>
                <input class="form-control" name="telefono" placeholder="Ej: 1123456789" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">📅 Fecha</label>
                <input class="form-control" type="date" name="fecha" min="{min_date}" max="{max_date}" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">⏰ Turno</label>
                <select class="form-control" name="turno" required>
                    <option value="">Seleccioná un turno</option>
                    {opciones}
                </select>
            </div>
            
            <button type="submit" class="btn btn-primary">Confirmar Turno</button>
        </form>
    </div>
    """
    
    return render_template_string(render_pagina(contenido, "asistencia"))

@app.route("/fechas-disponibles")
def fechas_disponibles():
    """API para chatbot - devuelve fechas disponibles"""
    hoy = date.today()
    fechas = []
    fecha_actual = hoy + timedelta(days=1)
    
    while len(fechas) < 7:  # Próximos 7 días hábiles
        if (fecha_actual.weekday() in DIAS_HABILITADOS and 
            fecha_actual.isoformat() not in FERIADOS):
            fechas.append(fecha_actual.strftime("%Y-%m-%d"))
        fecha_actual += timedelta(days=1)
    
    return jsonify({"fechas": fechas})

@app.route("/reservar-whatsapp", methods=["POST"])
def reservar_whatsapp():
    """API para chatbot - procesa reserva desde chat"""
    data = request.json
    
    try:
        db = get_db()
        cur = db.cursor()
        
        # Buscar alumno por teléfono
        cur.execute("SELECT id, nombre, apellido, nivel FROM alumnos WHERE telefono=%s", (data['telefono'],))
        alumno = cur.fetchone()
        
        if not alumno:
            return jsonify({"success": False, "error": "Alumno no registrado"})
        
        # Verificar turno disponible
        cur.execute("SELECT 1 FROM asistencias WHERE fecha=%s AND turno=%s", 
                   (data['fecha'], data['turno']))
        if cur.fetchone():
            return jsonify({"success": False, "error": "Turno ocupado"})
        
        # Crear asistencia
        cur.execute("""
            INSERT INTO asistencias (alumno_id, fecha, turno)
            VALUES (%s,%s,%s) RETURNING id
        """, (alumno[0], data['fecha'], data['turno']))
        db.commit()
        
        # Generar link de WhatsApp
        datos_alumno = {
            'nombre': alumno[1],
            'apellido': alumno[2],
            'telefono': data['telefono'],
            'nivel': alumno[3]
        }
        whatsapp_link = enviar_notificacion_whatsapp(datos_alumno, data['fecha'], data['turno'])
        
        return jsonify({
            "success": True,
            "whatsapp_link": whatsapp_link
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        db.close()

@app.route("/whatsapp-contact")
def whatsapp_contact():
    """Redirige a contacto por WhatsApp"""
    mensaje = "Hola, necesito ayuda con el laboratorio de electrónica"
    mensaje_codificado = requests.utils.quote(mensaje)
    return redirect(f"https://wa.me/{WHATSAPP_ADMIN}?text={mensaje_codificado}")

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, s.fecha, s.turno, a.nombre, a.apellido, a.nivel
        FROM asistencias s
        JOIN alumnos a ON a.id = s.alumno_id
        ORDER BY s.fecha DESC
    """)
    rows = cur.fetchall()
    db.close()

    # Organizar por fecha
    dias = defaultdict(dict)
    for aid, f, t, n, a, nivel in rows:
        dias[f][t] = (f"{n} {a}", nivel, aid)

    html = """
    <h1 class="card-title">📊 Dashboard</h1>
    <div style="margin-bottom: 20px;">
        <a class="btn btn-primary" href="/alumnos">👥 Historial de alumnos</a>
        <a class="btn btn-success" href="/exportar/todos">📥 Exportar todo</a>
    </div>
    """

    for fecha in sorted(dias.keys(), reverse=True):
        badge_color = "badge-inicial"  # default
        html += f"""
        <div class="card" style="margin-bottom: 20px;">
            <h3 style="color: var(--text-primary); margin-bottom: 15px;">📅 {fecha}</h3>
            <div class="table-container">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Turno</th>
                            <th>Alumno</th>
                            <th>Nivel</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for t in TURNOS:
            if t in dias[fecha]:
                alumno, nivel, aid = dias[fecha][t]
                badge_class = {
                    "Inicial": "badge-inicial",
                    "Intermedio": "badge-intermedio", 
                    "Avanzado": "badge-avanzado"
                }.get(nivel, "badge-inicial")
                
                html += f"""
                    <tr>
                        <td><strong>{t}</strong></td>
                        <td>{alumno}</td>
                        <td><span class="badge {badge_class}">{nivel}</span></td>
                        <td><a class="btn btn-danger btn-small" href="/eliminar-asistencia/{aid}" 
                               onclick="return confirm('¿Eliminar esta asistencia?')">🗑 Eliminar</a></td>
                    </tr>
                """
            else:
                html += f"""
                    <tr>
                        <td>{t}</td>
                        <td style="color: var(--text-secondary);">— Libre —</td>
                        <td>—</td>
                        <td>—</td>
                    </tr>
                """
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        """

    return render_template_string(render_pagina(html))

@app.route("/alumnos")
@login_required
def alumnos_menu():
    contenido = """
    <h1 class="card-title">📘 Historial de Alumnos por Nivel</h1>
    <div class="grid">
        <div class="card" style="text-align: center;">
            <h3 style="color: var(--green-success);">🟢 Inicial</h3>
            <p>Alumnos principiantes</p>
            <a class="btn btn-success" href="/alumnos/Inicial">Ver alumnos</a>
        </div>
        <div class="card" style="text-align: center;">
            <h3 style="color: var(--blue-primary);">🔵 Intermedio</h3>  
            <p>Alumnos con experiencia</p>
            <a class="btn btn-primary" href="/alumnos/Intermedio">Ver alumnos</a>
        </div>
        <div class="card" style="text-align: center;">
            <h3 style="color: var(--purple);">🟣 Avanzado</h3>
            <p>Alumnos avanzados</p>
            <a class="btn" style="background: var(--purple);" href="/alumnos/Avanzado">Ver alumnos</a>
        </div>
    </div>
    """
    return render_template_string(render_pagina(contenido))

@app.route("/alumnos/<nivel>")
@login_required
def alumnos_por_nivel(nivel):
    if nivel not in NIVELES:
        return redirect("/alumnos")

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT a.id, a.nombre, a.apellido, a.telefono, s.fecha, s.turno
        FROM alumnos a
        LEFT JOIN asistencias s ON s.alumno_id = a.id
        WHERE a.nivel = %s
        ORDER BY a.apellido, a.nombre, s.fecha DESC
    """, (nivel,))
    rows = cur.fetchall()
    db.close()

    alumnos = defaultdict(list)
    info = {}

    for aid, n, a, tel, f, t in rows:
        info[aid] = (n, a, tel)
        if f:
            alumnos[aid].append((f, t))

    badge_class = {
        "Inicial": "badge-inicial",
        "Intermedio": "badge-intermedio",
        "Avanzado": "badge-avanzado"
    }.get(nivel, "badge-inicial")

    html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h1 class="card-title">🎓 Nivel <span class="badge {badge_class}">{nivel}</span></h1>
        <a class="btn btn-success" href="/exportar/{nivel}">📥 Exportar CSV</a>
    </div>
    """

    for aid, data in info.items():
        n, a, tel = data
        hist = alumnos.get(aid, [])
        
        html += f"""
        <div class="card" style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h3 style="color: var(--text-primary);">{n} {a}</h3>
                    <p style="color: var(--text-secondary);">📞 {tel}</p>
                    <p style="color: var(--green-success);">✔ Asistencias: {len(hist)}</p>
                </div>
            </div>
        """
        
        if hist:
            html += """
            <div class="table-container">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Turno</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for f, t in hist:
                html += f"<tr><td>{f}</td><td>{t}</td></tr>"
            html += """
                    </tbody>
                </table>
            </div>
            """
        else:
            html += '<p style="color: var(--text-secondary);">Sin asistencias registradas</p>'
        
        html += "</div>"

    return render_template_string(render_pagina(html))

@app.route("/exportar/<nivel>")
@login_required
def exportar_nivel(nivel):
    if nivel not in NIVELES and nivel != "todos":
        return redirect("/alumnos")

    db = get_db()
    cur = db.cursor()
    
    if nivel == "todos":
        cur.execute("""
            SELECT a.nombre, a.apellido, a.telefono, a.nivel, 
                   COALESCE(s.fecha::text, '') as fecha, 
                   COALESCE(s.turno, '') as turno
            FROM alumnos a
            LEFT JOIN asistencias s ON s.alumno_id = a.id
            ORDER BY a.nivel, a.apellido
        """)
        filename = "todos_los_alumnos"
    else:
        cur.execute("""
            SELECT a.nombre, a.apellido, a.telefono, a.nivel, 
                   COALESCE(s.fecha::text, '') as fecha, 
                   COALESCE(s.turno, '') as turno
            FROM alumnos a
            LEFT JOIN asistencias s ON s.alumno_id = a.id
            WHERE a.nivel = %s
            ORDER BY a.apellido, a.nombre
        """, (nivel,))
        filename = f"alumnos_{nivel}"

    rows = cur.fetchall()
    db.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nombre", "Apellido", "Teléfono", "Nivel", "Fecha", "Turno"])
    for r in rows:
        writer.writerow(r)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
    )

@app.route("/eliminar-asistencia/<int:aid>")
@login_required
def eliminar_asistencia(aid):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM asistencias WHERE id=%s", (aid,))
    db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == USUARIO_ADMIN and request.form["password"] == PASSWORD_ADMIN:
            session["admin"] = True
            return redirect("/dashboard")
        else:
            error = "Usuario o contraseña incorrectos"
    
    contenido = f"""
    <div class="card" style="max-width: 400px; margin: 0 auto;">
        <h1 class="card-title">🔐 Login Admin</h1>
        
        {f'<div class="alert alert-error">{error}</div>' if error else ''}
        
        <form method="post">
            <div class="form-group">
                <label class="form-label">Usuario</label>
                <input class="form-control" name="usuario" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">Contraseña</label>
                <input class="form-control" type="password" name="password" required>
            </div>
            
            <button type="submit" class="btn btn-primary">Ingresar</button>
        </form>
    </div>
    """
    
    return render_template_string(render_pagina(contenido))

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# =========================
# INICIALIZACIÓN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
