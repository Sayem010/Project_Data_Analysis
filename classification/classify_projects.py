"""
classification/classify_projects.py

Part 2 - Tier 1 (metadata) classification.

Assigns an ISIC Rev.5 division to EVERY project using only the metadata already
stored in the database: title + description + keywords. This covers 100% of
projects (including the 10k+ UKDS projects that have no downloaded files).

Writes to PROJECTS:
    isic_division              e.g. '86'   (NULL if no term matched)
    isic_division_label        e.g. '86 - Human health activities'
    classification_source      'TIER1_METADATA'
    classification_confidence  rule-based match score

Run:
    python -m classification.classify_projects
"""

import sys
import pathlib
import sqlite3
from collections import defaultdict, Counter

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from classification.classifier import Classifier

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")
BATCH = 500


def _keywords_by_project(conn: sqlite3.Connection) -> dict[int, list[str]]:
    kw = defaultdict(list)
    for pid, keyword in conn.execute("SELECT project_id, keyword FROM keywords"):
        if keyword:
            kw[pid].append(keyword)
    return kw


def classify_projects(db_path: str = DEFAULT_DB) -> Counter:
    clf = Classifier()
    conn = sqlite3.connect(db_path)

    print("[TIER1] Loading keywords ...")
    kw_map = _keywords_by_project(conn)

    rows = conn.execute(
        "SELECT id, title, description FROM projects"
    ).fetchall()
    print(f"[TIER1] Classifying {len(rows)} projects ...")

    dist = Counter()
    updates = []
    n_classified = 0

    for pid, title, description in rows:
        parts = [title or "", description or ""]
        parts.extend(kw_map.get(pid, []))
        text = " . ".join(p for p in parts if p)

        ranked = clf.classify_ranked(text, n=2)
        if ranked:
            best = ranked[0]
            secondary_label = ranked[1].label if len(ranked) > 1 else None
            updates.append((best.division, best.label, best.label, secondary_label,
                            "TIER1_METADATA", best.score, pid))
            dist[best.division] += 1
            n_classified += 1
        else:
            updates.append((None, None, None, None, "TIER1_METADATA", 0.0, pid))
            dist["UNCLASSIFIED"] += 1

        if len(updates) >= BATCH:
            _flush(conn, updates)
            updates.clear()
            print(f"  ... {n_classified} classified so far")

    if updates:
        _flush(conn, updates)
    conn.close()

    print(f"[TIER1] Done. {n_classified}/{len(rows)} projects classified "
          f"({dist['UNCLASSIFIED']} unclassified).")
    return dist


def _flush(conn: sqlite3.Connection, updates: list[tuple]) -> None:
    with conn:
        conn.executemany(
            """UPDATE projects
               SET isic_division = ?, isic_division_label = ?,
                   primary_class = ?, secondary_class = ?,
                   classification_source = ?, classification_confidence = ?
               WHERE id = ?""",
            updates,
        )


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    dist = classify_projects(db)
    print("\nTop divisions:")
    for code, n in dist.most_common(15):
        print(f"  {code:>12}  {n}")
