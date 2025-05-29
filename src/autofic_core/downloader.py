import os
import requests

def download_files(js_files, save_dir="downloaded_repo"):
    results = []

    for file in js_files:
        path = file["path"]
        url = file["download_url"]
        local_path = os.path.join(save_dir, path)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if os.path.exists(local_path):
            results.append({"path": path, "status": "skipped"})
            continue

        try:
            response = requests.get(url)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                f.write(response.content)
            results.append({"path": path, "status": "success"})
        except Exception as e:
            results.append({"path": path, "status": "fail", "error": str(e)})

    return results
