import os
from github import Github
from dotenv import load_dotenv
from urllib.parse import urlparse
from autofic_core.errors import GitHubTokenMissingError, RepoURLFormatError, RepoAccessError

load_dotenv()

DEFAULT_EXTENSIONS = (".js", ".mjs", ".jsx", ".ts") 

def get_github_token():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token 
    raise GitHubTokenMissingError()

def parse_repo_url(repo_url):
    try:
        path = urlparse(repo_url).path.strip("/")
        owner, repo_name = path.split("/")[:2]
        repo_name = repo_name[:-4] if repo_name.endswith(".git") else repo_name
        return owner, repo_name
    except ValueError:
        raise RepoURLFormatError(repo_url)
    
def fetch_github_repo(token, owner, repo_name):
    full_name = f"{owner}/{repo_name}"
    try:
        return Github(token).get_repo(full_name)
    except Exception as e:
        raise RepoAccessError(f"{full_name}: {e}")

def collect_files_by_extension(repo, extensions):
    js_files = []
    contents = repo.get_contents("")
    while contents:
        file = contents.pop(0)
        try:
            if file.type == "dir":
                contents.extend(repo.get_contents(file.path))
            elif file.name.endswith(extensions) and file.download_url:
                js_files.append({"path": file.path, "download_url": file.download_url})
        except Exception:
            continue
    return js_files

def get_repo_files(repo_url, file_extensions=DEFAULT_EXTENSIONS):
    token = get_github_token()
    owner, repo_name = parse_repo_url(repo_url)
    repo = fetch_github_repo(token, owner, repo_name)
    return collect_files_by_extension(repo, file_extensions)