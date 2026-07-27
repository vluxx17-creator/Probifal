import sqlite3
import datetime

DB_PATH = "phantom.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            subscription_until INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            query TEXT,
            result TEXT,
            timestamp INTEGER DEFAULT (strftime('%s', 'now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS mirrors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            created_by INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            visits INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def update_subscription(user_id, until_timestamp):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription_until=? WHERE user_id=?", (until_timestamp, user_id))
    conn.commit()
    conn.close()

def is_subscribed(user_id):
    row = get_user(user_id)
    if not row:
        return False
    until = row[4]
    return until > int(datetime.datetime.now().timestamp())

def set_admin(user_id, admin_flag=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin=? WHERE user_id=?", (admin_flag, user_id))
    conn.commit()
    conn.close()

def is_admin(user_id):
    row = get_user(user_id)
    return row and row[5] == 1

def add_log(user_id, action, query, result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, query, result) VALUES (?, ?, ?, ?)",
              (user_id, action, query, result))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY user_id")
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_logs(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE user_id=? ORDER BY timestamp DESC LIMIT 50", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def create_mirror(path, created_by):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO mirrors (path, created_by) VALUES (?, ?)", (path, created_by))
    conn.commit()
    conn.close()

def get_mirror(path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM mirrors WHERE path=?", (path,))
    row = c.fetchone()
    conn.close()
    return row

def increment_mirror_visits(path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE mirrors SET visits = visits + 1 WHERE path=?", (path,))
    conn.commit()
    conn.close()

def get_mirrors_by_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT path, visits, created_at FROM mirrors WHERE created_by=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows
