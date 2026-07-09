"""
run_part2.py - Part 2 (Classification) entry point.

Operates on the Part 2 database  23455702-sq26-classification.db  (a copy of the
Part 1 seeding database; the Part 1 DB is left untouched). If that file does not
exist yet it is created from 23455702-seeding.db.

Pipeline (PDF pages 22-30):
    1. migrate schema        (add PROJECT_TYPE + ISIC columns, idempotent)
    2. Step 1: project types (QDA/QD/OTHER/NOT_A from file extensions) + file counts
    3. Step 2/3 Tier 1       (classify every project from metadata -> primary/secondary class)
    4. Step 2/3 Tier 2       (classify every downloaded primary-data file from content)
    5. Step 4b: stats report (console + CSV + Markdown, incl. type x repo matrix)
    6. Step 4c: XLSX table   (deliverables/…-classification-table.xlsx)
    7. Step 4d: PDF report   (deliverables/…-classification-report.pdf)

Usage:
    python run_part2.py                 # full Part 2 pipeline
    python run_part2.py --skip-files    # skip Tier 2 file-content classification
    python run_part2.py --report-only   # regenerate stats + XLSX + PDF only
"""

import sys
import shutil
import argparse
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SEEDING_DB = PROJECT_ROOT / "23455702-seeding.db"
DB_PATH = PROJECT_ROOT / "23455702-sq26-classification.db"


def _ensure_db():
    if not DB_PATH.exists():
        if not SEEDING_DB.exists():
            sys.exit(f"[ERROR] Neither {DB_PATH.name} nor {SEEDING_DB.name} found.")
        print(f"[INIT] Creating {DB_PATH.name} from {SEEDING_DB.name} ...")
        shutil.copy2(SEEDING_DB, DB_PATH)


def _reports(db):
    from classification import report_stats, export_xlsx, report_pdf
    print("\n[report] statistics ...")
    report_stats.report(db)
    print("\n[report] XLSX deliverable ...")
    export_xlsx.export_xlsx(db)
    print("\n[report] PDF deliverable ...")
    report_pdf.build_pdf(db)


def main():
    ap = argparse.ArgumentParser(description="QDArchive Part 2 - ISIC Rev.5 classification")
    ap.add_argument("--skip-files", action="store_true",
                    help="Skip Tier 2 file-content classification")
    ap.add_argument("--report-only", action="store_true",
                    help="Only regenerate statistics + XLSX + PDF")
    args = ap.parse_args()

    _ensure_db()
    db = str(DB_PATH)

    if args.report_only:
        _reports(db)
        return

    from classification import migrate_schema, project_type, classify_projects

    print("\n[1] Migrating schema ...")
    migrate_schema.migrate(db)

    print("\n[2] Step 1 - deriving PROJECT_TYPE from file extensions ...")
    project_type.classify_project_types(db)

    print("\n[3] Tier 1 - classifying projects from metadata ...")
    classify_projects.classify_projects(db)

    if args.skip_files:
        print("\n[4] Skipping Tier 2 (--skip-files)")
    else:
        print("\n[4] Tier 2 - classifying downloaded files from content ...")
        from classification import classify_files
        classify_files.classify_files(db)

    print("\n[5-7] Reports + deliverables ...")
    _reports(db)

    # make the DB self-contained (flush WAL) before commit/upload
    import sqlite3
    c = sqlite3.connect(db)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()

    print("\n[DONE] Part 2 complete. Deliverables in ./deliverables/")


if __name__ == "__main__":
    main()
