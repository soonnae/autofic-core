# autofic_core/github_handler.py

import os
from github import Github
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()  # .env 파일에서 환경 변수 로드

def parse_repo_url(repo_url):
    """URL에서 사용자명/저장소명을 추출"""
    path = urlparse(repo_url).path.strip("/")
    owner, repo_name = path.split("/")[:2]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    return owner, repo_name

def get_repo_files(repo_url, file_extensions=(".js", ".mjs", ".jsx", ".ts")):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN이 .env에 없습니다.")

    try:
        g = Github(token)
    except Exception as e:
        return []

    try:
        owner, repo_name = parse_repo_url(repo_url)
        repo = g.get_repo(f"{owner}/{repo_name}")
    except Exception as e:
        return []
    
    js_files = []
    contents = repo.get_contents("")

    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        elif file_content.name.endswith(file_extensions) and file_content.download_url:
            js_files.append({
                "path": file_content.path,
                "download_url": file_content.download_url
            })

    return js_files
