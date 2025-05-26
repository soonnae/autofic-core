import os
import requests
from .github_handler import get_repo_files

def download_files(repo_url, save_dir="downloaded_repo", silent=False):
    """GitHub 저장소에서 JS 파일 목록을 가져와 다운로드합니다."""

    js_files = get_repo_files(repo_url, silent=silent)

    if not js_files:
        if not silent:
            print("JS 파일을 찾지 못했습니다.")
        return

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
