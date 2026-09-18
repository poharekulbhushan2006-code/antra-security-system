import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DATABASE_PATH

def get_connection():
    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
        
        # 1. Registered Authorized Personnel
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            pin_salt TEXT NOT NULL,
            face_descriptor TEXT NOT NULL,
            photo_filename TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
        """)
        
        # 2. Intruder & Unregistered Access Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS intruder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            photo_filename TEXT NOT NULL,
            threat_level TEXT DEFAULT 'CRITICAL',
            score REAL DEFAULT 0.0,
            reason TEXT NOT NULL,
            email_sent INTEGER DEFAULT 0,
            email_recipient TEXT,
            resolved INTEGER DEFAULT 0,
            notes TEXT
        )
        """)
        
        # 3. Security Audit Logs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            user_name TEXT,
            employee_id TEXT,
            details TEXT,
            status TEXT NOT NULL,
            ip_address TEXT DEFAULT '127.0.0.1'
        )
        """)
        
        # 4. Key-Value System Settings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)
        
        conn.commit()
    except Exception as e:
        print(f"[WARN] init_db: {e}")

# --- Users Operations ---

def get_all_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, employee_id, role, photo_filename, created_at, status FROM users WHERE status = 'ACTIVE' ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_users_with_descriptors() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, employee_id, role, pin_hash, pin_salt, face_descriptor, photo_filename, status FROM users WHERE status = 'ACTIVE'")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["face_descriptor"] = json.loads(d["face_descriptor"])
            except Exception:
                d["face_descriptor"] = []
            result.append(d)
        return result

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            try:
                d["face_descriptor"] = json.loads(d["face_descriptor"])
            except Exception:
                d["face_descriptor"] = []
            return d
        return None

def get_user_by_employee_id(emp_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE employee_id = ?", (emp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_user(name: str, employee_id: str, role: str, pin_hash: str, pin_salt: str, face_descriptor: List[float] = None, descriptor: List[float] = None, photo_filename: str = None) -> int:
    desc = face_descriptor if face_descriptor is not None else (descriptor or [])
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO users (name, employee_id, role, pin_hash, pin_salt, face_descriptor, photo_filename, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (name, employee_id, role, pin_hash, pin_salt, json.dumps(desc), photo_filename, now))
        conn.commit()
        return cursor.lastrowid

register_user = create_user

def delete_user(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'REVOKED' WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

# --- Intruder Operations ---

def log_intruder(photo_filename: str, reason: str, threat_level: str = "CRITICAL", score: float = 0.0, email_recipient: str = None) -> int:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
            INSERT INTO intruder_logs (timestamp, photo_filename, threat_level, score, reason, email_recipient)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (now, photo_filename, threat_level, score, reason, email_recipient))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"[WARN] log_intruder error: {e}")
        return 0

def get_recent_intruders(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM intruder_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def update_intruder_email_status(incident_id: int, status: int, recipient: str = None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if recipient:
                cursor.execute("UPDATE intruder_logs SET email_sent = ?, email_recipient = ? WHERE id = ?", (status, recipient, incident_id))
            else:
                cursor.execute("UPDATE intruder_logs SET email_sent = ? WHERE id = ?", (status, incident_id))
            conn.commit()
    except Exception as e:
        print(f"[WARN] update_intruder_email_status error: {e}")

def resolve_intruder(incident_id: int, notes: str = "") -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE intruder_logs SET resolved = 1, notes = ? WHERE id = ?", (notes, incident_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"[WARN] resolve_intruder error: {e}")
        return False

mark_intruder_resolved = resolve_intruder
get_all_intruders = get_recent_intruders

# --- Audit Logging Operations ---

def log_audit(event_type: str, status: str, details: str = "", user_name: str = None, employee_id: str = None, ip_address: str = "127.0.0.1"):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
            INSERT INTO audit_logs (timestamp, event_type, user_name, employee_id, details, status, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (now, event_type, user_name, employee_id, details, status, ip_address))
            conn.commit()
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")

def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

# --- Settings Operations ---

def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

# Initialize DB when module loaded
init_db()
