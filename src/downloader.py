#src/downloader.py
import os
import subprocess
import zipfile
import requests
import shutil

def clone_from_github(repo_url: str, dest_path: str):
    if os.path.exists(dest_path):
        print(f"이미 폴더가 존재합니다: {dest_path} → 삭제 후 클론")
        shutil.rmtree(dest_path)
    try:
        subprocess.run(["git", "clone", repo_url, dest_path], check=True)
        print(f"GitHub 클론 완료: {repo_url}")
    except subprocess.CalledProcessError:
        print("git clone 실패. git이 설치되어 있는지 확인하세요.")

def download_and_extract_zip(repo_url: str, dest_path: str):
    zip_url = repo_url.rstrip("/").replace("github.com", "github.com") + "/archive/refs/heads/main.zip"
    zip_path = os.path.join(dest_path, "temp.zip")

    os.makedirs(dest_path, exist_ok=True)

    try:
        print(f"zip 다운로드 중... {zip_url}")
        with requests.get(zip_url, stream=True) as r:
            with open(zip_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)
        print(f"zip 압축 해제 완료")

    except Exception as e:
        print(f"zip 다운로드 실패: {e}")

    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

def use_local_path(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"경로가 존재하지 않습니다: {path}")
    print(f"로컬 경로 사용: {path}")
    return os.path.abspath(path)

