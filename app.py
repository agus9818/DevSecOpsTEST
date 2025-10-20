import sqlite3
from flask import Flask, request, jsonify, g
from flask_talisman import Talisman
import html
import click

# FUncionalidad de microservicio para manejo de comentarios

# --- Configuración y conexión a DB
app = Flask(__name__)
Talisman(app) # Inicializa Talisman para agregar cabeceras de seguridad automáticamente
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