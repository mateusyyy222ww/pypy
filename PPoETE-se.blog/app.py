import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import datetime

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
PASSWORD = "9999"  # Definindo a senha para postar e deletar

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS posts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            author TEXT NOT NULL,
                            content TEXT NOT NULL,
                            date TEXT NOT NULL,
                            reactions_stars INTEGER DEFAULT 0,
                            reactions_graduation INTEGER DEFAULT 0,
                            reactions_clap INTEGER DEFAULT 0
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS media (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            post_id INTEGER,
                            media_url TEXT,
                            media_type TEXT,
                            caption TEXT,
                            FOREIGN KEY (post_id) REFERENCES posts (id)
                        )''')
        conn.commit()

init_db()

@app.route('/posts', methods=['GET'])
def get_posts():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    results = []
    for post in posts:
        post_data = dict(post)
        media = conn.execute('SELECT media_url, media_type, caption FROM media WHERE post_id = ?', (post['id'],)).fetchall()
        post_data['media'] = [dict(m) for m in media]
        results.append(post_data)
    conn.close()
    return jsonify(results)

@app.route('/posts', methods=['POST'])
def add_post():
    password = request.form.get('password')
    
    if password != PASSWORD:
        return jsonify({'error': 'Senha incorreta'}), 403

    author = request.form.get('author')
    content = request.form.get('content')
    caption = request.form.get('caption')
    date = datetime.datetime.now().isoformat()

    if not author or not content:
        return jsonify({'error': 'Os campos "author" e "content" são obrigatórios.'}), 400

    conn = get_db_connection()
    conn.execute('INSERT INTO posts (author, content, date) VALUES (?, ?, ?)', (author, content, date))
    post_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    files = request.files.getlist('media')
    for file in files:
        if file and allowed_file(file.filename):
            filename = f"{datetime.datetime.now().timestamp()}_{file.filename}"
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(media_path)
            media_url = f"/{UPLOAD_FOLDER}/{filename}"
            media_type = 'image' if 'image' in file.content_type else 'video'
            conn.execute('INSERT INTO media (post_id, media_url, media_type, caption) VALUES (?, ?, ?, ?)', (post_id, media_url, media_type, caption))

    conn.commit()
    new_post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    media = conn.execute('SELECT media_url, media_type, caption FROM media WHERE post_id = ?', (post_id,)).fetchall()
    new_post_data = dict(new_post)
    new_post_data['media'] = [dict(m) for m in media]
    conn.close()
    return jsonify(new_post_data), 201

@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    data = request.get_json()
    password = data.get("password")

    if password != PASSWORD:
        return jsonify({'error': 'Senha incorreta'}), 403

    conn = get_db_connection()
    conn.execute('DELETE FROM media WHERE post_id = ?', (post_id,))
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'Post deletado com sucesso!'}), 200

@app.route('/posts/<int:post_id>/react', methods=['POST'])
def react_to_post(post_id):
    data = request.get_json()
    reaction_type = data['reaction']
    
    conn = get_db_connection()
    if reaction_type == 'star':
        conn.execute('UPDATE posts SET reactions_stars = reactions_stars + 1 WHERE id = ?', (post_id,))
    elif reaction_type == 'graduation':
        conn.execute('UPDATE posts SET reactions_graduation = reactions_graduation + 1 WHERE id = ?', (post_id,))
    elif reaction_type == 'clap':
        conn.execute('UPDATE posts SET reactions_clap = reactions_clap + 1 WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'Reaction added successfully'})

@app.route(f'/{UPLOAD_FOLDER}/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
