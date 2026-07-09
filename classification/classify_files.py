"""
classification/classify_files.py

Part 2 - Tier 2 (primary-data) classification.

For every successfully downloaded file we read its primary-data content
(see text_extract.py) and classify it into an ISIC Rev.5 division.

Only files with status = 'SUCCEEDED' have bytes on disk, so only those can be
read. Login-required / failed files are left unclassified (there is no content
to read - the honest outcome). To still satisfy "each primary data file should
have a class", a downloaded file whose bytes yield no usable text (e.g. a binary
.zsav statistics file) INHERITS its parent project's Tier-1 division, flagged
with classification_confidence = 0.0 to mark it as inherited rather than
content-derived.

Writes to FILES:
    isic_division              division code
    isic_division_label        'NN - Title'
    classification_confidence  >0  = derived from the file's own content
                               0.0 = inherited from the project's metadata class

Run (after classify_projects, so parent classes exist for inheritance):
    python -m classification.classify_files
"""

import sys
import pathlib
import sqlite3
from collections import Counter

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from classification.classifier import Classifier
from classification.text_extract import extract_text

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")
DATA_ROOT = _root / "data"
BATCH = 200


def _disk_path(repo_folder, project_folder, version_folder, file_name) -> pathlib.Path:
    parts = [DATA_ROOT, repo_folder, project_folder]
    if version_folder:
        parts.append(version_folder)
    parts.append(file_name)
    return pathlib.Path(*[str(p) for p in parts])


def classify_files(db_path: str = DEFAULT_DB) -> Counter:
    clf = Classifier()
    conn = sqlite3.connect(db_path)

    rows = conn.execute(
        """SELECT f.id, f.file_name,
                  p.download_repository_folder, p.download_project_folder,
                  p.download_version_folder, p.isic_division, p.isic_division_label
           FROM files f
           JOIN projects p ON p.id = f.project_id
           WHERE f.status = 'SUCCEEDED'"""
    ).fetchall()
    print(f"[TIER2] {len(rows)} downloaded files to classify ...")

    stats = Counter()
    updates = []

    for (fid, fname, repo_folder, proj_folder, ver_folder,
         parent_div, parent_label) in rows:
        path = _disk_path(repo_folder, proj_folder, ver_folder, fname)
        text = extract_text(path)

        result = clf.classify(text) if text else None
        if result:
            updates.append((result.division, result.label, result.score, fid))
            stats["from_content"] += 1
            stats[result.division] += 1
        elif parent_div:
            # no readable content -> inherit the project's metadata class
            updates.append((parent_div, parent_label, 0.0, fid))
            stats["inherited"] += 1
        else:
            updates.append((None, None, None, fid))
            stats["unclassified"] += 1

        if len(updates) >= BATCH:
            _flush(conn, updates)
            done = stats["from_content"] + stats["inherited"] + stats["unclassified"]
            print(f"  ... {done}/{len(rows)} processed "
                  f"(content={stats['from_content']}, inherited={stats['inherited']})")
            updates.clear()

    if updates:
        _flush(conn, updates)
    conn.close()

    print(f"[TIER2] Done. content-derived={stats['from_content']}, "
          f"inherited={stats['inherited']}, unclassified={stats['unclassified']}")
    return stats


def _flush(conn: sqlite3.Connection, updates: list[tuple]) -> None:
    with conn:
        conn.executemany(
            """UPDATE files
               SET isic_division = ?, isic_division_label = ?,
                   classification_confidence = ?
               WHERE id = ?""",
            updates,
        )


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    stats = classify_files(db)
    print("\nTop file divisions (content-derived):")
    for code, n in stats.most_common():
        if code not in ("from_content", "inherited", "unclassified"):
            from classification.isic_rev5 import label
            print(f"  {label(code)}: {n}")
