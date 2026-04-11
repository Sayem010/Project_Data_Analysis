"""
scrapers/ukds_scraper.py

Scrapes UK Data Service qualitative datasets.

Strategy (tried in order):
  1. UKDS internal REST API (what the SPA calls via XHR)
  2. OAI-PMH harvest with resumption tokens
  3. HTML page scraping to extract embedded study IDs

Download method: API-CALL / SCRAPING
Repository folder: ukds
"""

import sys
import re
import json
import time
import pathlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

_root = pathlib.Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

REPO_NAME  = "ukds"
REPO_ID    = 1
REPO_URL   = "https://ukdataservice.ac.uk"
MAX_FILE_BYTES = 500 * 1024 * 1024

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://datacatalogue.ukdataservice.ac.uk/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

OAI_ENDPOINT = "https://oai.ukdataservice.ac.uk/oai/provider"

SEARCH_QUERIES = [
    "qualitative",
    "interview",
    "focus group",
    "ethnography",
    "qualitative research",
    "thematic analysis",
    "grounded theory",
]

# All known API base URLs to try
API_BASES = [
    "https://datacatalogue.ukdataservice.ac.uk/api",
    "https://beta.ukdataservice.ac.uk/api",
    "https://search.ukdataservice.ac.uk",
]


def _get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            return r
        except requests.RequestException as e:
            print(f"    [WARN] attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None


def _ext(fname):
    return pathlib.Path(fname).suffix.lstrip(".").lower() or "bin"


def _insert_study(conn, project_row, keywords, persons, license_str, study_id):
    from db.database import insert_project, insert_file, insert_keywords, \
        insert_persons, insert_license
    project_id = insert_project(conn, project_row)
    insert_keywords(conn, project_id, keywords)
    insert_persons(conn, project_id, persons)
    insert_license(conn, project_id, license_str)
    insert_file(conn, {
        "project_id": project_id,
        "file_name":  f"{study_id}_data.zip",
        "file_type":  "zip",
        "status":     "FAILED_LOGIN_REQUIRED",
    })
    return project_id


def _make_project_row(pid, title, desc, lang, doi, upload_date,
                      query, method="API-CALL"):
    project_folder = str(pid).replace("/", "-").replace(":", "-")
    return project_folder, {
        "query_string":               query,
        "repository_id":              REPO_ID,
        "repository_url":             REPO_URL,
        "project_url":                f"https://datacatalogue.ukdataservice.ac.uk/studies/{pid}",
        "version":                    None,
        "title":                      str(title)[:500],
        "description":                str(desc)[:5000] if desc else "No description available",
        "language":                   str(lang) if lang else "en",
        "doi":                        str(doi) if doi else None,
        "upload_date":                str(upload_date)[:10] if upload_date else None,
        "download_date":              datetime.now(timezone.utc).isoformat(),
        "download_repository_folder": REPO_NAME,
        "download_project_folder":    str(pid).replace("/", "-").replace(":", "-"),
        "download_version_folder":    None,
        "download_method":            method,
    }


# ── Strategy 1: REST API ──────────────────────────────────────────────────────

def _try_rest_api(query, conn, data_root):
    from db.database import project_exists
    added = 0

    param_sets = [
        {"q": query, "limit": 25, "offset": 0},
        {"search": query, "rows": 25, "start": 0},
        {"query": query, "size": 25, "from": 0},
        {"term": query, "pageSize": 25, "page": 1},
        {"q": query, "per_page": 25, "page": 1},
    ]
    paths = ["/search", "/search/studies", "/studies/search",
             "/datasets", "/v0/search", "/v1/search"]

    for base in API_BASES:
        for path in paths:
            for params in param_sets:
                url = base + path
                r = _get(url, params=params)
                if not r or r.status_code != 200:
                    continue
                try:
                    data = r.json()
                except Exception:
                    continue

                # Extract items from various response shapes
                items = (data.get("hits", {}).get("hits") if isinstance(data.get("hits"), dict) else
                         data.get("hits") if isinstance(data.get("hits"), list) else
                         data.get("results") or data.get("datasets") or
                         data.get("studies") or data.get("data") or
                         (data if isinstance(data, list) else []))

                if not items:
                    continue

                print(f"  [API] {url} → {len(items)} results")
                for item in items:
                    src = item.get("_source", item)
                    pid = (src.get("studyNumber") or src.get("id") or
                           src.get("study_number") or "")
                    if not pid:
                        continue
                    project_url = f"https://datacatalogue.ukdataservice.ac.uk/studies/{pid}"
                    if project_exists(conn, project_url):
                        continue

                    title = src.get("titleStudy") or src.get("title") or ""
                    desc  = src.get("abstractText") or src.get("abstract") or src.get("description") or ""
                    lang  = src.get("language") or "en"
                    date  = src.get("publicationYear") or src.get("datePublished") or None
                    doi   = src.get("doi") or ""
                    kws   = [k.get("keyword", k) if isinstance(k, dict) else k
                             for k in src.get("keywords", [])]
                    auths = src.get("creators") or src.get("authors") or []
                    lic   = (src.get("access", {}).get("condition", "")
                             if isinstance(src.get("access"), dict) else "")

                    project_folder, row = _make_project_row(
                        pid, title, desc, lang, doi, date, query)
                    pathlib.Path(data_root, REPO_NAME, project_folder).mkdir(
                        parents=True, exist_ok=True)

                    with conn:
                        pid_out = _insert_study(
                            conn, row, kws,
                            [{"name": a, "role": "AUTHOR"} for a in auths if a],
                            lic, pid)
                    print(f"    [DB] {pid_out}: {str(title)[:50]}")
                    added += 1
                return added  # found working endpoint
    return added


# ── Strategy 2: OAI-PMH ──────────────────────────────────────────────────────

def _scrape_oai(conn, data_root):
    from db.database import project_exists, insert_project, insert_file, \
        insert_keywords, insert_persons, insert_license
    added = 0
    ns = {
        "oai":    "http://www.openarchives.org/OAI/2.0/",
        "dc":     "http://purl.org/dc/elements/1.1/",
        "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    }

    # Get list of sets first
    r = _get(OAI_ENDPOINT, params={"verb": "ListSets"})
    set_specs = [""]
    if r and r.status_code == 200:
        try:
            root = ET.fromstring(r.text)
            set_specs = [s.findtext("oai:setSpec", "", ns)
                         for s in root.findall(".//oai:set", ns)] or [""]
            print(f"  [OAI] {len(set_specs)} sets available")
        except ET.ParseError:
            pass

    for set_spec in set_specs[:10]:
        params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
        if set_spec:
            params["set"] = set_spec

        page = 0
        while page < 20:  # safety cap
            r = _get(OAI_ENDPOINT, params=params)
            if not r or r.status_code != 200:
                break
            try:
                root = ET.fromstring(r.text)
            except ET.ParseError:
                break

            records = root.findall(".//oai:record", ns)
            if not records:
                break

            for rec in records:
                header = rec.find("oai:header", ns)
                if header is not None and header.get("status") == "deleted":
                    continue
                meta_el = rec.find("oai:metadata/oai_dc:dc", ns)
                if meta_el is None:
                    continue

                def dc(tag):
                    return [e.text for e in meta_el.findall(f"dc:{tag}", ns) if e.text]

                id_el = header.find("oai:identifier", ns) if header else None
                pid   = id_el.text if id_el is not None else ""
                project_url = f"https://datacatalogue.ukdataservice.ac.uk/studies/{pid}"
                if project_exists(conn, project_url):
                    continue

                titles   = dc("title")
                descs    = dc("description")
                creators = dc("creator")
                subjects = dc("subject")
                dates    = dc("date")
                rights   = dc("rights")
                langs    = dc("language")
                ids      = dc("identifier")
                doi      = next((i for i in ids if "doi" in i.lower()), None)

                project_folder, row = _make_project_row(
                    pid,
                    titles[0] if titles else f"UKDS Study {pid}",
                    " ".join(descs) if descs else "",
                    langs[0] if langs else "en",
                    doi,
                    dates[0] if dates else None,
                    f"OAI-PMH set={set_spec}",
                    method="API-CALL"
                )
                pathlib.Path(data_root, REPO_NAME, project_folder).mkdir(
                    parents=True, exist_ok=True)

                with conn:
                    pid_out = _insert_study(
                        conn, row, subjects,
                        [{"name": c, "role": "AUTHOR"} for c in creators],
                        rights[0] if rights else "", pid)
                added += 1
                print(f"    [OAI] {pid_out}: {(titles[0] if titles else pid)[:50]}")

            # Resumption token
            tok = root.find(".//oai:resumptionToken", ns)
            if tok is not None and tok.text:
                params = {"verb": "ListRecords", "resumptionToken": tok.text}
                page += 1
            else:
                break

    return added


# ── Strategy 3: HTML scraping for study IDs ───────────────────────────────────

def _scrape_html(query, conn, data_root):
    from db.database import project_exists
    added = 0
    url = f"https://datacatalogue.ukdataservice.ac.uk/searchresults?search={query.replace(' ', '+')}"
    r = _get(url)
    if not r or r.status_code != 200:
        return 0

    # Extract study IDs from page HTML
    study_ids = list(set(re.findall(r'(?:studies|study)[/"](\d{4,})', r.text)))
    print(f"  [HTML] '{query}' → {len(study_ids)} study IDs in page")

    for sid in study_ids[:30]:
        project_url = f"https://datacatalogue.ukdataservice.ac.uk/studies/{sid}"
        if project_exists(conn, project_url):
            continue

        project_folder, row = _make_project_row(
            sid, f"UKDS Study {sid}",
            "Metadata retrieved via HTML scraping",
            "en", None, None, query, method="SCRAPING")
        pathlib.Path(data_root, REPO_NAME, project_folder).mkdir(
            parents=True, exist_ok=True)

        with conn:
            from db.database import insert_license
            pid_out = _insert_study(conn, row, [], [], "", sid)
        added += 1
        print(f"    [HTML] Study {sid}")
        time.sleep(0.3)

    return added


# ── entry point ───────────────────────────────────────────────────────────────

def scrape_ukds(data_root="data", db_path="23455702-seeding.db"):
    from db.database import get_connection
    conn = get_connection(db_path)
    total = 0

    for query in SEARCH_QUERIES:
        print(f"\n[UKDS] Query: '{query}'")
        n = _try_rest_api(query, conn, data_root)
        total += n
        time.sleep(1)

    print("\n[UKDS] Trying OAI-PMH...")
    n = _scrape_oai(conn, data_root)
    total += n
    print(f"  OAI-PMH added: {n}")

    print("\n[UKDS] Trying HTML scraping...")
    for query in SEARCH_QUERIES[:3]:
        n = _scrape_html(query, conn, data_root)
        total += n
        time.sleep(2)

    conn.close()
    print(f"\n[UKDS] Done. {total} projects processed.")
    return []
