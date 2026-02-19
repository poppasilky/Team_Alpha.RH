from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = '4bfd33473e4141b0533378fad588b6294409464d93d39810'
UPLOAD_FOLDER = 'flask_app/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/action')
def action():
    return render_template('action.html')

@app.route('/drama')
def drama():
    return render_template('drama.html')

@app.route('/comedy')
def comedy():
    return render_template('comedy.html')

@app.route('/scifi')
def scifi():
    return render_template('scifi.html')

@app.route('/horror')
def horror():
    return render_template('horror.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return "Username and password required!"
        
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                        (username, hashed_password))
            conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "Username already exists!"
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                           (username, hashed_password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        else:
            return "Invalid username or password!"
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template('dashboard.html', 
                          username=session.get('username'))
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"

        file = request.files['file']

        if file.filename == '':
            return "No selected file"

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        return redirect('/dashboard')

    return render_template('upload.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)