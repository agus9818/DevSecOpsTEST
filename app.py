import sqlite3
from flask import Flask, request, jsonify, g, send_from_directory
from flask_talisman import Talisman
import html

# FUncionalidad de microservicio para manejo de comentarios


# --- Configuración y conexión a DB
app = Flask(__name__)
csp = {
    'default-src': '\'self\'',
    'script-src': "'self'",
    'style-src': "'self'",
    'object-src': "'none'", # Deshabilita plugins como Flash
    'base-uri': "'none'", # Previene ataques de "base tag hijacking"
    'form-action': "'none'", # Solución para [WARN-NEW: 10055]
}
Talisman(
    app,
    force_https=False, # Necesario para pruebas locales/CI sin SSL
    content_security_policy=csp,
    frame_options='DENY',
    session_cookie_secure=False, # En producción debería ser True,
    session_cookie_http_only=True
)
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Permite acceder a las columnas por nombre
    return db

# Solución para las advertencias de ZAP:
# - [WARN-NEW: 10036] Elimina el header "Server"
# - [WARN-NEW: 90004] Añade aislamiento contra Spectre
# - [WARN-NEW: 10049] Añade cabeceras anti-caché a las respuestas de la API
@app.after_request
def add_security_headers(response):
    response.headers.pop('Server', None)
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    if '/api/' in request.path:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.teardown_appcontext
def close_connection(exception):

    db = getattr(g, '_database', None)
    
    if db is not None:
        db.close()

def init_db():

    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       username TEXT NOT NULL,
                       comment TEXT NOT NULL
            )
        ''')
        db.commit()

# Registra el comando 'init-db' con la aplicación Flask
@app.cli.command('init-db')
def init_db_command():
    """Limpia los datos existentes y crea nuevas tablas."""
    init_db()
    print('Base de datos inicializada.')

# --- Sanitización de salida (Mitigación de XSS)
def escape_html(text):

    if isinstance(text, str):
        return html.escape(text)
    return text

@app.route('/')
def index():
    return "OK", 200

# --- Endpoint para servir la especificación OpenAPI
@app.route('/openapi.yaml')
def openapi_spec():
    return send_from_directory('.', 'openapi.yaml')

# --- Endpoint 1: Agregar comentario (POST)
@app.route('/api/comment', methods=['POST'])
def add_comment():

    # Acepta datos JSON y los inserta en la BD
    #Preveción de Inyección SQL(SQLi)
    data = request.get_json()
    username = data.get('username', 'Anónimo')
    comment = data.get('comment', '')
    
    if not comment:
        return jsonify({'error': 'El comentario no puede estar vacío.'}), 400
    
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO comments (username, comment) VALUES (?, ?)",
            (username, comment) #Los datos se pasan como una tupla separada
        )
        db.commit()
        return jsonify({'message': 'Comentario agregado correctamente.'}), 201
    except sqlite3.Error:
        return jsonify({'error': 'Error al agregar el comentario.'}), 500
    
# Endpoint 2: Obtener comentarios (GET)
@app.route('/api/comments', methods=['GET'])
def get_comments():
    #Recupera los comentarios de la BD
    # Mitigación de XSS mediante sanitización de salida

    db = get_db()
    cursor = db.cursor() # El row_factory ya está configurado en la conexión
    cursor.execute ("SELECT id, username, comment FROM comments ORDER BY id DESC")

    raw_comments = cursor.fetchall()
    safe_comments = []

    # Se aplica el esacpae antes de la salida al cliente
    for row in raw_comments:
        safe_comments.append({
            "id": row["id"],
            "username": escape_html(row["username"]),
            "comment": escape_html(row["comment"])
        })

    return jsonify(safe_comments)

if __name__ == '__main__':
    app.run(debug=False, host= '0.0.0.0', port=5000)