import sqlite3
import bcrypt

from config import DB_PATH


def get_users_with_permissions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT USERS.ID, USERS.USERNAME, GROUP_CONCAT(PERMISSIONS.APP_PERM)
        FROM USERS
        LEFT JOIN REF_USER_PERMISSIONS ON USERS.ID = REF_USER_PERMISSIONS.USER_ID
        LEFT JOIN PERMISSIONS ON REF_USER_PERMISSIONS.PERMISSION_ID = PERMISSIONS.ID
        GROUP BY USERS.ID, USERS.USERNAME
        ORDER BY USERS.ID
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_permissions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ID, APP_PERM FROM PERMISSIONS")
    perms = c.fetchall()
    conn.close()
    return perms

def add_permission_if_not_exists(value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO PERMISSIONS (APP_PERM) VALUES (?)", (value,))
    conn.commit()
    conn.close()

def add_user(username, password, permission_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT INTO USERS (USERNAME, PASSWORD_HASH) VALUES (?, ?)", (username, password_hash))
    user_id = c.lastrowid
    for pid in permission_ids:
        c.execute("INSERT INTO REF_USER_PERMISSIONS (USER_ID, PERMISSION_ID) VALUES (?, ?)", (user_id, pid))
    conn.commit()
    conn.close()

def update_user(user_id, username, password, permission_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if password:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("UPDATE USERS SET USERNAME=?, PASSWORD_HASH=? WHERE ID=?", (username, password_hash, user_id))
    else:
        c.execute("UPDATE USERS SET USERNAME=? WHERE id=?", (username, user_id))
    c.execute("DELETE FROM REF_USER_PERMISSIONS WHERE USER_ID=?", (user_id,))
    for pid in permission_ids:
        c.execute("INSERT INTO REF_USER_PERMISSIONS (USER_ID, PERMISSION_ID) VALUES (?, ?)", (user_id, pid))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM USERS WHERE ID=?", (user_id,))
    conn.commit()
    conn.close()

def user_has_permission(user_id, permission_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT 1 FROM users
        JOIN REF_USER_PERMISSIONS ON USERS.ID = REF_USER_PERMISSIONS.USER_ID
        JOIN PERMISSIONS ON REF_USER_PERMISSIONS.PERMISSION_ID = PERMISSIONS.ID
        WHERE USERS.ID=? AND PERMISSIONS.APP_PERM=?
    ''', (user_id, permission_name))
    ret = c.fetchone()
    conn.close()
    return ret is not None