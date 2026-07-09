"""
classification/report_pdf.py

Part 2 - Step 4d: build the PDF results report (submitted on moo.uni1.de).

A polished, presentation-grade A4 report. Structure:

    * Cover page
    * Executive summary (overall coverage + repository x project-type matrix)
    * Per repository:
        - Primary-class distribution chart (top 20, full ISIC names, counts)
        - Rank-ordered top-20 table (count + share)
        - Commentary on the findings

All graphics are matplotlib vector output (zoomable), fonts embedded as
TrueType so the PDF is crisp at any zoom.

Run:
    python -m classification.report_pdf
"""

import sys
import textwrap
import pathlib
import sqlite3
import datetime
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams.update({
    "pdf.fonttype": 42,          # embed TrueType (selectable, crisp)
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial"],
    "axes.edgecolor": "#B8BFC9",
})

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")
OUT_DIR = _root / "deliverables"

# ── identity / palette ────────────────────────────────────────────────────────
STUDENT_ID = "23455702"
AUTHOR = "Sayem Bin Sarwar Chowdhury"
COURSE = "Applied Software Engineering Project (10 ECTS)"
INSTITUTION = "Friedrich-Alexander-Universitat Erlangen-Nurnberg (FAU)"
SUPERVISOR = "Prof. Dr. Dirk Riehle"

NAVY = "#1F3864"
BLUE = "#2E75B6"
LIGHT = "#DCE6F1"
ROW = "#F2F6FB"
INK = "#1A1A1A"
MUTED = "#5B6572"

A4 = (8.27, 11.69)          # portrait inches
TYPES = ["QDA_PROJECT", "QD_PROJECT", "OTHER_PROJECT", "NOT_A_PROJECT"]


class Report:
    def __init__(self, pdf):
        self.pdf = pdf
        self.page = 0

    # ---- page scaffolding -----------------------------------------------------
    def _frame(self, fig, title, eyebrow="SEEDING QDARCHIVE  ·  PART 2"):
        """Header band + footer, returns nothing (draws on fig)."""
        fig.add_artist(Rectangle((0, 0.925), 1, 0.075, transform=fig.transFigure,
                                 color=NAVY, zorder=0))
        fig.text(0.06, 0.972, eyebrow, color="#AFC3E6", size=8.5,
                 weight="bold", va="center")
        fig.text(0.06, 0.947, title, color="white", size=15,
                 weight="bold", va="center")
        # footer
        fig.add_artist(Rectangle((0.06, 0.045), 0.88, 0.0016,
                                 transform=fig.transFigure, color="#C7CFDA", zorder=0))
        fig.text(0.06, 0.03, f"Student {STUDENT_ID}  ·  ISIC Rev. 5 classification report",
                 color=MUTED, size=7.5, va="center")
        self.page += 1
        fig.text(0.94, 0.03, f"Page {self.page}", color=MUTED, size=7.5,
                 va="center", ha="right")

    def _new(self, title, eyebrow="SEEDING QDARCHIVE  ·  PART 2"):
        fig = plt.figure(figsize=A4)
        fig.patch.set_facecolor("white")
        self._frame(fig, title, eyebrow)
        return fig

    def _save(self, fig):
        self.pdf.savefig(fig, facecolor="white")
        plt.close(fig)

    # ---- cover ----------------------------------------------------------------
    def cover(self, total, coverage, files_cov, n_repos, n_classes):
        fig = plt.figure(figsize=A4)
        fig.patch.set_facecolor("white")
        # top block
        fig.add_artist(Rectangle((0, 0.68), 1, 0.32, transform=fig.transFigure,
                                 color=NAVY, zorder=0))
        fig.add_artist(Rectangle((0, 0.665), 1, 0.015, transform=fig.transFigure,
                                 color=BLUE, zorder=0))
        fig.text(0.08, 0.90, "SEEDING QDARCHIVE", color="#AFC3E6", size=13,
                 weight="bold")
        fig.text(0.08, 0.845, "Part 2 - Data Classification", color="white",
                 size=30, weight="bold")
        fig.text(0.08, 0.795, "ISIC Rev. 5 taxonomy  ·  division level", color="#DCE6F1",
                 size=15)
        fig.text(0.08, 0.725, "Results & Statistics Report", color="white",
                 size=13, style="italic")

        # authorship block
        info = [
            ("Author", AUTHOR),
            ("Student ID", STUDENT_ID),
            ("Course", COURSE),
            ("Supervisor", SUPERVISOR),
            ("Institution", INSTITUTION),
            ("Date", datetime.date.today().isoformat()),
        ]
        y = 0.60
        for k, v in info:
            fig.text(0.08, y, k.upper(), color=MUTED, size=8.5, weight="bold")
            fig.text(0.30, y, v, color=INK, size=11)
            y -= 0.038

        # KPI strip
        kpis = [
            (f"{total:,}", "projects"),
            (f"{coverage:.1f}%", "projects classified"),
            (f"{files_cov:.1f}%", "files classified"),
            (str(n_classes), "ISIC divisions used"),
        ]
        x = 0.08
        w = 0.21
        for val, lab in kpis:
            fig.add_artist(Rectangle((x, 0.20), w - 0.02, 0.11,
                                     transform=fig.transFigure, color=LIGHT, zorder=0))
            fig.text(x + (w - 0.02) / 2, 0.265, val, color=NAVY, size=17,
                     weight="bold", ha="center")
            fig.text(x + (w - 0.02) / 2, 0.225, lab, color=MUTED, size=8.2,
                     ha="center")
            x += w
        fig.text(0.08, 0.13,
                 "Method: local, deterministic rule-based classifier (keyword scoring) applied to two tiers of\n"
                 "source data - (1) project metadata and (2) primary-data file content - across "
                 f"{n_repos} repositories.",
                 color=MUTED, size=9.5)
        self.page += 1
        self._save(fig)

    # ---- executive summary ----------------------------------------------------
    def summary(self, conn, total, classified, files_ok, files_cls, sec_rows, matrix):
        fig = self._new("Executive summary")
        y = 0.87

        fig.text(0.06, y, "Coverage", color=NAVY, size=12, weight="bold")
        y -= 0.035
        cov = 100 * classified / total if total else 0
        fcov = 100 * files_cls / files_ok if files_ok else 0
        for line in [
            f"Projects classified into an ISIC division:  {classified:,} / {total:,}  ({cov:.1f}%)",
            f"Downloaded primary-data files classified:   {files_cls:,} / {files_ok:,}  ({fcov:.1f}%)",
        ]:
            fig.text(0.08, y, line, color=INK, size=10.5)
            y -= 0.03

        # top sections chart
        y -= 0.02
        fig.text(0.06, y, "Distribution across ISIC sections (all repositories)",
                 color=NAVY, size=12, weight="bold")
        ax = fig.add_axes([0.30, 0.40, 0.63, 0.20])
        labels = [r[0] for r in sec_rows][:8][::-1]
        vals = [r[1] for r in sec_rows][:8][::-1]
        wrapped = [textwrap.fill(l, 34) for l in labels]
        bars = ax.barh(range(len(vals)), vals, color=BLUE, height=0.68)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels(wrapped, fontsize=7.5)
        ax.tick_params(length=0)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.set_xlim(0, max(vals) * 1.12)
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.01, i, f"{v:,}", va="center", size=7.5, color=INK)
        ax.set_xlabel("projects", size=8, color=MUTED)

        # matrix table
        fig.text(0.06, 0.34, "Distributions by repository x project type (Step 3)",
                 color=NAVY, size=12, weight="bold")
        ax2 = fig.add_axes([0.06, 0.09, 0.88, 0.22])
        ax2.axis("off")
        header = ["Repository", "Project type", "Projects", "Dominant primary class"]
        cells = [[a, b, f"{c:,}", textwrap.fill(d, 44)] for a, b, c, d in matrix]
        tbl = ax2.table(cellText=cells, colLabels=header,
                        colWidths=[0.17, 0.16, 0.11, 0.56],
                        cellLoc="left", loc="upper center")
        _style_table(tbl, len(cells))
        self._save(fig)

    # ---- repository chart -----------------------------------------------------
    def repo_chart(self, repo_name, rid, rows, total_repo, tcounts, classified_repo):
        n_distinct = len(rows)
        rows = rows[:20]
        fig = self._new(f"Repository {rid}: {repo_name.upper()}  -  primary-class distribution")

        # stat strip
        cov = 100 * classified_repo / total_repo if total_repo else 0
        chips = [
            (f"{total_repo:,}", "projects"),
            (f"{tcounts.get('QD_PROJECT',0):,}", "QD_PROJECT"),
            (f"{tcounts.get('OTHER_PROJECT',0):,}", "OTHER_PROJECT"),
            (f"{tcounts.get('NOT_A_PROJECT',0):,}", "NOT_A_PROJECT"),
            (f"{cov:.0f}%", "classified"),
        ]
        x = 0.06
        w = 0.176
        for val, lab in chips:
            fig.add_artist(Rectangle((x, 0.845), w - 0.012, 0.055,
                                     transform=fig.transFigure, color=LIGHT, zorder=0))
            fig.text(x + (w - 0.012) / 2, 0.878, val, color=NAVY, size=12.5,
                     weight="bold", ha="center")
            fig.text(x + (w - 0.012) / 2, 0.856, lab, color=MUTED, size=7, ha="center")
            x += w

        labels = [textwrap.fill(r[0], 40) for r in rows][::-1]
        vals = [r[1] for r in rows][::-1]
        ax = fig.add_axes([0.42, 0.10, 0.53, 0.70])
        ax.barh(range(len(vals)), vals, color=BLUE, height=0.72)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels(labels, fontsize=7.3)
        ax.tick_params(length=0)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.xaxis.grid(True, color="#E4E9F0", linewidth=0.8)
        ax.set_axisbelow(True)
        xmax = max(vals) if vals else 1
        ax.set_xlim(0, xmax * 1.10)
        for i, v in enumerate(vals):
            ax.text(v + xmax * 0.012, i, f"{v:,}", va="center", size=7.3,
                    color=INK, weight="bold")
        ax.set_xlabel("number of projects", size=9, color=MUTED)
        fig.text(0.42, 0.83, f"Top {len(rows)} of {n_distinct} ISIC divisions identified",
                 color=MUTED, size=8.5, style="italic")
        self._save(fig)

    # ---- repository table + comments -----------------------------------------
    def repo_table(self, repo_name, rid, rows, classified_repo, comment):
        fig = self._new(f"Repository {rid}: {repo_name.upper()}  -  ranked classes & commentary")
        top = rows[:20]
        ax = fig.add_axes([0.06, 0.40, 0.88, 0.47])
        ax.axis("off")
        cells = []
        for i, (cls, n) in enumerate(top, 1):
            pct = 100 * n / classified_repo if classified_repo else 0
            cells.append([str(i), textwrap.fill(cls, 62), f"{n:,}", f"{pct:.1f}%"])
        tbl = ax.table(cellText=cells,
                       colLabels=["#", "ISIC class (division)", "Count", "Share"],
                       colWidths=[0.06, 0.72, 0.11, 0.11],
                       cellLoc="left", loc="upper center")
        _style_table(tbl, len(cells))

        fig.text(0.06, 0.34, "Commentary", color=NAVY, size=12, weight="bold")
        fig.text(0.06, 0.31, comment, color=INK, size=9.6, va="top",
                 linespacing=1.5, wrap=True)
        self._save(fig)


def _style_table(tbl, n_body):
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.2)
    tbl.scale(1, 1.42)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#D4DBE5")
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color="white", weight="bold")
        elif r % 2 == 0:
            cell.set_facecolor(ROW)
        else:
            cell.set_facecolor("white")


def _commentary(repo_name, rows, classified, unclassified, tcounts):
    top3 = "; ".join(f"{c} ({n:,})" for c, n in rows[:3])
    if repo_name.lower() == "ukds":
        specific = (
            "All UK Data Service files require registration and login, so no primary-data file "
            "content could be read. Every UKDS project is therefore typed OTHER_PROJECT from its "
            "single (login-walled) container file and classified from catalogue metadata alone. "
            "The resulting classes reflect the study topics described in the catalogue rather than "
            "the file contents."
        )
    else:
        specific = (
            "AUSSDA projects that expose primary-data files (PDF, RTF, DOCX) are typed QD_PROJECT and "
            "additionally classified from their file content; projects exposing only tabular or "
            "statistical files are OTHER_PROJECT, and those without retrievable files are "
            "NOT_A_PROJECT. A substantial share of AUSSDA records carry only short German-language "
            "topic labels, which the English keyword classifier cannot match - the main reason for "
            "unclassified projects in this repository."
        )
    return (
        f"Classified projects: {classified:,};  unclassified: {unclassified:,}.  "
        f"Distinct primary classes identified: {len(rows)}.\n"
        f"Most common primary classes: {top3}.\n\n"
        f"{specific}\n\n"
        "Interpretation note: ISIC classifies economic activities, whereas qualitative studies "
        "describe research subjects. The classifier assigns the closest economic activity (for "
        "example, labour-market research maps to division 78, Employment activities). This is an "
        "approximation inherent to applying an industrial taxonomy to research metadata, and the "
        "reported classes should be read as thematic groupings rather than exact industry codes."
    )


def build_pdf(db_path: str = DEFAULT_DB) -> pathlib.Path:
    from classification.isic_rev5 import SECTION_TITLE, DIVISION_SECTION

    OUT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(db_path)

    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    classified = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE primary_class IS NOT NULL").fetchone()[0]
    files_ok = conn.execute(
        "SELECT COUNT(*) FROM files WHERE status='SUCCEEDED'").fetchone()[0]
    files_cls = conn.execute(
        "SELECT COUNT(*) FROM files WHERE isic_division IS NOT NULL").fetchone()[0]
    n_classes = conn.execute(
        "SELECT COUNT(DISTINCT isic_division) FROM projects "
        "WHERE isic_division IS NOT NULL").fetchone()[0]
    repos = conn.execute("SELECT id, name FROM repositories ORDER BY id").fetchall()

    # sections roll-up
    sec = Counter()
    for code, n in conn.execute(
            "SELECT isic_division, COUNT(*) FROM projects "
            "WHERE isic_division IS NOT NULL GROUP BY isic_division"):
        sec[SECTION_TITLE.get(DIVISION_SECTION.get(code, "?"), "?")] += n
    sec_rows = sec.most_common()

    # matrix
    matrix = []
    for rid, rname in repos:
        for ptype in ("QDA_PROJECT", "QD_PROJECT"):
            n = conn.execute("SELECT COUNT(*) FROM projects WHERE repository_id=? AND type=?",
                             (rid, ptype)).fetchone()[0]
            dom = conn.execute(
                "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? AND type=? "
                "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC LIMIT 1",
                (rid, ptype)).fetchone()
            matrix.append((f"{rid} ({rname})", ptype, n, dom[0] if dom else "-"))

    out = OUT_DIR / f"{STUDENT_ID}-sq26-classification-report.pdf"
    with PdfPages(out) as pdf:
        pdf.infodict().update({"Title": "Seeding QDArchive Part 2 - Classification Report",
                               "Author": AUTHOR, "Subject": "ISIC Rev.5 classification results"})
        rep = Report(pdf)
        rep.cover(total, 100 * classified / total, 100 * files_cls / files_ok,
                  len(repos), n_classes)
        rep.summary(conn, total, classified, files_ok, files_cls, sec_rows, matrix)

        for rid, rname in repos:
            rows = conn.execute(
                "SELECT primary_class, COUNT(*) c FROM projects WHERE repository_id=? "
                "AND primary_class IS NOT NULL GROUP BY primary_class ORDER BY c DESC",
                (rid,)).fetchall()
            if not rows:
                continue
            total_repo = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE repository_id=?", (rid,)).fetchone()[0]
            classified_repo = sum(r[1] for r in rows)
            unclassified = total_repo - classified_repo
            tcounts = dict(conn.execute(
                "SELECT type, COUNT(*) FROM projects WHERE repository_id=? GROUP BY type", (rid,)))
            rep.repo_chart(rname, rid, rows, total_repo, tcounts, classified_repo)
            comment = _commentary(rname, rows, classified_repo, unclassified, tcounts)
            rep.repo_table(rname, rid, rows, classified_repo, comment)

    conn.close()
    print(f"[PDF] Wrote report ({rep.page} pages) -> {out}")
    return out


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    build_pdf(db)
