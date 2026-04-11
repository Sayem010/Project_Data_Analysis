-- QDArchive Seeding Database Schema
-- Student ID: 23455702
-- Primary rule: Do not change data when downloading

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─────────────────────────────────────────
-- REPOSITORIES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS repositories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    url     TEXT    NOT NULL
);

-- ─────────────────────────────────────────
-- PROJECTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    query_string                TEXT,
    repository_id               INTEGER NOT NULL REFERENCES repositories(id),
    repository_url              TEXT    NOT NULL,
    project_url                 TEXT    NOT NULL,
    version                     TEXT,
    title                       TEXT    NOT NULL,
    description                 TEXT    NOT NULL,
    language                    TEXT,
    doi                         TEXT,
    upload_date                 TEXT,
    download_date               TEXT    NOT NULL,
    download_repository_folder  TEXT    NOT NULL,
    download_project_folder     TEXT    NOT NULL,
    download_version_folder     TEXT,
    download_method             TEXT    NOT NULL CHECK(download_method IN ('SCRAPING','API-CALL'))
);

-- ─────────────────────────────────────────
-- FILES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    file_name   TEXT    NOT NULL,
    file_type   TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK(status IN (
                    'SUCCEEDED',
                    'FAILED_LOGIN_REQUIRED',
                    'FAILED_SERVER_UNRESPONSIVE',
                    'FAILED_TOO_LARGE'
                ))
);

-- ─────────────────────────────────────────
-- KEYWORDS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    keyword     TEXT    NOT NULL
);

-- ─────────────────────────────────────────
-- PERSON_ROLE
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS person_role (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    name        TEXT    NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN (
                    'AUTHOR','UPLOADER','OWNER','OTHER','UNKNOWN'
                ))
);

-- ─────────────────────────────────────────
-- LICENSES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS licenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    license     TEXT    NOT NULL
);
