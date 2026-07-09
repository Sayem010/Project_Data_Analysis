"""
classification/migrate_schema.py

Part 2 schema enhancement.

The professor's requirement for Part 2 is:
  * "Each QDA_PROJECT should have a class"
  * "Each primary data file in a project should also have a class"

We therefore add ISIC Rev.5 division columns to the existing PROJECTS and FILES
tables. This is done with idempotent `ALTER TABLE ... ADD COLUMN` calls so that:
  * Part 1 tables and their CHECK constraints are left completely intact
  * the professor's Part 1 grading script still passes (only extra columns added)
  * re-running the migration is safe (columns are only added if missing)

Project-level columns (PROJECTS):
  isic_division            2-digit ISIC Rev.5 division code, e.g. '86'  (NULL = unclassified)
  isic_division_label      human-readable 'NN - Title'
  classification_source    TIER1_METADATA | TIER2_PRIMARY_DATA | COMBINED
  classification_confidence  rule-based match score (REAL)

File-level columns (FILES):
  isic_division            division code assigned to that file's primary-data content
  isic_division_label      human-readable label
  classification_confidence  rule-based match score (REAL)

Run:
    python -m classification.migrate_schema
"""

import sys
import pathlib
import sqlite3

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")

# table -> list of (column_name, column_definition)
PART2_COLUMNS = {
    "projects": [
        # Step 1 - PROJECT_TYPE + deliverable columns (PDF pages 22-23, 28)
        ("type", "TEXT CHECK(type IN "
                 "('QDA_PROJECT','QD_PROJECT','OTHER_PROJECT','NOT_A_PROJECT'))"),
        ("no_project_files", "INTEGER"),
        ("primary_class", "TEXT"),      # full ISIC division label, most likely class
        ("secondary_class", "TEXT"),    # full ISIC division label, 2nd class (if any)
        # Step 2 - ISIC division classification internals
        ("isic_division", "TEXT"),
        ("isic_division_label", "TEXT"),
        ("classification_source", "TEXT"),
        ("classification_confidence", "REAL"),
    ],
    "files": [
        ("isic_division", "TEXT"),
        ("isic_division_label", "TEXT"),
        ("classification_confidence", "REAL"),
    ],
}


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(db_path: str = DEFAULT_DB) -> None:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            for table, columns in PART2_COLUMNS.items():
                have = _existing_columns(conn, table)
                for name, coltype in columns:
                    if name in have:
                        print(f"  [SKIP] {table}.{name} already exists")
                        continue
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
                    print(f"  [ADD]  {table}.{name} {coltype}")
    finally:
        conn.close()
    print(f"[MIGRATE] Part 2 columns ready -> {db_path}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    migrate(db)
