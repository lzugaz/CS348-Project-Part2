import sqlite3

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = sqlite3.connect('message_board.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create tables."""
    conn = create_connection()
    cur = conn.cursor()

    create_comments_table = """
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (message_id) REFERENCES messages (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """

    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    """

    create_messages_table = """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """

    create_classes_table = """
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """

    alter_messages_table = """
    ALTER TABLE messages ADD COLUMN class_id INTEGER REFERENCES classes(id);
    """

    # Create indexes for the username and password columns
    create_username_index = """
    CREATE INDEX IF NOT EXISTS idx_username ON users (username);
    """

    create_password_index = """
    CREATE INDEX IF NOT EXISTS idx_password ON users (password);
    """

    # Execute the create table functions
    cur.execute(create_users_table)
    cur.execute(create_messages_table)
    cur.execute(create_comments_table)

    # Execute the new classes table creation and alter messages table
    cur.execute(create_classes_table)
    cur.execute(create_username_index)  # Create index for username
    cur.execute(create_password_index)  # Create index for password

    # Check first if the class_id column already exists to avoid an error
    cur.execute("PRAGMA table_info(messages)")
    columns = [info[1] for info in cur.fetchall()]
    if 'class_id' not in columns:
        cur.execute(alter_messages_table)

    conn.commit()
    conn.close()

