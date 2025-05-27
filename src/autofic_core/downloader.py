import os
import requests

def download_files(js_files, save_dir="downloaded_repo", silent=False):

    for file in js_files:
        path = file["path"]
        url = file["download_url"]
        local_path = os.path.join(save_dir, path)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            response = requests.get(url)
            with open(local_path, "wb") as f:
                f.write(response.content)
            if not silent:
                print(f"{path} 다운로드 완료")
        except Exception as e:
            print(f"{path} 다운로드 실패: {e}")
