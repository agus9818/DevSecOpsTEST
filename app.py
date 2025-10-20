import sqlite3
from flask import Flask, request, jsonify, g
from flask_talisman import Talisman, GOOGLE_CSP_POLICY
import html
import click

# FUncionalidad de microservicio para manejo de comentarios

# --- Configuración y conexión a DB
app = Flask(__name__)

# Política de Seguridad de Contenido (CSP) más estricta para una API
# Usamos una política base robusta y la personalizamos
csp = GOOGLE_CSP_POLICY.copy()
csp['object-src'] = '\'none\''
csp['frame-ancestors'] = '\'none\''

# Inicializa Talisman.
# force_https=False es crucial para el entorno de CI/CD, donde no hay un proxy inverso
# que gestione TLS. Sin esto, Talisman redirigiría HTTP a HTTPS, causando que el
# escaneo de ZAP falle al no poder conectar con un servidor que no habla SSL/TLS.
# NOTA: Se ha cambiado force_https a False para alinearse con el entorno de CI.
# Se añade la política CSP personalizada.
# Se añaden políticas de aislamiento para mitigar ataques como Spectre.
Talisman(
    app,
    force_https=False,
    content_security_policy=csp,
)

# Middleware para añadir cabeceras de seguridad faltantes
@app.after_request
def add_extra_security_headers(response):
    response.headers['Server'] = 'Microservicio Web' # Oculta información del servidor
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache' # Compatibilidad con HTTP/1.0
    return response

DATABASE = 'database.db'

def get_db():

    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Permite acceder a las columnas por nombre
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):

    db = getattr(g, '_database', None)
    
    if db is not None:
        db.close()

@app.cli.command('init-db')
def init_db():
    """Limpia los datos existentes y crea nuevas tablas."""
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
    click.echo('Base de datos inicializada.')

# --- Sanitización de salida (Mitigación de XSS)
def escape_html(text):

    if isinstance(text, str):
        return html.escape(text)
    return text

# --- Endpoint 0: Raíz (GET) - Para satisfacer el health check de ZAP
@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "API de comentarios está activa."}), 200

# --- Endpoint para robots.txt - Evita 404 en escaneos
@app.route('/robots.txt')
def robots_txt():
    # Instruye a todos los crawlers a no indexar el sitio
    response = app.response_class("User-agent: *\nDisallow: /", mimetype="text/plain")
    return response

# --- Endpoint para sitemap.xml - Evita 404 en escaneos
@app.route('/sitemap.xml')
def sitemap_xml():
    return jsonify({"error": "Not Found"}), 404

# --- Endpoint 1: Agregar comentario (POST)
@app.route('/api/comment', methods=['POST'])
def add_comment():

    if not request.is_json:
        return jsonify({"error": "La solicitud debe ser de tipo application/json"}), 415

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
    cursor = db.cursor()
    cursor.execute ("SELECT id, username, comment FROM comments ORDER BY id DESC")

    raw_comments = cursor.fetchall()
    safe_comments = []

    # Se aplica el esacpae antes de la salida al cliente
    for row in raw_comments:
        safe_comments.append({
            "id": row['id'],
            "username": escape_html(row['username']),
            "comment": escape_html(row['comment'])
        })

    return jsonify(safe_comments)

if __name__ == '__main__':
    app.run(debug=False, host= '0.0.0.0', port=5000)