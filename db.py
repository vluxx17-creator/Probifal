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
            is_admin INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            requests_balance INTEGER DEFAULT 0
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
        CREATE TABLE IF NOT EXISTS clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            owner_id INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            is_active INTEGER DEFAULT 1
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

def set_admin(user_id, admin_flag=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin=? WHERE user_id=?", (admin_flag, user_id))
    conn.commit()
    conn.close()

def is_admin(user_id):
    row = get_user(user_id)
    return row and row[4] == 1

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

def get_all_logs(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------- Баланс запросов ----------
def get_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT requests_balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_requests(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET requests_balance = requests_balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def use_request(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET requests_balance = requests_balance - 1 WHERE user_id=? AND requests_balance > 0", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def can_make_request(user_id):
    if is_admin(user_id):
        return True, None
    balance = get_balance(user_id)
    if balance <= 0:
        return False, "У вас закончились запросы. Пополните баланс в разделе «Купить запросы»."
    return True, None

# ---------- Клоны ----------
def add_clone(token, owner_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO clones (token, owner_id) VALUES (?, ?)", (token, owner_id))
    conn.commit()
    conn.close()

def get_clones_by_owner(owner_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, token, created_at, is_active FROM clones WHERE owner_id=? ORDER BY created_at DESC", (owner_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_active_clones():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, token, owner_id FROM clones WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return rows

def deactivate_clone(clone_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE clones SET is_active=0 WHERE id=?", (clone_id,))
    conn.commit()
    conn.close()
