import sqlite3
import pandas as pd

DB_PATH = "data/metadata/qdarchive.db"


def export_csv():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query("SELECT * FROM datasets", conn)

    df.to_csv("data/metadata/metadata.csv", index=False)

    conn.close()