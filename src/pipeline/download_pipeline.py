import os

from src.scrapers.zenodo_scraper import search_zenodo
from src.utils.file_utils import download_file
from src.database.db_manager import insert_record


DOWNLOAD_DIR = "data/raw_downloads/zenodo"


def run_pipeline():

    records = search_zenodo()

    for record in records:

        local_dir = os.path.join(DOWNLOAD_DIR, record["filename"].split(".")[0])
        os.makedirs(local_dir, exist_ok=True)

        save_path = os.path.join(local_dir, record["filename"])

        download_file(record["url"], save_path)

        record["local_dir"] = local_dir

        insert_record(record)