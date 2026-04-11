"""
main.py — QDArchive Seeding Pipeline
Student ID: 23455702

Run:
    python main.py                  # run everything
    python main.py --repo aussda    # only AUSSDA
    python main.py --repo ukds      # only UK Data Service
    python main.py --export-only    # just export CSVs from existing DB
"""

import argparse
import sys
import pathlib

# Ensure the project root is always on sys.path so subpackages
# (db, scrapers, export, scripts) are importable regardless of
# which directory Python was launched from.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH   = str(PROJECT_ROOT / "23455702-seeding.db")
DATA_ROOT = str(PROJECT_ROOT / "data")


def setup():
    """Initialise DB and seed repositories table."""
    import db.database as dbm
    dbm.init_db(DB_PATH)
    dbm.seed_repositories(DB_PATH)
    pathlib.Path(DATA_ROOT).mkdir(exist_ok=True)


def run_aussda():
    from scrapers.aussda_scraper import scrape_aussda
    print("\n" + "="*60)
    print("  AUSSDA — Austrian Social Science Data Archive")
    print("="*60)
    scrape_aussda(data_root=DATA_ROOT, db_path=DB_PATH)


def run_ukds():
    from scrapers.ukds_scraper import scrape_ukds
    print("\n" + "="*60)
    print("  UK Data Service")
    print("="*60)
    scrape_ukds(data_root=DATA_ROOT, db_path=DB_PATH)


def run_export():
    import sqlite3, csv
    out_dir = PROJECT_ROOT / "export_output"
    out_dir.mkdir(exist_ok=True)
    print("\n" + "="*60)
    print("  Exporting to CSV")
    print("="*60)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = ["repositories","projects","files","keywords","person_role","licenses"]
    counts = {}
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        out_file = out_dir / f"{table}.csv"
        if rows:
            with open(out_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows([dict(r) for r in rows])
        counts[table] = len(rows)
        print(f"  {table}: {len(rows)} rows")
    conn.close()
    print(f"\n  Row counts: {counts}")

def main():
    parser = argparse.ArgumentParser(description="QDArchive Seeding Pipeline")
    parser.add_argument("--repo",        choices=["aussda", "ukds"], help="Run only one repo scraper")
    parser.add_argument("--export-only", action="store_true",        help="Skip scraping, just export")
    args = parser.parse_args()

    setup()

    if args.export_only:
        run_export()
        return

    if args.repo == "aussda":
        run_aussda()
    elif args.repo == "ukds":
        run_ukds()
    else:
        run_aussda()
        run_ukds()

    run_export()
    print(f"\n[DONE] Database: {DB_PATH}")
    print(f"       Files:    {DATA_ROOT}/")
    print(f"       CSVs:     export_output/")


if __name__ == "__main__":
    main()
