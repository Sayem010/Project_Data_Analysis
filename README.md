# Project_Data_AnalysisSeeding QDArchive – Part 1: Data Acquisition Pipeline
Project Overview

This project is part of the Applied Software Engineering Project focused on Seeding QDArchive, a research initiative aimed at collecting and organizing qualitative research datasets from publicly available repositories.

The objective of Part-1 is to design and implement an automated data acquisition pipeline that collects qualitative research datasets, extracts metadata, stores the information in a structured database, and exports the metadata into a CSV format for further processing.

The collected datasets will later be used for classification and analysis tasks in subsequent phases of the project.

Objectives

The main goals of Part-1 are:

Identify and access repositories that host qualitative research data.

Automatically download research datasets from open-access sources.

Extract relevant metadata from each dataset.

Store metadata in a structured database.

Export the metadata into a CSV file for further analysis.

Maintain a reproducible data acquisition pipeline.

Project Structure

The repository is organized using a modular Python project structure to support maintainability and scalability.

Project_Data_Analysis
│
├── src
│   ├── main.py
│   │
│   ├── database
│   │   └── db_manager.py
│   │
│   ├── pipeline
│   │   └── download_pipeline.py
│   │
│   ├── scrapers
│   │   ├── zenodo_scraper.py
│   │   └── dataverse_scraper.py
│   │
│   └── utils
│       ├── file_utils.py
│       └── metadata_extractor.py
│
├── data
│   ├── raw_downloads
│   └── metadata
│
├── config
│
├── logs
│
├── notebooks
│
├── requirements.txt
└── README.md
Data Acquisition Pipeline

The implemented pipeline performs the following steps:

Repository Search

The system queries open research repositories such as:

Zenodo

Dataverse

These repositories provide publicly accessible research datasets.

Dataset Retrieval

When relevant datasets are found, the pipeline downloads associated files into the local data directory.

Metadata Extraction

For each dataset, the following metadata fields are collected:

Dataset URL

Download timestamp

Local storage directory

Filename

Source repository

License information

Uploader name

Uploader email (if available)

Database Storage

All metadata is stored in a SQLite database:

data/metadata/qdarchive.db

CSV Export

The metadata is exported to:

data/metadata/metadata.csv

This file will be used for classification and analysis in later stages of the project.

Database Schema

The metadata database contains the following fields:

Field	Description
id	Unique dataset identifier
url	Source dataset URL
timestamp	Download time
local_dir	Local storage path
filename	Name of downloaded file
source	Repository source
license	Dataset license
uploader_name	Dataset author/uploader
uploader_email	Contact email if available
Installation

Ensure that Python is installed on your system.

Install required dependencies:

pip install -r requirements.txt

Required libraries include:

requests

pandas

tqdm

beautifulsoup4

pyyaml

Running the Pipeline

To execute the pipeline, run:

python -m src.main

The pipeline will:

Initialize the metadata database

Collect datasets from repositories

Store metadata in the database

Export metadata to CSV

Output Files

After execution, the following outputs are generated:

Downloaded datasets

data/raw_downloads/

Metadata database

data/metadata/qdarchive.db

Metadata CSV

data/metadata/metadata.csv
Reproducibility

The pipeline is designed to be fully reproducible. Running the pipeline multiple times will continue collecting datasets and storing metadata without duplicating existing records.

Future Work (Part-2 and Part-3)

Subsequent project stages will extend this work to include:

Dataset classification using ISIC categories

Duplicate dataset detection

Metadata analysis

Statistical reporting of collected qualitative data

Integration with the QDArchive system

Author

Sayem Bin Sarwar Chowdhury
Master's Student – Artificial Intelligence
Friedrich-Alexander-Universität Erlangen-Nürnberg