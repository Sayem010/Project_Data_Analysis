import sqlite3
from datetime import datetime

DB_PATH = "data/metadata/qdarchive.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        timestamp TEXT,
        local_dir TEXT,
        filename TEXT,
        source TEXT,
        license TEXT,
        uploader_name TEXT,
        uploader_email TEXT
    )
    """)

    conn.commit()
    conn.close()


def insert_record(record):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO datasets
    (url, timestamp, local_dir, filename, source, license, uploader_name, uploader_email)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["url"],
        datetime.now().isoformat(),
        record["local_dir"],
        record["filename"],
        record["source"],
        record["license"],
        record["uploader_name"],
        record["uploader_email"]
    ))

    conn.commit()
    conn.close()
    