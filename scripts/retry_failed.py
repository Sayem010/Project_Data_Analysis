"""
scripts/retry_failed.py

Re-attempts all files with status FAILED_SERVER_UNRESPONSIVE.
Run after the main pipeline if some downloads timed out.

Usage:
    python scripts/retry_failed.py [--db 23455702-seeding.db] [--data data]
"""

import argparse
import pathlib
import sys
import sqlite3
import time
import requests

# Ensure project root is on path
_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DB_NAME   = "23455702-seeding.db"
DATA_ROOT = "data"
MAX_FILE_BYTES = 500 * 1024 * 1024

HEADERS = {"User-Agent": "SQ26-Student-Scraper/1.0 (FAU Erlangen; 23455702)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

AUSSDA_BASE = "https://data.aussda.at"


def retry_aussda_file(file_id: str, dest: pathlib.Path) -> tuple[bool, int | None]:
    url = f"{AUSSDA_BASE}/api/access/datafile/{file_id}"
    try:
        r = SESSION.get(url, timeout=120, stream=True)
        if r.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            return True, 200
        return False, r.status_code
    except requests.RequestException as e:
        print(f"  [FAIL] {e}")
        return False, None


def run_retry(db_path: str, data_root: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    failed = conn.execute(
        """SELECT f.id, f.file_name, f.file_type, f.project_id,
                  p.download_repository_folder, p.download_project_folder
           FROM files f
           JOIN projects p ON f.project_id = p.id
           WHERE f.status = 'FAILED_SERVER_UNRESPONSIVE'"""
    ).fetchall()

    print(f"[RETRY] {len(failed)} files to retry")

    for row in failed:
        dest = (
            pathlib.Path(data_root)
            / row["download_repository_folder"]
            / row["download_project_folder"]
            / row["file_name"]
        )

        if dest.exists():
            conn.execute("UPDATE files SET status='SUCCEEDED' WHERE id=?", (row["id"],))
            conn.commit()
            print(f"  [ALREADY EXISTS] {row['file_name']}")
            continue

        print(f"  Retrying: {row['file_name']} …")
        ok, code = retry_aussda_file(row["file_name"], dest)

        if ok:
            new_status = "SUCCEEDED"
        elif code in (401, 403):
            new_status = "FAILED_LOGIN_REQUIRED"
        else:
            new_status = "FAILED_SERVER_UNRESPONSIVE"

        conn.execute("UPDATE files SET status=? WHERE id=?", (new_status, row["id"]))
        conn.commit()
        print(f"    → {new_status}")
        time.sleep(1)

    conn.close()
    print("[RETRY] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",   default=DB_NAME)
    parser.add_argument("--data", default=DATA_ROOT)
    args = parser.parse_args()
    run_retry(args.db, args.data)
