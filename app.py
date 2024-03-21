from flask import Flask, request, render_template, redirect, url_for,session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('message_board.db')
        return conn
    except sqlite3.Error as e:
        print(e)

def init_db():
    users_table = """CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                    );"""
    messages_table = """CREATE TABLE IF NOT EXISTS messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content TEXT NOT NULL,
                            user_id INTEGER NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        );"""
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute(users_table)
            c.execute(messages_table)
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()

@app.route('/')
def index():
    # Example of fetching messages to display on index page
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages")
    messages = cur.fetchall()
    return render_template('index.html', messages=messages)




@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirmed_password = request.form['re-typed_password']

        if password != confirmed_password:
            error = 'Passwords do not match.'
        else:
            conn = create_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                error = 'Username is already taken. Try another one.'
            else:
                hashed_password = generate_password_hash(password)
                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()

                return redirect(url_for('login'))

            conn.close()

    return render_template('register.html', error=error)





@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = create_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user_record = cur.fetchone()
        conn.close()
        
        # Check if user_record exists and verify the password
        # Note that user_record[0] is the user's id and user_record[1] is the password
        if user_record and check_password_hash(user_record[1], password):
            session['user_id'] = user_record[0]
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'

    return render_template('login.html', error=error)




@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

if __name__ == '__main__':
    init_db()  # Initialize the database and create tables if they don't exist
    app.run(debug=True)
