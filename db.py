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
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            daily_requests INTEGER DEFAULT 0,
            last_request_date INTEGER DEFAULT 0
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

def get_all_logs(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------- Клоны (зеркальные боты) ----------
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

# ---------- Дневной лимит ----------
def get_daily_requests(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT daily_requests, last_request_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return 0, 0

def reset_daily_requests_if_needed(user_id):
    today = int(datetime.datetime.now().timestamp() // 86400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT daily_requests, last_request_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        last_date = row[1] // 86400 if row[1] else 0
        if last_date != today:
            c.execute("UPDATE users SET daily_requests=0, last_request_date=? WHERE user_id=?", (int(datetime.datetime.now().timestamp()), user_id))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def increment_daily_requests(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET daily_requests = daily_requests + 1, last_request_date = ? WHERE user_id=?", (int(datetime.datetime.now().timestamp()), user_id))
    conn.commit()
    conn.close()

def can_make_request(user_id):
    if is_admin(user_id) or is_subscribed(user_id):
        return True, None
    reset_daily_requests_if_needed(user_id)
    daily, _ = get_daily_requests(user_id)
    if daily >= 2:
        return False, "Вы исчерпали лимит на сегодня (2 запроса). Купите подписку для неограниченного доступа."
    return True, None

def reset_requests_for_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET daily_requests=0, last_request_date=? WHERE user_id=?", (int(datetime.datetime.now().timestamp()), user_id))
    conn.commit()
    conn.close()
