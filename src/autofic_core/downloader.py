import os
import requests
from autofic_core.errors import FileDownloadError

def download_file(file, save_dir="downloaded_repo"):
    path = file["path"]
    local_path = os.path.join(save_dir, path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    if os.path.exists(local_path):
        return {"path": path, "status": "skipped"}

    try:
        res = requests.get(file["download_url"])
        res.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(res.content)
        return {"path": path, "status": "success"}
    
    except Exception as e:
        return {"path": path, "status": "fail", "error": str(FileDownloadError(path, str(e)))}