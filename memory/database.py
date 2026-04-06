import sqlite3
import os

# ✅ Fix: Absolute path for reliability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "memory.db")

# ✅ Global flag to track if DB is already initialized
_DB_INITIALIZED = False

def get_connection():
    # ✅ Ensure dir exists
    os.makedirs(SCRIPT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    global _DB_INITIALIZED
    
    # ✅ Agar pehle se initialize hai to skip karo
    if _DB_INITIALIZED:
        return
    
    # ✅ Agar database file already exist karti hai to sirf verify karo
    if os.path.exists(DB_PATH):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM memory LIMIT 1")
            conn.close()
            # Database already exists and is valid
            _DB_INITIALIZED = True
            return
        except:
            # Database file exists but might be corrupted, recreate
            pass
    
    conn = get_connection()
    cursor = conn.cursor()

    # MEMORY TABLE (same)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            source_agent TEXT,
            content_type TEXT,
            confidence_score REAL DEFAULT 0.5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # INDEX (same)
# memory/database.py

import sqlite3
import os

def get_connection():

    # ✅ FIXED ABSOLUTE PATH
    DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


    cursor.execute("DROP TABLE IF EXISTS memory")

    cursor.execute("""
        CREATE TABLE memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            source_agent TEXT,
            content_type TEXT,
            confidence_score REAL DEFAULT 0.5,
            created_at TEXT
        )
    """)

    # ✅ INDEX (NOW CORRECTLY OUTSIDE STRING)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_content
        ON memory(content)
    """)

    # IMAGE MEMORY TABLE (same)
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
    conn.close()
    
    # ✅ Sirf ek line print karo, count mat dikhao
    print(f"✅ DB Ready: {DB_PATH}")
    
    # ❌ DELETE KARO YEH LINES - time waste hai
    # conn = get_connection()
    # cursor = conn.cursor()
    # count = cursor.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    # print(f"📊 Current DB Rows: {count}")
    # conn.close()
    
    _DB_INITIALIZED = True
    return conn
