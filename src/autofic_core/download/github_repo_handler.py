# =============================================================================
# Copyright 2025 AutoFiC Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

import os
import requests 
import subprocess
import shutil
from github import Github
from github.Repository import Repository
from urllib.parse import urlparse
from autofic_core.errors import GitHubTokenMissingError, RepoAccessError, RepoURLFormatError, ForkFailedError

class GitHubRepoHandler():
    """
    Handles GitHub authentication and repository operations using the given URL and token.
    Supports forking the repository if needed and returns the appropriate repo object.
    """
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubTokenMissingError()
        
        self.github = Github(self.token)
        self._owner, self._name = self._parse_repo_url(repo_url)
        self._current_user = self.github.get_user().login

        self.needs_fork = self._owner != self._current_user     # Determine if forking is necessary
    
    @staticmethod
    def _parse_repo_url(url: str) -> tuple[str, str]:
        """
        Extracts the owner and repo name from the given GitHub URL.
        """
        try:
            path = urlparse(url).path.strip("/")
            owner, repo = path.split("/")[:2]
            return owner, repo.removesuffix(".git")
        except Exception:
            raise RepoURLFormatError(url)
    
    def fetch_repo(self) -> Repository:
        """
        Returns the repository object (forked if needed).
        """
        repo_name = f"{self._current_user}/{self._name}"
        try:
            return self.github.get_repo(repo_name)
        except Exception as e:
            raise RepoAccessError(f"{repo_name}: {e}")

    def fork(self) -> bool:
        """
        Forks the repository into the current user's account.
        Returns True on success, raises error otherwise.
        """
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
    
    def clone_repo(self, save_dir: str, use_forked: bool = False) -> str:
        """
        Clones the repository into the specified local directory.
        Removes any existing 'repo' directory first.
        """
        save_dir = os.path.abspath(save_dir) 
        repo_path = os.path.join(save_dir, "repo")
    
        # Remove existing repo directory
        if os.path.exists(repo_path):
            if os.path.isdir(repo_path):
                shutil.rmtree(repo_path)
            else:
                raise ValueError(f"Target path is not a directory: {repo_path}")

        clone_url = f"https://github.com/{self._current_user}/{self._name}.git"
        subprocess.run(['git', 'clone', clone_url, repo_path], check=True)
        return repo_path