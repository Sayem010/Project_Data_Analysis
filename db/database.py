"""
db/database.py
Database initialisation and all insert helpers.
Primary rule: store data exactly as received; no normalisation.
"""

import sqlite3
import pathlib

DB_NAME = "23455702-seeding.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_NAME) -> None:
    """Create all tables (idempotent)."""
    conn = get_connection(db_path)
    with conn:
        conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    print(f"[DB] Initialised → {db_path}")


# ── seed repos ────────────────────────────────────────────────────────────────

REPOSITORIES = [
    {"id": 1, "name": "ukds",   "url": "https://ukdataservice.ac.uk"},
    {"id": 2, "name": "aussda", "url": "https://aussda.at/en/"},
]


def seed_repositories(db_path: str = DB_NAME) -> None:
    conn = get_connection(db_path)
    with conn:
        for r in REPOSITORIES:
            conn.execute(
                """INSERT OR IGNORE INTO repositories (id, name, url)
                   VALUES (:id, :name, :url)""",
                r,
            )
    conn.close()


# ── project ────────────────────────────────────────────────────────────────────

def insert_project(conn: sqlite3.Connection, p: dict) -> int:
    cur = conn.execute(
        """INSERT INTO projects (
               query_string, repository_id, repository_url, project_url,
               version, title, description, language, doi,
               upload_date, download_date,
               download_repository_folder, download_project_folder,
               download_version_folder, download_method
           ) VALUES (
               :query_string, :repository_id, :repository_url, :project_url,
               :version, :title, :description, :language, :doi,
               :upload_date, :download_date,
               :download_repository_folder, :download_project_folder,
               :download_version_folder, :download_method
           )""",
        p,
    )
    return cur.lastrowid


def project_exists(conn: sqlite3.Connection, project_url: str) -> bool:
    row = conn.execute(
        "SELECT id FROM projects WHERE project_url = ?", (project_url,)
    ).fetchone()
    return row is not None


# ── files ──────────────────────────────────────────────────────────────────────

def insert_file(conn: sqlite3.Connection, f: dict) -> None:
    conn.execute(
        """INSERT INTO files (project_id, file_name, file_type, status)
           VALUES (:project_id, :file_name, :file_type, :status)""",
        f,
    )


# ── keywords ───────────────────────────────────────────────────────────────────

def insert_keywords(conn: sqlite3.Connection, project_id: int, keywords: list[str]) -> None:
    for kw in keywords:
        if kw and kw.strip():
            conn.execute(
                "INSERT INTO keywords (project_id, keyword) VALUES (?, ?)",
                (project_id, kw.strip()),
            )


# ── person_role ────────────────────────────────────────────────────────────────

def insert_persons(conn: sqlite3.Connection, project_id: int, persons: list[dict]) -> None:
    for p in persons:
        conn.execute(
            """INSERT INTO person_role (project_id, name, role)
               VALUES (?, ?, ?)""",
            (project_id, p["name"], p["role"]),
        )


# ── licenses ───────────────────────────────────────────────────────────────────

def insert_license(conn: sqlite3.Connection, project_id: int, license_str: str) -> None:
    if license_str:
        conn.execute(
            "INSERT INTO licenses (project_id, license) VALUES (?, ?)",
            (project_id, license_str),
        )
