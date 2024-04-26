from flask import Flask, request, render_template, redirect, url_for, session, flash
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, create_connection
import openai
from flask import jsonify
import requests
from waitress import serve

# ...

app = Flask(__name__)
app.secret_key = '123'


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


from flask import g

@app.route('/comment/<int:message_id>', methods=['POST'])
def add_comment(message_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content']
    user_id = session['user_id']

    conn = create_connection()
    try:
        with conn:
            conn.execute("INSERT INTO comments (content, message_id, user_id) VALUES (?, ?, ?)",
                         (content, message_id, user_id))
    except Exception as e:
        conn.rollback()  # Roll back in case of error
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

    return redirect(url_for('dashboard'))


@app.route('/like/<int:message_id>', methods=['POST'])
def like_message(message_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE messages SET likes = likes + 1 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/dislike/<int:message_id>', methods=['POST'])
def dislike_message(message_id):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE messages SET dislikes = dislikes + 1 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))






@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    class_id = request.args.get('class_id')
    selected_class_id = int(class_id) if class_id else None
    
    conn = create_connection()
    cur = conn.cursor()
    
    # Fetch classes for the dropdown
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()
    
    # Determine the SQL query based on class_id
    if selected_class_id:
        cur.execute("SELECT id, content, user_id FROM messages WHERE class_id = ? ORDER BY id DESC", (selected_class_id,))
    else:
        cur.execute("SELECT id, content, user_id FROM messages ORDER BY id DESC")
    
    messages = [{'id': row[0], 'content': row[1], 'user_id': row[2], 'comments': []} for row in cur.fetchall()]
    
    # Fetch comments for each message
    for message in messages:
        cur.execute("SELECT content, user_id FROM comments WHERE message_id = ?", (message['id'],))
        comments = [{'content': row[0], 'user_id': row[1]} for row in cur.fetchall()]
        message['comments'] = comments

    conn.close()
    
    # Pass selected_class_id to the template for use in the form
    return render_template('dashboard.html', messages=messages, classes=classes, selected_class_id=selected_class_id)







@app.route('/post_message', methods=['POST'])
def post_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content']
    user_id = session['user_id']
    class_id = request.form.get('class_id')  # Get class_id from form data

    conn = create_connection()
    cur = conn.cursor()
    # Insert message with class_id if provided
    if class_id:
        cur.execute("INSERT INTO messages (content, user_id, class_id) VALUES (?, ?, ?)", (content, user_id, class_id))
    else:
        cur.execute("INSERT INTO messages (content, user_id) VALUES (?, ?)", (content, user_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('dashboard'))



@app.route('/search_messages', methods=['GET'])
def search_messages():
    query = request.args.get('query')
    conn = create_connection()
    cur = conn.cursor()
    # Use the '%' wildcard to find any matches containing the query string
    cur.execute("SELECT id, content, user_id FROM messages WHERE content LIKE ?", ('%' + query + '%',))
    messages = [{'id': row[0], 'content': row[1], 'user_id': row[2], 'comments': []} for row in cur.fetchall()]

    # Optionally, fetch comments for each message as well
    for message in messages:
        cur.execute("SELECT content, user_id FROM comments WHERE message_id = ?", (message['id'],))
        comments = [{'content': row[0], 'user_id': row[1]} for row in cur.fetchall()]
        message['comments'] = comments

    conn.close()

    # Render the dashboard template but only with messages containing the search query
    return render_template('dashboard.html', messages=messages)




@app.route('/add_class', methods=['POST'])
def add_class():
    if 'user_id' not in session:
        # Optionally, you could check if the user is an admin before allowing this action.
        return redirect(url_for('login'))
    
    class_name = request.form['class_name']
    
    if not class_name:
        flash('Class name cannot be empty.', 'error')
        return redirect(url_for('dashboard'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes WHERE name = ?", (class_name,))
    if cur.fetchone() is not None:
        flash('Class already exists.', 'error')
        conn.close()
        return redirect(url_for('dashboard'))
    
    cur.execute("INSERT INTO classes (name) VALUES (?)", (class_name,))
    conn.commit()
    conn.close()
    flash('New class added successfully.', 'success')
    
    return redirect(url_for('dashboard'))


@app.route('/get_classes')
def get_classes():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()
    conn.close()
    return render_template('classes_dropdown.html', classes=classes)



@app.route('/generate_ai_response/<int:message_id>', methods=['POST'])
def generate_ai_response(message_id):
    if 'user_id' not in session:
        # Redirect to login if the user is not in session
        return redirect(url_for('login'))

    # Fetch the content of the message
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT content FROM messages WHERE id = ?", (message_id,))
    message_row = cur.fetchone()
    
    if not message_row:
        return jsonify({'error': 'Message not found'}), 404
    
    # Ensure your OpenAI API key is correctly set

    openai.api_key = ' '

    
    try:
        response = openai.Completion.create(
          model="gpt-3.5-turbo",  # Updated to a newer model
          prompt=f"Respond to this message: {message_row['content']}",
          temperature=0.7,
          max_tokens=15 
        )
        ai_response = response['choices'][0]['text'].strip()  # Adjusted for the latest API
    except Exception as e:
        return jsonify({'error': str(e)}), 500
       
    # Insert AI response as a comment in the database
    cur.execute("INSERT INTO comments (content, message_id, user_id) VALUES (?, ?, ?)", (ai_response, message_id, session['user_id']))
    conn.commit()
    conn.close()
    
    # Redirect back to the dashboard after the operation
    return redirect(url_for('dashboard'))


@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = create_connection()
    cur = conn.cursor()
    
    # Fetch user information
    cur.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    
    # Fetch user messages
    cur.execute("SELECT id, content FROM messages WHERE user_id = ?", (user_id,))
    user_messages = cur.fetchall()
    
    conn.close()
    return render_template('account.html', user=user, user_messages=user_messages)



@app.route('/edit_username', methods=['POST'])
def edit_username():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_username = request.form['new_username']
    user_id = session['user_id']
    
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('account'))

if __name__ == '__main__':
    init_db()  # Initialize the database and create tables if they don't exist
    serve(app, host='0.0.0.0', port=5000)
