import sqlite3
import os
import threading

# ✅ Fix: Absolute path for reliability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "memory.db")

# ✅ Global connection with thread lock (SINGLETON)
_connection = None
_connection_lock = threading.Lock()
_DB_INITIALIZED = False


def get_connection():
    """Get thread-safe database connection (Singleton pattern)"""
    global _connection
    if _connection is None:
        with _connection_lock:
            if _connection is None:
                os.makedirs(SCRIPT_DIR, exist_ok=True)
                _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
                _connection.row_factory = sqlite3.Row
    return _connection


def init_db():
    """Initialize database tables only once"""
    global _DB_INITIALIZED
    
    # Agar pehle se initialize hai to skip karo
    if _DB_INITIALIZED:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # MEMORY TABLE - DROP ONLY IF NEEDED (REMOVE THIS IF YOU WANT TO KEEP DATA)
    # cursor.execute("DROP TABLE IF EXISTS memory")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            source_agent TEXT,
            content_type TEXT,
            confidence_score REAL DEFAULT 0.5,
            created_at TEXT
        )
    """)

    # INDEX
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_content ON memory(content)
    """)

    # IMAGE MEMORY TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT UNIQUE,
            image_path TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    _DB_INITIALIZED = True
    print(f"✅ DB Ready: {DB_PATH}")


# Call init_db when module loads
init_db()