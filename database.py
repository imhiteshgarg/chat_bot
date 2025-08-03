import sqlite3
import uuid
import logging
from typing import List
from contextlib import contextmanager

# These should match your main.py constants
DATABASE_NAME = "chat_history.db"
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup"""
    conn = sqlite3.connect(
        DATABASE_NAME,
        timeout=30.0,  # 30 second timeout
    )
    
    # Enable optimizations for better performance
    conn.execute("PRAGMA journal_mode=WAL")       # Better concurrency
    conn.execute("PRAGMA synchronous=NORMAL")     # Good balance of safety/speed
    conn.execute("PRAGMA cache_size=1000")        # More memory for caching
    conn.execute("PRAGMA temp_store=MEMORY")      # Store temp tables in RAM
    
    try:
        yield conn
        conn.commit()  # Auto-commit on successful completion
    except Exception as e:
        conn.rollback()  # Auto-rollback on error
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        conn.close()  # Always close the connection

def init_database():
    """Initialize the SQLite database and create tables if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')
        
        logger.info("Database initialized successfully")

def create_session() -> str:
    """Create a new chat session and return session ID."""
    session_id = str(uuid.uuid4())
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id) VALUES (?)",
            (session_id,)
        )
    
    logger.info(f"Created new session: {session_id}")
    return session_id

def save_message(session_id: str, role: str, content: str):
    """Save a message to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        
        # Update session last activity
        cursor.execute(
            "UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
    
    logger.debug(f"Saved {role} message to session {session_id}")

def get_conversation_history(session_id: str) -> List[dict]:
    """Retrieve conversation history for a session."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "timestamp": row[2]
            })
    
    return messages

def get_recent_sessions(limit: int = 10) -> List[dict]:
    """Get recent chat sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.created_at, s.last_activity, 
                   (SELECT content FROM messages WHERE session_id = s.id AND role = 'user' ORDER BY timestamp LIMIT 1) as first_message
            FROM sessions s
            ORDER BY s.last_activity DESC
            LIMIT ?
        ''', (limit,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row[0],
                "created_at": row[1],
                "last_activity": row[2],
                "first_message": row[3] or "New Chat"
            })
    
    return sessions
