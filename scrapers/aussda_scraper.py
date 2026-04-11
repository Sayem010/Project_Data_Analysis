"""
scrapers/aussda_scraper.py

Scrapes AUSSDA (https://data.aussda.at) via the standard Dataverse REST API.
Download method: API-CALL
Repository folder: aussda
"""

import os
import sys
import time
import pathlib
import requests
from datetime import datetime, timezone

# Ensure project root is on path for db imports
_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# ── constants ──────────────────────────────────────────────────────────────────
BASE_URL        = "https://data.aussda.at"
REPO_NAME       = "aussda"
REPO_ID         = 2
REPO_URL        = "https://aussda.at/en/"
QUERY_STRING    = "qualitative"
DOWNLOAD_METHOD = "API-CALL"

# Files larger than 500 MB are flagged as too large rather than downloaded
MAX_FILE_BYTES  = 500 * 1024 * 1024

SEARCH_QUERIES = [
    "qualitative",
    "interview",
    "qualitative research",
    "interview transcripts",
    "focus group",
]

HEADERS = {
    "User-Agent": "SQ26-Student-Scraper/1.0 (FAU Erlangen; 23455702)"
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ── helpers ────────────────────────────────────────────────────────────────────

def _get(url: str, params: dict = None, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 401:
                return {"__access_denied__": True}
            elif r.status_code == 404:
                return None
            else:
                print(f"  [WARN] HTTP {r.status_code} for {url}")
        except requests.RequestException as e:
            print(f"  [WARN] attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
    return None


def _determine_license(data: dict) -> str:
    """Extract license from dataset metadata; return raw string."""
    try:
        terms = data.get("data", {}).get("latestVersion", {}).get("termsOfUse", "")
        if terms:
            return terms
        license_obj = data.get("data", {}).get("latestVersion", {}).get("license", {})
        if isinstance(license_obj, dict):
            return license_obj.get("name", "") or license_obj.get("uri", "")
        return str(license_obj) if license_obj else ""
    except Exception:
        return ""


def _determine_file_status(file_meta: dict, download_ok: bool, status_code: int | None) -> str:
    if download_ok:
        return "SUCCEEDED"
    if status_code == 401 or status_code == 403:
        return "FAILED_LOGIN_REQUIRED"
    if status_code is None:
        return "FAILED_SERVER_UNRESPONSIVE"
    return "FAILED_SERVER_UNRESPONSIVE"


def _download_file(url: str, dest_path: pathlib.Path, file_size: int | None) -> tuple[bool, int | None]:
    """Download a single file. Returns (success, http_status_code)."""
    if file_size and file_size > MAX_FILE_BYTES:
        print(f"    [SKIP] too large ({file_size/1e6:.1f} MB): {dest_path.name}")
        return False, None  # will be marked FAILED_TOO_LARGE by caller

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        print(f"    [SKIP] already exists: {dest_path.name}")
        return True, 200

    try:
        r = SESSION.get(url, timeout=60, stream=True)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            print(f"    [OK] {dest_path.name}")
            return True, 200
        else:
            print(f"    [FAIL] HTTP {r.status_code}: {dest_path.name}")
            return False, r.status_code
    except requests.RequestException as e:
        print(f"    [FAIL] {e}: {dest_path.name}")
        return False, None


# ── main scraper ───────────────────────────────────────────────────────────────

def scrape_aussda(data_root: str = "data", db_path: str = "23455702-seeding.db") -> list[dict]:
    """
    Scrape AUSSDA and return list of project dicts ready for DB insertion.
    Each dict also contains 'files', 'keywords', 'persons', 'license'.
    """
    from db.database import get_connection, insert_project, insert_file, insert_keywords, insert_persons, insert_license, project_exists

    conn = get_connection(db_path)
    results = []
    seen_dois = set()

    for query in SEARCH_QUERIES:
        print(f"\n[AUSSDA] Query: '{query}'")
        start = 0
        per_page = 25

        while True:
            resp = _get(
                f"{BASE_URL}/api/search",
                params={"q": query, "type": "dataset", "per_page": per_page, "start": start},
            )
            if not resp or resp.get("status") != "OK":
                print(f"  [WARN] no/bad response for query '{query}' start={start}")
                break

            items = resp["data"].get("items", [])
            total = resp["data"].get("total_count", 0)
            print(f"  Found {total} total; fetching {start}–{start+len(items)}")

            for item in items:
                doi = item.get("global_id", "")
                if doi in seen_dois:
                    continue
                seen_dois.add(doi)

                project_url = item.get("url", f"{BASE_URL}/dataset.xhtml?persistentId={doi}")

                if project_exists(conn, project_url):
                    print(f"  [SKIP] already in DB: {doi}")
                    continue

                print(f"\n  Processing: {item.get('name','?')[:60]}")

                # ── fetch full dataset metadata ──
                meta = _get(
                    f"{BASE_URL}/api/datasets/:persistentId/",
                    params={"persistentId": doi},
                )

                version_str = None
                upload_date = None
                language    = None
                license_str = ""

                if meta and meta.get("status") == "OK":
                    latest = meta["data"].get("latestVersion", {})
                    version_str = f"{latest.get('majorVersionNumber','')}.{latest.get('minorVersionNumber','')}".strip(".")
                    upload_date = item.get("published_at", "")[:10] if item.get("published_at") else None
                    license_str = _determine_license(meta)

                # ── fetch file list ──
                files_resp = _get(
                    f"{BASE_URL}/api/datasets/:persistentId/versions/:latest/files",
                    params={"persistentId": doi},
                )

                file_list = []
                if files_resp and files_resp.get("status") == "OK":
                    file_list = files_resp.get("data", [])

                # ── determine local folder ──
                # Use last segment of DOI as project folder
                project_folder = doi.split("/")[-1].replace(":", "-")
                local_dir = pathlib.Path(data_root) / REPO_NAME / project_folder
                local_dir.mkdir(parents=True, exist_ok=True)

                download_date = datetime.now(timezone.utc).isoformat()

                project_row = {
                    "query_string":                 query,
                    "repository_id":                REPO_ID,
                    "repository_url":               REPO_URL,
                    "project_url":                  project_url,
                    "version":                      version_str,
                    "title":                        item.get("name", ""),
                    "description":                  item.get("description", ""),
                    "language":                     language,
                    "doi":                          f"https://doi.org/{doi.replace('doi:','')}" if doi else None,
                    "upload_date":                  upload_date,
                    "download_date":                download_date,
                    "download_repository_folder":   REPO_NAME,
                    "download_project_folder":      project_folder,
                    "download_version_folder":      None,
                    "download_method":              DOWNLOAD_METHOD,
                }

                with conn:
                    project_id = insert_project(conn, project_row)

                    # keywords
                    insert_keywords(conn, project_id, item.get("keywords", []))

                    # authors → AUTHOR role
                    persons = [{"name": a, "role": "AUTHOR"} for a in item.get("authors", [])]
                    # contacts → UNKNOWN
                    for c in item.get("contacts", []):
                        if c.get("name"):
                            persons.append({"name": c["name"], "role": "UNKNOWN"})
                    insert_persons(conn, project_id, persons)

                    # license
                    insert_license(conn, project_id, license_str)

                    # ── download files ──
                    for file_meta in file_list:
                        df = file_meta.get("dataFile", {})
                        file_id   = df.get("id")
                        file_name = df.get("filename", f"file_{file_id}")
                        file_size = df.get("filesize")
                        ext       = pathlib.Path(file_name).suffix.lstrip(".").lower() or "bin"

                        if not file_id:
                            continue

                        # Check if restricted
                        restricted = file_meta.get("restricted", False)
                        if restricted:
                            insert_file(conn, {
                                "project_id": project_id,
                                "file_name":  file_name,
                                "file_type":  ext,
                                "status":     "FAILED_LOGIN_REQUIRED",
                            })
                            print(f"    [RESTRICTED] {file_name}")
                            continue

                        if file_size and file_size > MAX_FILE_BYTES:
                            insert_file(conn, {
                                "project_id": project_id,
                                "file_name":  file_name,
                                "file_type":  ext,
                                "status":     "FAILED_TOO_LARGE",
                            })
                            continue

                        download_url = f"{BASE_URL}/api/access/datafile/{file_id}"
                        dest = local_dir / file_name
                        ok, code = _download_file(download_url, dest, file_size)

                        if not ok and file_size and file_size > MAX_FILE_BYTES:
                            status = "FAILED_TOO_LARGE"
                        else:
                            status = _determine_file_status(file_meta, ok, code)

                        insert_file(conn, {
                            "project_id": project_id,
                            "file_name":  file_name,
                            "file_type":  ext,
                            "status":     status,
                        })

                        time.sleep(0.5)  # be polite

                results.append(project_row)
                print(f"  [DB] Saved project_id={project_id}: {item.get('name','')[:50]}")
                time.sleep(1)

            start += per_page
            if start >= total:
                break

    conn.close()
    print(f"\n[AUSSDA] Done. {len(results)} projects processed.")
    return results
