"""
scrapers/ukds_scraper.py

Scrapes UK Data Service qualitative datasets.

Confirmed resolving domains:
  - datacatalogue.ukdataservice.ac.uk  (CloudFront, the main SPA)
  - oai.ukdataservice.ac.uk            (Essex server - OAI-PMH endpoint)
  - beta.ukdataservice.ac.uk           (Essex server - beta API)

REMOVED (does not resolve):
  - search.ukdataservice.ac.uk

Strategy (in order):
  1. beta.ukdataservice.ac.uk REST API
  2. oai.ukdataservice.ac.uk OAI-PMH harvest
  3. datacatalogue HTML scraping for study IDs
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://datacatalogue.ukdataservice.ac.uk/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── CONFIRMED working domains only ────────────────────────────────────────────
OAI_URL      = "https://oai.ukdataservice.ac.uk/oai/provider"
BETA_URL     = "https://beta.ukdataservice.ac.uk"
CATALOGUE_URL = "https://datacatalogue.ukdataservice.ac.uk"

SEARCH_QUERIES = [
    "qualitative",
    "interview",
    "focus group",
    "ethnography",
    "qualitative research",
    "thematic analysis",
    "grounded theory",
]


def _get(url, params=None, retries=3, timeout=25):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=timeout)
            return r
        except requests.RequestException as e:
            print(f"    [WARN] attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None


def _now():
    return datetime.now(timezone.utc).isoformat()


def _make_row(pid, title, desc, lang, doi, upload_date, query, method):
    folder = str(pid).replace("/", "-").replace(":", "-")
    return folder, {
        "query_string":               query,
        "repository_id":              REPO_ID,
        "repository_url":             REPO_URL,
        "project_url":                f"{CATALOGUE_URL}/studies/{pid}",
        "version":                    None,
        "title":                      str(title)[:500] if title else f"UKDS Study {pid}",
        "description":                str(desc)[:5000] if desc else "No description available",
        "language":                   str(lang) if lang else "en",
        "doi":                        str(doi) if doi else None,
        "upload_date":                str(upload_date)[:10] if upload_date else None,
        "download_date":              _now(),
        "download_repository_folder": REPO_NAME,
        "download_project_folder":    folder,
        "download_version_folder":    None,
        "download_method":            method,
    }


def _save(conn, row, keywords, persons, license_str, pid, data_root):
    from db.database import insert_project, insert_file, insert_keywords, \
        insert_persons, insert_license, project_exists

    if project_exists(conn, row["project_url"]):
        return None

    folder = row["download_project_folder"]
    pathlib.Path(data_root, REPO_NAME, folder).mkdir(parents=True, exist_ok=True)

    with conn:
        project_id = insert_project(conn, row)
        insert_keywords(conn, project_id, keywords)
        insert_persons(conn, project_id, persons)
        insert_license(conn, project_id, license_str)
        # UKDS requires login for all files
        insert_file(conn, {
            "project_id": project_id,
            "file_name":  f"{pid}_data.zip",
            "file_type":  "zip",
            "status":     "FAILED_LOGIN_REQUIRED",
        })
    return project_id


# ── Strategy 1: beta.ukdataservice.ac.uk REST API ────────────────────────────

def _try_beta_api(query, conn, data_root):
    added = 0

    # These are the paths the beta site might expose
    endpoints = [
        f"{BETA_URL}/api/search",
        f"{BETA_URL}/api/studies",
        f"{BETA_URL}/api/datasets",
        f"{BETA_URL}/search",
    ]
    param_variants = [
        {"q": query,      "limit": 25, "offset": 0},
        {"search": query, "rows":  25, "start":  0},
        {"query": query,  "size":  25, "from":   0},
        {"q": query,      "per_page": 25, "page": 1},
    ]

    for url in endpoints:
        for params in param_variants:
            r = _get(url, params=params, timeout=15)
            if not r or r.status_code != 200:
                continue
            try:
                data = r.json()
            except Exception:
                continue

            # Extract items from various response shapes
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (
                    data.get("hits", {}).get("hits") if isinstance(data.get("hits"), dict)
                    else data.get("hits") if isinstance(data.get("hits"), list)
                    else data.get("results") or data.get("studies")
                    or data.get("datasets") or data.get("data") or []
                )
            else:
                items = []

            if not items:
                continue

            print(f"  [BETA-API] {url} params={list(params.keys())} → {len(items)} items")
            for item in items:
                src = item.get("_source", item)
                pid = (src.get("studyNumber") or src.get("id") or
                       src.get("study_number") or "")
                if not pid:
                    continue

                title = src.get("titleStudy") or src.get("title") or ""
                desc  = src.get("abstractText") or src.get("abstract") or src.get("description") or ""
                lang  = src.get("language") or "en"
                date  = src.get("publicationYear") or src.get("datePublished") or None
                doi   = src.get("doi") or ""
                kws   = [k.get("keyword", k) if isinstance(k, dict) else str(k)
                         for k in src.get("keywords", [])]
                auths = src.get("creators") or src.get("authors") or []
                acc   = src.get("access", {})
                lic   = acc.get("condition", "") if isinstance(acc, dict) else ""

                folder, row = _make_row(pid, title, desc, lang, doi, date,
                                        query, "API-CALL")
                pid_out = _save(conn, row, kws,
                                [{"name": str(a), "role": "AUTHOR"} for a in auths if a],
                                lic, pid, data_root)
                if pid_out:
                    print(f"    [DB] {pid_out}: {str(title)[:55]}")
                    added += 1
            return added  # stop trying other combos once one works

    return added


# ── Strategy 2: OAI-PMH ──────────────────────────────────────────────────────

def _scrape_oai(conn, data_root):
    added = 0
    ns = {
        "oai":    "http://www.openarchives.org/OAI/2.0/",
        "dc":     "http://purl.org/dc/elements/1.1/",
        "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    }

    # Discover sets
    r = _get(OAI_URL, params={"verb": "ListSets"}, timeout=20)
    set_specs = [""]  # "" means no set filter = harvest everything
    if r and r.status_code == 200:
        try:
            root = ET.fromstring(r.text)
            found = [s.findtext("oai:setSpec", "", ns)
                     for s in root.findall(".//oai:set", ns)]
            if found:
                set_specs = found
                print(f"  [OAI] {len(set_specs)} sets: {set_specs[:5]}")
            else:
                print("  [OAI] No sets found, harvesting without set filter")
        except ET.ParseError as e:
            print(f"  [OAI] ListSets parse error: {e}")
    else:
        print(f"  [OAI] ListSets failed (status={r.status_code if r else 'no response'})")

    for set_spec in set_specs[:15]:
        params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
        if set_spec:
            params["set"] = set_spec

        page = 0
        while page < 50:
            r = _get(OAI_URL, params=params, timeout=30)
            if not r or r.status_code != 200:
                print(f"  [OAI] set={set_spec!r} HTTP {r.status_code if r else 'None'}")
                break

            try:
                root = ET.fromstring(r.text)
            except ET.ParseError as e:
                print(f"  [OAI] XML parse error: {e}")
                break

            # Check for OAI error
            err = root.find(".//oai:error", ns)
            if err is not None:
                print(f"  [OAI] error code={err.get('code')}: {err.text}")
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
                    return [e.text for e in meta_el.findall(f"dc:{tag}", ns)
                            if e.text]

                id_el = header.find("oai:identifier", ns) if header else None
                pid   = id_el.text if id_el is not None else ""
                if not pid:
                    continue

                titles   = dc("title")
                descs    = dc("description")
                creators = dc("creator")
                subjects = dc("subject")
                dates    = dc("date")
                rights   = dc("rights")
                langs    = dc("language")
                idents   = dc("identifier")
                doi      = next((i for i in idents if "doi" in i.lower()), None)

                folder, row = _make_row(
                    pid,
                    titles[0] if titles else "",
                    " ".join(descs),
                    langs[0] if langs else "en",
                    doi,
                    dates[0] if dates else None,
                    f"OAI set={set_spec!r}",
                    "API-CALL"
                )
                pid_out = _save(
                    conn, row, subjects,
                    [{"name": c, "role": "AUTHOR"} for c in creators],
                    rights[0] if rights else "",
                    pid, data_root
                )
                if pid_out:
                    added += 1
                    print(f"    [OAI] {pid_out}: {(titles[0] if titles else pid)[:50]}")

            # Resumption token for next page
            tok = root.find(".//oai:resumptionToken", ns)
            if tok is not None and tok.text and tok.text.strip():
                params = {"verb": "ListRecords",
                          "resumptionToken": tok.text.strip()}
                page += 1
                time.sleep(0.5)
            else:
                break

    return added


# ── Strategy 3: HTML study ID extraction ──────────────────────────────────────

def _scrape_html(query, conn, data_root):
    added = 0
    url = f"{CATALOGUE_URL}/searchresults?search={query.replace(' ', '+')}"
    r = _get(url, timeout=20)
    if not r or r.status_code != 200:
        print(f"  [HTML] no response for '{query}'")
        return 0

    # Extract numeric study IDs from href patterns like /studies/12345
    study_ids = list(set(re.findall(r'/studies/(\d{4,})', r.text)))
    print(f"  [HTML] '{query}' → {len(study_ids)} study IDs found in page")

    for sid in study_ids[:50]:
        folder, row = _make_row(
            sid, f"UKDS Study {sid}",
            "Metadata retrieved via HTML scraping — login required for full access",
            "en", None, None, query, "SCRAPING"
        )
        pid_out = _save(conn, row, [], [], "", sid, data_root)
        if pid_out:
            added += 1
            print(f"    [HTML] Study {sid} saved as project_id={pid_out}")
        time.sleep(0.2)

    return added


# ── entry point ───────────────────────────────────────────────────────────────

def scrape_ukds(data_root="data", db_path="23455702-seeding.db"):
    from db.database import get_connection
    conn = get_connection(db_path)
    total = 0

    # Strategy 1: Beta REST API
    for query in SEARCH_QUERIES:
        print(f"\n[UKDS] Query: '{query}'")
        n = _try_beta_api(query, conn, data_root)
        total += n
        if n:
            print(f"  Beta API added: {n}")
        time.sleep(0.5)

    # Strategy 2: OAI-PMH (best chance of real data)
    print("\n[UKDS] OAI-PMH harvest...")
    n = _scrape_oai(conn, data_root)
    total += n
    print(f"  OAI-PMH added: {n}")

    # Strategy 3: HTML scraping fallback
    print("\n[UKDS] HTML scraping fallback...")
    for query in SEARCH_QUERIES[:4]:
        n = _scrape_html(query, conn, data_root)
        total += n
        time.sleep(1.5)

    conn.close()
    print(f"\n[UKDS] Done. {total} projects processed.")
    return []
