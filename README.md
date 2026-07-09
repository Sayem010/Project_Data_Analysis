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

---

# Part 2 — Classification (ISIC Rev. 5)

Part 2 (a) assigns each project a **PROJECT_TYPE** derived from its file types,
and (b) classifies every project and every downloaded primary-data file into an
**ISIC Revision 5 division** — "two levels down", i.e. divisions not just
sections (per the assignment). ISIC = the UN International Standard Industrial
Classification of All Economic Activities.

All Part 2 work is performed on a **separate database**,
`23455702-sq26-classification.db` (a copy of the Part 1 seeding DB), so the
Part 1 database stays pristine. That DB is tagged `classification-results`.

## Step 1 — Project types (`type` column)

Each project is filtered into one of four `PROJECT_TYPE` values, derived from the
file extensions recorded for it:

| Type | Rule |
|------|------|
| `QDA_PROJECT` | has a file with a QDA extension (`.qdpx`, NVivo, ATLAS.ti, MAXQDA …) |
| `QD_PROJECT` | not QDA, but has primary-data files (`txt/pdf/rtf/docx …`) |
| `OTHER_PROJECT` | not QD, but has other valid data files (tabular/statistical/containers) |
| `NOT_A_PROJECT` | no files → nothing can be derived |

Result: **0 QDA_PROJECT** (no `.qdpx` files exist in the collected data),
**936 QD_PROJECT** (AUSSDA records with primary documents), **10,388 OTHER_PROJECT**
(all UKDS, which only expose a login-walled container file, + AUSSDA tabular-only),
**643 NOT_A_PROJECT** (no files).

## Approach

A **local, deterministic, rule-based classifier** is used (no external API, no
network, fully reproducible). Each ISIC division is associated with weighted
terms drawn from two sources:

1. **Auto-seeded terms** — extracted from each division's official ISIC title,
   guaranteeing that all 87 divisions are reachable.
2. **Curated terms** — a hand-built map of strong, discriminative signals for
   the topics that dominate qualitative social-science research (health,
   education, social work, public administration, labour, agriculture, …).

For a given text the classifier lower-cases it, scores every division by the
weighted terms that appear (single words matched on word boundaries, phrases
matched verbatim), and assigns the highest-scoring division. A text with no
matching term is left unclassified. The same input always produces the same
division.

## Two tiers of source data

| Tier | Source | Covers |
|------|--------|--------|
| **Tier 1** | Project **metadata** (title + description + keywords) | all 11,967 projects |
| **Tier 2** | **Primary-data content** of downloaded files (PDF/DOCX/TXT/RTF text, plus the text files inside QDA/ZIP containers) | the 2,626 downloaded AUSSDA files |

Files whose bytes contain no readable text (e.g. binary `.zsav`/`.sav`
statistics files) **inherit** their project's Tier-1 division, flagged with
`classification_confidence = 0.0` to distinguish inherited from content-derived
classes.

## Schema additions

The classification is stored by adding columns to the existing Part 1 tables
(via idempotent `ALTER TABLE`; Part 1 tables and grading are unaffected):

**`projects`**
| Column | Meaning |
|--------|---------|
| `type` | PROJECT_TYPE (`QDA_PROJECT`/`QD_PROJECT`/`OTHER_PROJECT`/`NOT_A_PROJECT`) |
| `no_project_files` | total number of files recorded for the project |
| `primary_class` | full ISIC label of the most likely division |
| `secondary_class` | full ISIC label of the 2nd division (if any) |
| `isic_division` | 2-digit division code, e.g. `86` (NULL = unclassified) |
| `isic_division_label` | `NN - Title`, e.g. `86 - Human health activities` |
| `classification_source` | `TIER1_METADATA` |
| `classification_confidence` | rule-based match score |

**`files`**
| Column | Meaning |
|--------|---------|
| `isic_division` | division code assigned to the file |
| `isic_division_label` | `NN - Title` |
| `classification_confidence` | `>0` = derived from file content; `0.0` = inherited from project |

## Running Part 2

```bash
python run_part2.py                 # full: migrate -> types -> Tier 1 -> Tier 2 -> reports + deliverables
python run_part2.py --skip-files    # skip Tier 2 file-content classification (fast)
python run_part2.py --report-only   # regenerate stats + XLSX + PDF only
```

Individual stages:
```bash
python -m classification.migrate_schema
python -m classification.project_type      # Step 1: PROJECT_TYPE
python -m classification.classify_projects # Tier 1
python -m classification.classify_files    # Tier 2
python -m classification.report_stats      # stats (CSV + Markdown)
python -m classification.export_xlsx       # Step 4c XLSX deliverable
python -m classification.report_pdf        # Step 4d PDF deliverable
```

## Part 2 structure

```
classification/
├── isic_rev5.py          ← ISIC Rev.5 reference (22 sections, 87 divisions)
├── project_type.py       ← Step 1: PROJECT_TYPE from file extensions
├── classifier.py         ← rule-based keyword classifier (top-N divisions)
├── text_extract.py       ← primary-data text extraction (pdf/docx/rtf/txt/zip)
├── migrate_schema.py     ← adds PROJECT_TYPE + ISIC columns to projects + files
├── classify_projects.py  ← Tier 1 (metadata) -> primary/secondary class
├── classify_files.py     ← Tier 2 (file content)
├── report_stats.py       ← distribution stats + CSV/Markdown (+ type x repo matrix)
├── export_xlsx.py        ← Step 4c XLSX deliverable table
├── report_pdf.py         ← Step 4d PDF report (vector histograms + top-20 tables)
└── data/
    └── isic_rev5_structure.csv   ← authoritative UNSD source file (provenance)
run_part2.py              ← Part 2 entry point
```

## Results

| Level | Classified | Coverage |
|-------|-----------|----------|
| Projects | 11,500 / 11,967 | **96.1 %** |
| Downloaded files | 2,606 / 2,626 | **99.2 %** (1,891 from content, 715 inherited) |

**Distributions by repository × project type** (the page-29 matrix):

| Repository | QDA_PROJECT | QD_PROJECT |
|------------|------------:|-----------:|
| 1 — UKDS | 0 | 0 (all UKDS = OTHER_PROJECT, files login-walled) |
| 2 — AUSSDA | 0 | 936 (dominant class: 84 – Public administration) |

**Top ISIC sections (all classified projects):**

| Section | Title | Projects | % |
|---------|-------|---------:|--:|
| R | Human health and social work activities | 2,530 | 22.0 % |
| O | Administrative and support service activities | 2,517 | 21.9 % |
| P | Public administration and defence | 1,874 | 16.3 % |
| Q | Education | 1,522 | 13.2 % |
| N | Professional, scientific and technical activities | 499 | 4.3 % |

## Deliverables (submit on moo.uni1.de)

| File | Step | Content |
|------|------|---------|
| `deliverables/23455702-sq26-classification-table.xlsx` | 4c | one row per project: `repository_id, project_type, project_title, primary_class, secondary_class, no_project_files` |
| `deliverables/23455702-sq26-classification-report.pdf` | 4d | per repository: primary-class histogram (vector, counts on bars) + top-20 table + comments |
| `23455702-sq26-classification.db` | 4a | the Part 2 database, committed to the repo and git-tagged `classification-results` |

Machine-readable stats are also written to `export_output/`
(`classification_projects_by_division.csv`, `classification_by_section.csv`,
`PART2_classification_report.md`).

Additionally, **Step 4b** requires filling the Google Form
(<https://forms.gle/wxTGQFBQbBvFi3N69>) once per repository with the project
types found, their counts, and the dominant class — see the PDF report's
per-repository summary pages for those figures.

## Technical Challenges (Part 2 — Data)

1. **German-language metadata.** A large share of AUSSDA records have only
   short German topic labels (e.g. *"Thema: Umweltethik"*). The English keyword
   classifier cannot match these, which accounts for most of the 467
   unclassified projects. A multilingual keyword layer is a future improvement.
2. **Research topic vs. economic activity.** ISIC classifies *economic
   activities*, but qualitative studies describe *subjects*. Mapping, e.g.,
   labour-market research to division 78 (*Employment activities*) is the
   closest available fit rather than an exact match — an inherent limitation of
   applying an industrial classification to research metadata.
3. **No file content for most projects.** The 10,373 UKDS projects and the
   restricted AUSSDA SUF datasets have no downloadable files, so they can only
   be classified from Tier-1 metadata; Tier-2 content classification is limited
   to the 2,626 successfully downloaded AUSSDA files.
4. **Binary primary-data files.** Statistics files (`.zsav`, `.sav`, `.dta`)
   contain no readable text; those files inherit their project's class rather
   than being classified from content.