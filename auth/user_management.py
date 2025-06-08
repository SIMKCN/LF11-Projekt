import sqlite3
import bcrypt

from config import DB_PATH


def get_users_with_permissions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT users.id, users.username, GROUP_CONCAT(permissions.name)
        FROM users
        LEFT JOIN user_permissions ON users.id = user_permissions.user_id
        LEFT JOIN permissions ON user_permissions.permission_id = permissions.id
        GROUP BY users.id, users.username
        ORDER BY users.id
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_permissions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM permissions")
    perms = c.fetchall()
    conn.close()
    return perms

def add_permission_if_not_exists(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def add_user(username, password, permission_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    user_id = c.lastrowid
    for pid in permission_ids:
        c.execute("INSERT INTO user_permissions (user_id, permission_id) VALUES (?, ?)", (user_id, pid))
    conn.commit()
    conn.close()

def update_user(user_id, username, password, permission_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if password:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("UPDATE users SET username=?, password_hash=? WHERE id=?", (username, password_hash, user_id))
    else:
        c.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
    c.execute("DELETE FROM user_permissions WHERE user_id=?", (user_id,))
    for pid in permission_ids:
        c.execute("INSERT INTO user_permissions (user_id, permission_id) VALUES (?, ?)", (user_id, pid))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def user_has_permission(user_id, permission_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT 1 FROM users
        JOIN user_permissions ON users.id = user_permissions.user_id
        JOIN permissions ON user_permissions.permission_id = permissions.id
        WHERE users.id=? AND permissions.name=?
    ''', (user_id, permission_name))
    ret = c.fetchone()
    conn.close()
    return ret is not None