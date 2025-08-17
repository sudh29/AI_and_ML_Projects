import os
import sqlite3
import json

DB_PATH = os.environ.get("QUOTE_DB_PATH", "quotes_history.db")


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT NOT NULL,
            author TEXT,
            caption TEXT,
            platforms TEXT,
            date_posted TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def quote_exists(quote_text: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM posts WHERE quote = ? LIMIT 1", (quote_text,))
    found = cur.fetchone() is not None
    conn.close()
    return found


def log_post(quote_text: str, author: str, caption: str, platforms: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO posts (quote, author, caption, platforms, date_posted) VALUES (?, ?, ?, ?, datetime("now"))',
        (quote_text, author, caption, json.dumps(platforms)),
    )
    conn.commit()
    conn.close()
