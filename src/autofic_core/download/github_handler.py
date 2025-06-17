import os
from github import Github
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from autofic_core.errors import GitHubTokenMissingError, RepoURLFormatError, RepoAccessError

class RepoFile(BaseModel):
    path: str
    download_url: str

class GitHubRepoHandler(BaseModel):
    repo_url: str
    file_extensions: tuple = Field(
        default_factory=lambda: tuple(
            ext.strip() for ext in os.getenv("GITHUB_EXTENSIONS", "").split(",") if ext.strip()
        )
    )
    token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))

    def __init__(self, **data):
        super().__init__(**data)
        if not self.token:
            raise GitHubTokenMissingError()
        
    def parse_repo_url(self) -> tuple[str, str]:
        try:
            path = urlparse(self.repo_url).path.strip("/")
            owner, repo_name = path.split("/")[:2]
            repo_name = repo_name[:-4] if repo_name.endswith(".git") else repo_name
            return owner, repo_name
        except ValueError:
            raise RepoURLFormatError(self.repo_url)
    
    def fetch_repo(self):
        owner, repo_name = self.parse_repo_url()
        full_name = f"{owner}/{repo_name}"
        try:
            return Github(self.token).get_repo(full_name)
        except Exception as e:
            raise RepoAccessError(f"{full_name}: {e}")
    
    def collect_files_by_extension(self, repo) -> list[RepoFile]:
        js_files = []
        contents = repo.get_contents("")
        while contents:
            file = contents.pop(0)
            try:
                if file.type == "dir":
                    contents.extend(repo.get_contents(file.path))
                elif file.name.endswith(self.file_extensions) and file.download_url:
                    js_files.append(RepoFile(path=file.path, download_url=file.download_url))
            except Exception:
                continue
        return js_files

    def get_repo_files(self) -> list[RepoFile]:
        repo = self.fetch_repo()
        return self.collect_files_by_extension(repo) 