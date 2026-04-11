"""
export/export_csv.py
Exports all tables to CSV and a summary JSON report.
"""

import csv
import json
import sqlite3
import pathlib
from datetime import datetime

DB_NAME = "23455702-seeding.db"

TABLES = ["repositories", "projects", "files", "keywords", "person_role", "licenses"]


def export_all(db_path: str = DB_NAME, out_dir: str = "export_output"):
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    summary = {}

    for table in TABLES:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        out_file = pathlib.Path(out_dir) / f"{table}.csv"
        if rows:
            with open(out_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(r) for r in rows])
        else:
            out_file.touch()
        summary[table] = len(rows)
        print(f"  Exported {table}: {len(rows)} rows → {out_file}")

    # summary report
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "db": db_path,
        "row_counts": summary,
    }
    report_file = pathlib.Path(out_dir) / "summary.json"
    report_file.write_text(json.dumps(report, indent=2))
    print(f"\n  Summary → {report_file}")
    conn.close()
    return report


if __name__ == "__main__":
    export_all()
