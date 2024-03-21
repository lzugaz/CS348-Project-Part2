import sqlite3

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect('message_board.db')
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(create_table_sql):
    """Create a table from the create_table_sql statement."""
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")

def init_db():
    """Initialize the database and create tables."""
    create_users_table = """CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT NOT NULL UNIQUE,
                                password TEXT NOT NULL
                            );"""
    create_messages_table = """CREATE TABLE IF NOT EXISTS messages (
                                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                                  content TEXT NOT NULL,
                                  user_id INTEGER NOT NULL,
                                  FOREIGN KEY (user_id) REFERENCES users (id)
                              );"""
    create_table(create_users_table)
    create_table(create_messages_table)
