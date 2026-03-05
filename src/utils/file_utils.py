import requests
import os


def download_file(url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    response = requests.get(url, stream=True)

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return save_path