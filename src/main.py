from src.database.db_manager import init_db
from src.pipeline.download_pipeline import run_pipeline
from src.utils.metadata_extractor import export_csv


def main():

    print("Initializing database...")
    init_db()

    print("Running download pipeline...")
    run_pipeline()

    print("Exporting metadata to CSV...")
    export_csv()

    print("Pipeline completed!")


if __name__ == "__main__":
    main()