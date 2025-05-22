import os
import subprocess
import shutil
import argparse

def clone_from_github(repo_url: str, dest_path: str = "downloaded_repo"):
    if os.path.exists(dest_path):
        print(f"이미 폴더가 존재합니다: {dest_path} → 삭제 후 클론")
        shutil.rmtree(dest_path)
    try:
        subprocess.run(["git", "clone", repo_url, dest_path], check=True)
        print(f"GitHub 클론 완료: {repo_url}")
    except subprocess.CalledProcessError:
        print("git clone 실패. git이 설치되어 있는지 확인하세요.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub 저장소 다운로드 자동화 스크립트")
    parser.add_argument("--url", required=True, help="GitHub 저장소 URL")
    parser.add_argument("--dest", default="downloaded_repo", help="다운로드 경로 (기본값: downloaded_repo)")
    args = parser.parse_args()

    clone_from_github(args.url, args.dest)
