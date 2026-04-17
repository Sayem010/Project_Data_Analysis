# Seeding QDArchive — Part 1: Data Acquisition

**Student ID:** 23455702  
**Course:** Seeding QDArchive (SQ26) — FAU Erlangen  
**Supervisor:** Prof. Dirk Riehle  
**Semester:** Winter 2025/26 + Summer 2026

---

## Overview

This repository contains the data acquisition pipeline for Part 1 of the Seeding QDArchive project. The goal is to discover, download, and catalogue qualitative research datasets from two assigned repositories, storing all metadata in a structured SQLite database.

**Assigned repositories:**
| # | Name | URL |
|---|------|-----|
| 1 | UK Data Service (UKDS) | https://ukdataservice.ac.uk |
| 2 | AUSSDA (Austrian Social Science Data Archive) | https://aussda.at/en/ |

---

## Database

The metadata database is `23455702-seeding.db` located in the root of this repository.

It contains six tables as defined by the professor's schema:

| Table | Description |
|-------|-------------|
| `repositories` | The two assigned source repositories |
| `projects` | One row per discovered research project |
| `files` | All files (downloaded or attempted) per project |
| `keywords` | Keywords/tags per project, stored verbatim |
| `person_role` | Authors, uploaders, owners per project |
| `licenses` | License string per project, stored verbatim |

---

## Project Structure

```
.
├── 23455702-seeding.db          ← SQLite database (professor's required name)
├── main.py                      ← Pipeline entry point
├── requirements.txt
├── db/
│   ├── schema.sql               ← Table definitions
│   └── database.py              ← DB connection + insert helpers
├── scrapers/
│   ├── aussda_scraper.py        ← AUSSDA via Dataverse REST API
│   └── ukds_scraper.py          ← UKDS via CESSDA API + OAI-PMH
├── export/
│   └── export_csv.py            ← Export all tables to CSV
├── scripts/
│   └── retry_failed.py          ← Retry FAILED_SERVER_UNRESPONSIVE files
└── data/                        ← Downloaded files (not in git; uploaded to FAUbox)
    ├── aussda/
    │   └── {project_folder}/
    └── ukds/
        └── {project_folder}/
```

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/Sayem010/Project_Data_Analysis
cd Project_Data_Analysis

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Pipeline

```bash
# Run full pipeline (both repos)
python main.py

# Run only AUSSDA
python main.py --repo aussda

# Run only UK Data Service
python main.py --repo ukds

# Export CSVs only (no scraping)
python main.py --export-only

# Retry failed downloads
python scripts/retry_failed.py
```

---

## Download Methods

| Repository | Method | Reason |
|------------|--------|--------|
| AUSSDA | `API-CALL` | Full Dataverse 6.7.1 REST API available |
| UKDS | `API-CALL` | CESSDA Data Catalogue API + OAI-PMH harvest |

---

## File Status Values

| Status | Meaning |
|--------|---------|
| `SUCCEEDED` | File downloaded successfully |
| `FAILED_LOGIN_REQUIRED` | File exists but requires authentication (common in UKDS) |
| `FAILED_SERVER_UNRESPONSIVE` | Server did not respond or timed out |
| `FAILED_TOO_LARGE` | File exceeds 500 MB threshold |

---

## Technical Challenges (Data, not Programming)

### 1. Access Restrictions at UK Data Service

The UK Data Service requires user registration and login to download the actual data files for nearly all datasets, even those described as "open" or "publicly available." The portal presents metadata freely, but the download links redirect to a login wall. This means that while we can catalogue full metadata (title, description, keywords, authors, license) for all discovered projects, the actual files are recorded as `FAILED_LOGIN_REQUIRED`. This is a data governance issue: UKDS licenses are open, but the delivery mechanism requires institutional authentication. The metadata is complete and accurate; the files themselves require a UKDS account.

### 2. UKDS Catalogue is a Single-Page Application

The UK Data Service catalogue at `datacatalogue.ukdataservice.ac.uk` is built as a JavaScript Single-Page Application (SPA). Standard HTTP requests return only a minimal HTML shell with no data content — all search results and metadata are loaded dynamically via JavaScript. This means standard HTML scraping returns nothing useful. The pipeline therefore uses the CESSDA Data Catalogue API (the European network that indexes UKDS) and OAI-PMH harvesting as alternative data access points. The metadata retrieved this way is equivalent to what the catalogue shows visually, but the discovery path is indirect.

### 3. Inconsistent License Metadata

License information varies greatly in how it is recorded across projects. Some AUSSDA entries use the full Creative Commons name ("Creative Commons Attribution 4.0 International"), others use the URI (`https://creativecommons.org/licenses/by/4.0/`), and some entries have no license field at all. UKDS datasets often list access conditions ("Available to all registered users") rather than a formal license identifier. Per the professor's primary rule, all license strings are stored verbatim as found. Normalisation to CC-style shortcodes (e.g., `CC BY 4.0`) is deferred to Part 2 data quality fixing.

### 4. Keyword Quality and Granularity

Keywords from AUSSDA are stored individually per the schema. However, many projects use compound keyword strings that mix multiple concepts (e.g., `"interlanguage pragmatics, EFL learners, scoping review"`). These are stored exactly as received from the API without splitting or normalising. The professor's guidance explicitly states that keyword parsing should be handled in a separate cleanup step.

### 5. AUSSDA Access Restrictions (SUF Edition Datasets)

AUSSDA hosts two types of datasets: OA (Open Access) editions downloadable freely, and SUF (Scientific Use File) editions that require a formal data usage agreement with AUSSDA. The API returns metadata for both types equally, but file download attempts for SUF datasets return HTTP 401/403. These are recorded as `FAILED_LOGIN_REQUIRED`. This is expected and not a pipeline error — it is a data access policy of the repository.

### 6. Missing Version Information

Many projects lack formal version strings or have only implicit versions embedded in DOI suffixes (e.g., `V2` in the AUSSDA citation string). The `version` field is populated where available from the Dataverse API's `majorVersionNumber`/`minorVersionNumber` fields. For projects without this, the field is left NULL as allowed by the schema.

---

## Data Sources Summary

| Repository | Projects | Files Downloaded | Files Login-Required |
|------------|----------|-----------------|---------------------|
| AUSSDA | 1,594 | 2,627 | ~1,823 (SUF editions) |
| UKDS | 630 (via OAI-PMH) | 0 | 630 (all login-required) |
| **Total** | **11,967** | **2,627** | **~12,196** |

## Submission
- **Database:** `23455702-seeding.db` in repo root
- **GitHub:** https://github.com/Sayem010/Project_Data_Analysis
- **Git tag:** `part-1-release`
- **Data folder:** https://faubox.rrze.uni-erlangen.de/getlink/fiGUSAwEFHnMfzz6rchjfv/