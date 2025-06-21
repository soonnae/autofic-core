import os
from pydantic import BaseModel, Field
from typing import List
from github.Repository import Repository

class RepoFile(BaseModel):
    """
    다운로드 대상 파일의 경로 및 다운로드 URL을 저장하는 모델
    """
    path: str
    download_url: str

class GitHubFileCollector(BaseModel):
    """
    GitHub Repository에서 지정한 확장자의 파일 목록을 수집하는 클래스
    """
    repo: Repository
    file_extensions: tuple = Field(
        default_factory=lambda: tuple(
            ext.strip() for ext in os.getenv("GITHUB_EXTENSIONS", "").split(",") if ext.strip()
        )
    )

    def collect(self) -> List[RepoFile]:
        files = []
        contents = self.repo.get_contents("")
        while contents:
            item = contents.pop(0)
            try:
                if item.type == "dir":
                    contents.extend(self.repo.get_contents(item.path))
                elif item.name.endswith(self.file_extensions):
                    files.append(RepoFile(path=item.path, download_url=item.download_url))
            except Exception:
                continue
        return files