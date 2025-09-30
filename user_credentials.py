# user_credentials.py
import random
import string
import sqlite3
from pathlib import Path
from datetime import datetime
import csv

DB_PATH = Path("database.db")
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


def init_db():
    """Ensure candidates table exists (without wiping existing data)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL,
            issued INTEGER DEFAULT 0,
            issued_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def generate_username(next_id: int, prefix: str = "candidate") -> str:
    """Format candidate username with prefix and ID"""
    return f"{prefix}{next_id:04d}"  # candidate0001, candidate0002...


def generate_password(length: int = 8) -> str:
    """Random password with letters + digits"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_credentials(count=1, prefix="candidate", pwd_length=8):
    """Generate and save new candidate credentials"""
    init_db()  # make sure table exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    credentials = []
    for _ in range(count):
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM candidates")
        next_id = cursor.fetchone()[0] + 1
        username = generate_username(next_id, prefix)
        password = generate_password(pwd_length)

        cursor.execute(
            "INSERT INTO candidates (username, password, created_at, issued) VALUES (?, ?, ?, 0)",
            (username, password, datetime.utcnow().isoformat())
        )
        conn.commit()
        credentials.append({"username": username, "password": password, "issued": 0})

    conn.close()
    save_to_csv(credentials)

    return {
        "count": len(credentials),
        "timestamp": datetime.utcnow().isoformat(),
        "credentials": credentials
    }


def save_to_csv(credentials):
    """Append generated credentials to a CSV log file"""
    if not credentials:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"credentials_{today}.csv"

    new_file = not log_file.exists()
    with open(log_file, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["username", "password", "issued"])
        if new_file:
            writer.writeheader()
        writer.writerows(credentials)


def get_credentials(limit=100):
    """Fetch recent credentials"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, password, created_at, issued, issued_at FROM candidates ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    creds = cursor.fetchall()
    conn.close()
    return [
        {
            "username": u,
            "password": p,
            "created_at": t,
            "issued": i,
            "issued_at": ia
        }
        for u, p, t, i, ia in creds
    ]


def mark_issued(usernames):
    """Mark given usernames as issued"""
    if not usernames:
        return False
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    issued_at = datetime.utcnow().isoformat()
    cursor.executemany(
        "UPDATE candidates SET issued=1, issued_at=? WHERE username=?",
        [(issued_at, u) for u in usernames]
    )
    conn.commit()
    conn.close()
    return True


def validate_credentials(username, password):
    """Check if given credentials exist and were issued"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM candidates WHERE username=? AND password=? AND issued=1",
        (username, password)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None
