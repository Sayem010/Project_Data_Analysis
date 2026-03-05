# Seeding QDArchive – Part 1: Data Acquisition Pipeline

## Project Overview

This project is part of the **Applied Software Engineering Project** focused on *Seeding QDArchive*, a research initiative aimed at collecting and organizing qualitative research datasets from publicly available repositories.

The objective of **Part 1** is to design and implement an automated **data acquisition pipeline** that collects qualitative research datasets, extracts metadata, stores the information in a structured database, and exports the metadata into a CSV format for further processing.

The collected datasets will later be used for classification and analysis in the next stages of the project.

---

## Objectives

The main goals of this project are:

- Identify repositories that host qualitative research datasets.
- Automatically download research datasets from open-access sources.
- Extract relevant metadata from each dataset.
- Store metadata in a structured database.
- Export metadata to a CSV file for analysis.
- Build a reproducible and modular data acquisition pipeline.

---

## Project Structure

```
Project_Data_Analysis
│
├── src
│ ├── main.py
│ │
│ ├── database
│ │ └── db_manager.py
│ │
│ ├── pipeline
│ │ └── download_pipeline.py
│ │
│ ├── scrapers
│ │ ├── zenodo_scraper.py
│ │ └── dataverse_scraper.py
│ │
│ └── utils
│ ├── file_utils.py
│ └── metadata_extractor.py
│
├── data
│ ├── raw_downloads
│ └── metadata
│
├── config
├── logs
├── notebooks
├── requirements.txt
└── README.md

```


---

## Data Acquisition Pipeline

The pipeline performs the following steps:

### 1. Repository Search
The system searches for datasets from open research repositories such as:

- Zenodo  
- Dataverse  

These repositories provide publicly available research datasets.

---

### 2. Dataset Download
When relevant datasets are identified, the pipeline downloads the associated files into the local **data/raw_downloads/** directory.

---

### 3. Metadata Extraction

For each dataset, the pipeline extracts the following metadata:

- Dataset URL
- Download timestamp
- Local storage directory
- Filename
- Source repository
- License information
- Uploader name
- Uploader email (if available)

---

### 4. Database Storage

All metadata is stored in a **SQLite database**:

data/metadata/qdarchive.db
---

### 5. CSV Export

Metadata is exported to a CSV file:

data/metadata/metadata.csv

This file will be used for classification and analysis in the next phases of the project.

---

## Database Schema

| Field | Description |
|------|-------------|
| id | Unique dataset identifier |
| url | Source dataset URL |
| timestamp | Download time |
| local_dir | Local storage path |
| filename | Downloaded file name |
| source | Dataset repository |
| license | Dataset license |
| uploader_name | Author/uploader name |
| uploader_email | Author email |

---

## Installation

Make sure **Python 3.9+** is installed.

Install project dependencies:

pip install -r requirements.txt

Required libraries include:

- requests
- pandas
- tqdm
- beautifulsoup4
- pyyaml

---

## Running the Pipeline

Run the following command from the project root:

python -m src.main

The pipeline will:

1. Initialize the metadata database  
2. Download datasets from repositories  
3. Store metadata in the database  
4. Export metadata to CSV  

---

## Output Files

After execution, the following outputs are generated.

### Downloaded datasets
data/raw_downloads/


### Metadata database


data/metadata/qdarchive.db


### Metadata CSV


data/metadata/metadata.csv


---

## Reproducibility

The pipeline is designed to be reproducible. Running the pipeline multiple times will continue collecting datasets without duplicating existing records.

---

## Future Work (Part 2 & Part 3)

Future stages of the project will include:

- Dataset classification using **ISIC categories**
- Duplicate dataset detection
- Metadata analysis
- Statistical reporting
- Integration with the **QDArchive system**

---

## Author

**Sayem Bin Sarwar Chowdhury**  
Msc in Artificial Intelligence  
Friedrich Alexander University