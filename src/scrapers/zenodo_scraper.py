import requests


ZENODO_API = "https://zenodo.org/api/records"


def search_zenodo(query="qualitative interview"):
    params = {
        "q": query,
        "size": 10
    }

    response = requests.get(ZENODO_API, params=params)
    data = response.json()

    records = []

    for hit in data["hits"]["hits"]:
        metadata = hit["metadata"]

        for file in hit["files"]:
            records.append({
                "url": file["links"]["self"],
                "filename": file["key"],
                "license": metadata.get("license", {}).get("id", ""),
                "source": "zenodo",
                "uploader_name": metadata.get("creators", [{}])[0].get("name", ""),
                "uploader_email": ""
            })

    return records