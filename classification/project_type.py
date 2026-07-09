"""
classification/project_type.py

Part 2 - Step 1: derive PROJECT_TYPE from a project's file types (PDF pages 22-23).

Rules (in priority order):
    QDA_PROJECT    if any file has a QDA file extension (.qdpx etc.)
    QD_PROJECT     else if there are primary-data files (txt/pdf/rtf/docx ...)
    OTHER_PROJECT  else if there are any other valid data files
    NOT_A_PROJECT  else nothing can be derived about file types (no files)

File-type sets are derived from the FILES table, which records file_name /
file_type for BOTH downloaded and login-required files, so the type can be
derived even when a file could not be downloaded.

Also computes no_project_files (total files recorded for the project) for the
Step 4c deliverable table.

Run (on the Part 2 database):
    python -m classification.project_type 23455702-sq26-classification.db
"""

import sys
import pathlib
import sqlite3
from collections import Counter

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DEFAULT_DB = str(_root / "23455702-sq26-classification.db")

# QDA (qualitative data analysis) project-file extensions - the REFI-QDA
# standard plus the major QDA tools' native project containers.
QDA_EXTS = {
    "qdpx", "qdp", "qde", "qdc",          # REFI-QDA exchange / project
    "nvp", "nvpx", "nvproj",              # NVivo
    "atlproj", "hpr7", "hpr8", "atlas",   # ATLAS.ti
    "mx24", "mx22", "mx20", "mx18", "mx12", "mex",  # MAXQDA
}

# Primary-data files: any form of qualitative data (transcripts, articles ...).
PRIMARY_EXTS = {
    "txt", "pdf", "rtf", "docx", "doc", "odt", "md",
    "html", "htm", "epub", "tex", "pages",
}

# Other "valid data files": real data-bearing files that are neither QDA nor
# primary qualitative data (statistical / tabular / container / media data).
VALID_EXTS = {
    "tab", "csv", "tsv", "sav", "zsav", "dta", "por", "sas7bdat",
    "sps", "do", "r", "rdata", "rda", "rds", "sas", "syntax",
    "xls", "xlsx", "ods", "json", "xml", "yml", "yaml", "dat",
    "zip", "7z", "rar", "tar", "gz",              # containers
    "jpg", "jpeg", "png", "gif", "tif", "tiff",   # image data
    "mp3", "wav", "mp4", "avi", "mov",            # audio/video data
}


def derive_type(file_types) -> str:
    """file_types: iterable of lowercase extensions (without dot)."""
    exts = {e.strip().lower().lstrip(".") for e in file_types if e and e.strip()}
    if not exts:
        return "NOT_A_PROJECT"
    if exts & QDA_EXTS:
        return "QDA_PROJECT"
    if exts & PRIMARY_EXTS:
        return "QD_PROJECT"
    if exts & VALID_EXTS:
        return "OTHER_PROJECT"
    return "NOT_A_PROJECT"


def classify_project_types(db_path: str = DEFAULT_DB) -> Counter:
    conn = sqlite3.connect(db_path)

    # file types + count per project
    ftypes: dict[int, list[str]] = {}
    counts: dict[int, int] = {}
    for pid, ftype in conn.execute("SELECT project_id, file_type FROM files"):
        ftypes.setdefault(pid, []).append(ftype)
        counts[pid] = counts.get(pid, 0) + 1

    all_ids = [r[0] for r in conn.execute("SELECT id FROM projects")]

    dist = Counter()
    updates = []
    for pid in all_ids:
        ptype = derive_type(ftypes.get(pid, []))
        nfiles = counts.get(pid, 0)
        updates.append((ptype, nfiles, pid))
        dist[ptype] += 1

    with conn:
        conn.executemany(
            "UPDATE projects SET type = ?, no_project_files = ? WHERE id = ?",
            updates,
        )
    conn.close()

    print(f"[TYPES] Classified {len(all_ids)} projects by file type:")
    for t in ("QDA_PROJECT", "QD_PROJECT", "OTHER_PROJECT", "NOT_A_PROJECT"):
        print(f"    {t:<14} {dist.get(t, 0)}")
    return dist


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    classify_project_types(db)
