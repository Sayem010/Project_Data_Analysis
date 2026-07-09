"""
classification/report_stats.py

Part 2 - statistics on the ISIC Rev.5 class distribution.

Produces:
  * console summary
  * export_output/classification_projects_by_division.csv
  * export_output/classification_by_section.csv
  * export_output/PART2_classification_report.md   (human-readable)

Run:
    python -m classification.report_stats
"""

import sys
import csv
import pathlib
import sqlite3
from collections import Counter

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from classification.isic_rev5 import DIVISION_TITLE, DIVISION_SECTION, SECTION_TITLE

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")
OUT_DIR = _root / "export_output"


def _fetch_counts(conn, sql):
    c = Counter()
    for code, n in conn.execute(sql):
        c[code] = n
    return c


def report(db_path: str = DEFAULT_DB) -> None:
    conn = sqlite3.connect(db_path)
    OUT_DIR.mkdir(exist_ok=True)

    total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    proj_classified = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE isic_division IS NOT NULL").fetchone()[0]
    total_files_ok = conn.execute(
        "SELECT COUNT(*) FROM files WHERE status='SUCCEEDED'").fetchone()[0]
    files_classified = conn.execute(
        "SELECT COUNT(*) FROM files WHERE isic_division IS NOT NULL").fetchone()[0]
    files_content = conn.execute(
        "SELECT COUNT(*) FROM files WHERE classification_confidence > 0").fetchone()[0]

    proj_div = _fetch_counts(conn,
        "SELECT isic_division, COUNT(*) FROM projects "
        "WHERE isic_division IS NOT NULL GROUP BY isic_division")

    # by repository
    per_repo = {}
    for rid, rname in conn.execute("SELECT id, name FROM repositories"):
        c = _fetch_counts(conn,
            f"SELECT isic_division, COUNT(*) FROM projects "
            f"WHERE repository_id={rid} AND isic_division IS NOT NULL "
            f"GROUP BY isic_division")
        per_repo[rname] = c

    # roll divisions up to sections
    sec_counts = Counter()
    for code, n in proj_div.items():
        sec_counts[DIVISION_SECTION.get(code, "?")] += n

    # ── console ──
    print("=" * 64)
    print("  PART 2 - ISIC Rev.5 CLASSIFICATION STATISTICS")
    print("=" * 64)
    pct = 100 * proj_classified / total_projects if total_projects else 0
    print(f"Projects: {proj_classified}/{total_projects} classified ({pct:.1f}%)")
    fpct = 100 * files_classified / total_files_ok if total_files_ok else 0
    print(f"Files (downloaded): {files_classified}/{total_files_ok} classified "
          f"({fpct:.1f}%); {files_content} from file content, "
          f"{files_classified - files_content} inherited")
    print("\nTop 15 divisions (projects):")
    for code, n in proj_div.most_common(15):
        p = 100 * n / proj_classified if proj_classified else 0
        print(f"  {code}  {DIVISION_TITLE.get(code,'?')[:48]:<48} {n:>6}  {p:4.1f}%")

    print("\nBy ISIC section (projects):")
    for sec, n in sec_counts.most_common():
        p = 100 * n / proj_classified if proj_classified else 0
        print(f"  {sec}  {SECTION_TITLE.get(sec,'?')[:48]:<48} {n:>6}  {p:4.1f}%")

    # ── Distributions by repository x project type (PDF page 29) ──
    print("\nDistributions by repository x project type "
          "(QDA_PROJECT / QD_PROJECT):")
    repos = conn.execute("SELECT id, name FROM repositories ORDER BY id").fetchall()
    matrix_md = ["\n## Distributions by repository x project type "
                 "(Step 3 / page 29)\n\n",
                 "| Repository | Project type | Projects | Dominant class |\n",
                 "|---|---|--:|---|\n"]
    for rid, rname in repos:
        for ptype in ("QDA_PROJECT", "QD_PROJECT"):
            n = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE repository_id=? AND type=?",
                (rid, ptype)).fetchone()[0]
            dom_row = conn.execute(
                "SELECT primary_class, COUNT(*) c FROM projects "
                "WHERE repository_id=? AND type=? AND primary_class IS NOT NULL "
                "GROUP BY primary_class ORDER BY c DESC LIMIT 1", (rid, ptype)).fetchone()
            dom = dom_row[0] if dom_row else "-"
            print(f"  repo {rid} ({rname:<6}) x {ptype:<12}: {n:>5}  dominant: {dom}")
            matrix_md.append(f"| {rid} ({rname}) | {ptype} | {n} | {dom} |\n")

    # file-level classification by parent project type (Step 3: classify each
    # primary-data file of QDA/QD projects)
    print("\nDownloaded primary-data files classified, by parent project type:")
    for ptype in ("QDA_PROJECT", "QD_PROJECT", "OTHER_PROJECT"):
        row = conn.execute(
            "SELECT COUNT(*) FROM files f JOIN projects p ON p.id=f.project_id "
            "WHERE p.type=? AND f.status='SUCCEEDED' AND f.isic_division IS NOT NULL",
            (ptype,)).fetchone()[0]
        print(f"  {ptype:<14}: {row} files classified")

    # ── CSV: by division ──
    with open(OUT_DIR / "classification_projects_by_division.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["isic_division", "division_title", "section",
                    "section_title", "project_count", "pct_of_classified"])
        for code, n in sorted(proj_div.items(), key=lambda x: -x[1]):
            sec = DIVISION_SECTION.get(code, "")
            p = 100 * n / proj_classified if proj_classified else 0
            w.writerow([code, DIVISION_TITLE.get(code, ""), sec,
                        SECTION_TITLE.get(sec, ""), n, f"{p:.2f}"])

    # ── CSV: by section ──
    with open(OUT_DIR / "classification_by_section.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["section", "section_title", "project_count", "pct_of_classified"])
        for sec, n in sorted(sec_counts.items(), key=lambda x: -x[1]):
            p = 100 * n / proj_classified if proj_classified else 0
            w.writerow([sec, SECTION_TITLE.get(sec, ""), n, f"{p:.2f}"])

    # ── Markdown report ──
    md = []
    md.append("# Part 2 - ISIC Rev.5 Classification Report\n")
    md.append(f"**Database:** `23455702-seeding.db`  \n")
    md.append(f"**Classifier:** local rule-based (keyword scoring), division level\n")
    md.append("\n## Coverage\n")
    md.append(f"- Projects classified: **{proj_classified} / {total_projects}** ({pct:.1f}%)\n")
    md.append(f"- Downloaded files classified: **{files_classified} / {total_files_ok}** "
              f"({fpct:.1f}%) - {files_content} from file content, "
              f"{files_classified - files_content} inherited from project metadata\n")
    md.append("\n## Projects by ISIC section\n\n")
    md.append("| Section | Title | Projects | % |\n|---|---|--:|--:|\n")
    for sec, n in sec_counts.most_common():
        p = 100 * n / proj_classified if proj_classified else 0
        md.append(f"| {sec} | {SECTION_TITLE.get(sec,'')} | {n} | {p:.1f}% |\n")
    md.append("\n## Top 20 divisions (projects)\n\n")
    md.append("| Division | Title | Projects | % |\n|---|---|--:|--:|\n")
    for code, n in proj_div.most_common(20):
        p = 100 * n / proj_classified if proj_classified else 0
        md.append(f"| {code} | {DIVISION_TITLE.get(code,'')} | {n} | {p:.1f}% |\n")
    md.extend(matrix_md)
    md.append("\n## Divisions by repository (top 10 each)\n")
    for rname, c in per_repo.items():
        md.append(f"\n### {rname}\n\n| Division | Title | Projects |\n|---|---|--:|\n")
        for code, n in c.most_common(10):
            md.append(f"| {code} | {DIVISION_TITLE.get(code,'')} | {n} |\n")
    (OUT_DIR / "PART2_classification_report.md").write_text("".join(md), encoding="utf-8")

    conn.close()
    print(f"\n[REPORT] Wrote CSVs + PART2_classification_report.md to {OUT_DIR}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    report(db)
