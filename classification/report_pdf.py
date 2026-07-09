"""
classification/report_pdf.py

Part 2 - Step 4d: build the PDF results report (submitted on moo.uni1.de).

Structure (per PDF page 30), for each repository:
    a. Histogram of primary classes identified
         - full ISIC class name as the bin label
         - the count printed on each bar
         - vector graphics (matplotlib PDF backend => zoomable vectors)
    b. Rank-ordered table of the top 20 classes (most common first) with counts
    c. Comments on the findings
Plus a project-type summary per repository (covers the Step 4b statistics:
which project types were found, how many, and the dominant class).

Output: deliverables/23455702-sq26-classification-report.pdf

Run:
    python -m classification.report_pdf
"""

import sys
import textwrap
import pathlib
import sqlite3
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")
OUT_DIR = _root / "deliverables"
STUDENT_ID = "23455702"

TYPES = ["QDA_PROJECT", "QD_PROJECT", "OTHER_PROJECT", "NOT_A_PROJECT"]


def _fetchall(conn, sql, args=()):
    return conn.execute(sql, args).fetchall()


def _title_page(pdf, total, type_counts):
    fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
    fig.text(0.5, 0.80, "Seeding QDArchive - Part 2", ha="center", size=22, weight="bold")
    fig.text(0.5, 0.73, "ISIC Rev. 5 Classification Results", ha="center", size=16)
    fig.text(0.5, 0.66, f"Student {STUDENT_ID}", ha="center", size=12)
    lines = [
        "Method: local rule-based classifier (keyword scoring), ISIC Rev. 5 division level.",
        "Two tiers of source data: (1) project metadata, (2) primary-data file content.",
        "",
        f"Total projects: {total}",
        "Project types (all repositories):",
    ]
    for t in TYPES:
        lines.append(f"    {t:<14} {type_counts.get(t, 0)}")
    fig.text(0.12, 0.52, "\n".join(lines), ha="left", va="top", size=12, family="monospace")
    pdf.savefig(fig)
    plt.close(fig)


def _repo_type_summary_page(pdf, repo_name, rid, conn):
    tcounts = Counter()
    for t, n in _fetchall(conn,
            "SELECT type, COUNT(*) FROM projects WHERE repository_id=? GROUP BY type", (rid,)):
        tcounts[t] = n
    total = sum(tcounts.values())

    # dominant class overall for this repo
    dom = _fetchall(conn,
        "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? "
        "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC LIMIT 1", (rid,))
    dominant = dom[0][0] if dom else "(none)"

    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.5, 0.90, f"Repository {rid}: {repo_name.upper()}",
             ha="center", size=18, weight="bold")
    lines = [
        f"Total projects in repository: {total}",
        "",
        "Project types found:",
    ]
    for t in TYPES:
        n = tcounts.get(t, 0)
        pct = 100 * n / total if total else 0
        lines.append(f"    {t:<14} {n:>6}   ({pct:4.1f}%)")
    lines += ["", f"Dominant primary class: {dominant}"]
    fig.text(0.12, 0.78, "\n".join(lines), ha="left", va="top", size=13, family="monospace")
    pdf.savefig(fig)
    plt.close(fig)


def _histogram_pages(pdf, repo_name, rid, conn):
    rows = _fetchall(conn,
        "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? "
        "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC", (rid,))
    if not rows:
        return
    labels = [textwrap.fill(r[0], 46) for r in rows]
    counts = [r[1] for r in rows]

    n = len(rows)
    height = max(5.0, 0.34 * n + 1.5)
    fig, ax = plt.subplots(figsize=(11.69, height))
    ypos = range(n)
    ax.barh(list(ypos), counts, color="#305496")
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()  # most common on top
    ax.set_xlabel("Number of projects (primary class)")
    ax.set_title(f"Repository {rid} ({repo_name.upper()}): "
                 f"histogram of primary classes ({n} classes)", weight="bold")
    xmax = max(counts)
    for i, v in zip(ypos, counts):
        ax.text(v + xmax * 0.01, i, str(v), va="center", fontsize=7)
    ax.set_xlim(0, xmax * 1.08)
    fig.subplots_adjust(left=0.42, right=0.97, top=1 - 0.6 / height, bottom=0.5 / height)
    pdf.savefig(fig)
    plt.close(fig)


def _top20_table_page(pdf, repo_name, rid, conn):
    rows = _fetchall(conn,
        "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? "
        "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC LIMIT 20", (rid,))
    if not rows:
        return
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.suptitle(f"Repository {rid} ({repo_name.upper()}): top {len(rows)} primary classes",
                 size=15, weight="bold", y=0.96)
    ax = fig.add_axes([0.06, 0.05, 0.88, 0.85])
    ax.axis("off")
    cell_text = [[str(i + 1), textwrap.fill(c, 70), str(n)]
                 for i, (c, n) in enumerate(rows)]
    table = ax.table(cellText=cell_text,
                     colLabels=["Rank", "ISIC class (division)", "Count"],
                     colWidths=[0.08, 0.78, 0.12], cellLoc="left", loc="upper center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#305496")
            cell.set_text_props(color="white", weight="bold")
    pdf.savefig(fig)
    plt.close(fig)


def _comments_page(pdf, repo_name, rid, conn):
    rows = _fetchall(conn,
        "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? "
        "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC", (rid,))
    total_cls = sum(r[1] for r in rows)
    unclassified = _fetchall(conn,
        "SELECT COUNT(*) FROM projects WHERE repository_id=? AND primary_class IS NULL", (rid,))[0][0]
    top3 = ", ".join(f"{c} ({n})" for c, n in rows[:3])

    if repo_name.lower() == "ukds":
        specific = (
            "All UKDS files sit behind a login wall, so no primary-data file content could\n"
            "be read; every UKDS project is typed OTHER_PROJECT from the single (container)\n"
            "file recorded, and classified from metadata only. Classes therefore reflect the\n"
            "study topics described in the catalogue rather than file content."
        )
    else:
        specific = (
            "AUSSDA projects with primary-data files (PDF/RTF/DOCX) are typed QD_PROJECT and\n"
            "additionally classified from file content; projects with only tabular/statistical\n"
            "files are OTHER_PROJECT, and those with no files NOT_A_PROJECT. Many records carry\n"
            "only short German-language topic labels, which the English keyword classifier\n"
            "cannot match - the main source of unclassified projects here."
        )

    text = (
        f"Comments - Repository {rid} ({repo_name.upper()})\n\n"
        f"- Classified projects: {total_cls}; unclassified: {unclassified}.\n"
        f"- Most common primary classes: {top3}.\n"
        f"- Distinct primary classes identified: {len(rows)}.\n\n"
        f"{specific}\n\n"
        "General note: ISIC classifies economic activities, whereas qualitative studies\n"
        "describe research subjects. The mapping assigns the closest activity (e.g. labour\n"
        "research -> 78 Employment activities), which is an approximation inherent to applying\n"
        "an industrial taxonomy to research metadata."
    )
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.08, 0.90, text, ha="left", va="top", size=11, family="monospace")
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(db_path: str = DEFAULT_DB) -> pathlib.Path:
    OUT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(db_path)

    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    type_counts = Counter()
    for t, n in conn.execute("SELECT type, COUNT(*) FROM projects GROUP BY type"):
        type_counts[t] = n
    repos = conn.execute("SELECT id, name FROM repositories ORDER BY id").fetchall()

    out = OUT_DIR / f"{STUDENT_ID}-sq26-classification-report.pdf"
    with PdfPages(out) as pdf:
        _title_page(pdf, total, type_counts)
        for rid, rname in repos:
            _repo_type_summary_page(pdf, rname, rid, conn)
            _histogram_pages(pdf, rname, rid, conn)
            _top20_table_page(pdf, rname, rid, conn)
            _comments_page(pdf, rname, rid, conn)

    conn.close()
    print(f"[PDF] Wrote report -> {out}")
    return out


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    build_pdf(db)
