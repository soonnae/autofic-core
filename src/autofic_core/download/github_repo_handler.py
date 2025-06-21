import os
import requests 
from github import Github
from github.Repository import Repository
from github.GithubException import GithubException
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from autofic_core.errors import GitHubTokenMissingError, RepoAccessError, RepoURLFormatError, ForkFailedError

class GitHubRepoHandler(BaseModel):
    """GitHub 저장소 URL과 토큰을 이용해 인증하고, 
    필요한 경우 Fork를 수행한 뒤, 저장소 객체를 반환하는 클래스"""
    repo_url: str
    token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.token:
            raise GitHubTokenMissingError()
        self.github = Github(self.token)
        self._owner, self._name = self._parse_repo_url(self.repo_url)
        self._current_user = self.github.get_user().login
    
    @staticmethod
    # URL에서 owner와 name 추출
    def _parse_repo_url(url: str) -> tuple[str, str]:
        try:
            path = urlparse(url).path.strip("/")
            owner, repo = path.split("/")[:2]
            return owner, repo.removesuffix(".git")
        except Exception:
            raise RepoURLFormatError(url)

    # 현재 로그인 사용자와 저장소 소유자가 다른지 확인
    @property
    def needs_fork(self) -> bool:
        return self._current_user.lower() != self._owner.lower()
    
    # 저장소 객체 반환 (Fork 여부에 따라 소유자 변경)
    def fetch_repo(self, use_forked: bool = False) -> Repository:
        owner = self._current_user if use_forked else self._owner
        try:
            return self.github.get_repo(f"{owner}/{self._name}")
        except GithubException as e:
            raise RepoAccessError(f"{owner}/{self._name}: [{e.status}] {e.data.get('message')}")
        except Exception as e:
            raise RepoAccessError(f"{owner}/{self._name}: {e}")

    # 저장소를 현재 사용자 계정으로 Fork. 성공 여부 반환
    def fork(self) -> bool:
        api_url = f"https://api.github.com/repos/{self._owner}/{self._name}/forks"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        response = requests.post(api_url, headers=headers)
        if response.status_code == 202:
            return True
        else:
            raise ForkFailedError(response.status_code, response.text)