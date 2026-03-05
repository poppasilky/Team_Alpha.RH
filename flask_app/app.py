from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import hashlib
import os
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv
load_dotenv()
                        

from services import tmdb               

app = Flask(__name__)
app.secret_key = '4bfd33473e4141b0533378fad588b6294409464d93d39810'
UPLOAD_FOLDER = 'flask_app/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TMDB_API_KEY'] = os.getenv('TMDB_API_KEY')
print("API Key loaded:", app.config['TMDB_API_KEY'])

@app.context_processor
def inject_genres():
    try:
        all_genres = tmdb.get_genres()
        return dict(all_genres=all_genres)
    except Exception as e:
        print(f"Error fetching genres for dropdown: {e}")
        return dict(all_genres=[])

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, movie_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
    offset = request.args.get('offset', 0, type=int)
    all_movies = tmdb.get_popular_movies()
    total_movies = len(all_movies)

    movies_per_page = 3
    start = offset
    end = start + movies_per_page
    movies_to_show = all_movies[start:end]

    has_prev = offset > 0
    has_next = end < total_movies
    
    conn = get_db_connection()
    comments = conn.execute('''
        SELECT global_comments.*, users.username
        FROM global_comments
        JOIN users ON global_comments.user_id = users.id
        ORDER BY created_at DESC
        LIMIT 20
    ''').fetchall()
    conn.close()
    
    return render_template('home.html',
                           movies=movies_to_show,
                           offset=offset,
                           has_prev=has_prev,
                           has_next=has_next,
                           comments=comments)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        gender = request.form.get('gender')
        comments = request.form.get('comments')

        return redirect(url_for('thx'))
    
    return render_template('contact.html')

@app.route('/thx')
def thx():
    return render_template('thx.html')
                        

@app.route('/genre/<int:genre_id>')
def genre_page(genre_id):
    movies = tmdb.get_movies_by_genre(genre_id)
    
    genre_name = "Selected Genre"
    all_genres = tmdb.get_genres()
    for g in all_genres:
        if g['id'] == genre_id:
            genre_name = g['name']
            break

    return render_template('genre_results.html', movies=movies, genre_name=genre_name)

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

@app.route('/set_language', methods=['POST'])
def set_language():
    selected_lang = request.form.get('language', 'en-US')
    session['language'] = selected_lang
    return redirect(request.referrer or url_for('home'))

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

@app.route('/search')
def search():
    query = request.args.get('q')
    if query:
        movies = tmdb.search_movies(query)
    else:
        movies = []

    return render_template('genre_results.html', movies=movies, genre_name=f"Results for: {query}")

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    # Pull the language preference from the session (default to English)
    lang = session.get('language', 'en-US')
    movie = tmdb.get_movie_details(movie_id, language=lang)
    trailer = tmdb.get_movie_trailer(movie_id, language=lang)

    conn = get_db_connection()
    reviews = conn.execute('''
        SELECT reviews.*, users.username 
        FROM reviews 
        JOIN users ON reviews.user_id = users.id 
        WHERE movie_id = ? 
        ORDER BY created_at DESC
    ''', (movie_id,)).fetchall()
    conn.close()

    user_review = None
    if 'user_id' in session:
        conn = get_db_connection()
        user_review = conn.execute('SELECT * FROM reviews WHERE user_id = ? AND movie_id = ?',
                                   (session['user_id'], movie_id)).fetchone()
        conn.close()

    return render_template('movie_detail.html',
                           movie=movie,
                           trailer=trailer,
                           reviews=reviews,
                           user_review=user_review)

@app.route('/movie/<int:movie_id>/review', methods=['POST'])
def submit_review(movie_id):
    if 'user_id' not in session:
        return redirect('/login')

    rating = request.form.get('rating', type=int)
    review_text = request.form.get('review_text', '')

    if not rating or rating < 1 or rating > 5:
        return "Rating must be between 1 and 5."

    user_id = session['user_id']
    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM reviews WHERE user_id = ? AND movie_id = ?',
                            (user_id, movie_id)).fetchone()
    if existing:
        conn.execute('''
            UPDATE reviews 
            SET rating = ?, review_text = ?, created_at = CURRENT_TIMESTAMP 
            WHERE user_id = ? AND movie_id = ?
        ''', (rating, review_text, user_id, movie_id))
    else:
        conn.execute('''
            INSERT INTO reviews (user_id, movie_id, rating, review_text)
            VALUES (?, ?, ?, ?)
        ''', (user_id, movie_id, rating, review_text))
    conn.commit()
    conn.close()

    return redirect(f'/movie/{movie_id}')

@app.route('/quick_review', methods=['POST'])
def quick_review():
    if 'user_id' not in session:
        return redirect('/login')

    movie_id = request.form.get('movie_id', type=int)
    rating = request.form.get('rating', type=int)
    review_text = request.form.get('review_text', '')

    if not movie_id or not rating or rating < 1 or rating > 5:
        return "Invalid input."

    user_id = session['user_id']
    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM reviews WHERE user_id = ? AND movie_id = ?',
                            (user_id, movie_id)).fetchone()
    if existing:
        conn.execute('''
            UPDATE reviews
            SET rating = ?, review_text = ?, created_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND movie_id = ?
        ''', (rating, review_text, user_id, movie_id))
    else:
        conn.execute('''
            INSERT INTO reviews (user_id, movie_id, rating, review_text)
            VALUES (?, ?, ?, ?)
        ''', (user_id, movie_id, rating, review_text))
    conn.commit()
    conn.close()
    offset = request.form.get('offset', 0, type=int)
    
    return redirect(url_for('home', offset=offset))

@app.route('/post_comment', methods=['POST'])
def post_comment():
    if 'user_id' not in session:
        return redirect('/login')
    content = request.form.get('content', '').strip()
    if content:
        conn = get_db_connection()
        conn.execute('INSERT INTO global_comments (user_id, content) VALUES (?, ?)',
                     (session['user_id'], content))
        conn.commit()
        conn.close()
    offset = request.args.get('offset', 0)
    return redirect(url_for('home', offset=offset))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)