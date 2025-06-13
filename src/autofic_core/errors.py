class AutoficError(Exception):
    """Base class for all custom errors"""
    pass

# github_handler.py 

class GitHubTokenMissingError(AutoficError):
    def __init__(self):
        super().__init__("GITHUB_TOKEN이 설정되어 있지 않습니다.")

class RepoURLFormatError(AutoficError):
    def __init__(self, repo_url):
        super().__init__(f"잘못된 GitHub URL 형식입니다 : {repo_url}")

class RepoAccessError(AutoficError):
    def __init__(self, repo_name):
        super().__init__(f"저장소에 접근할 수 없습니다 : {repo_name}")

# downloader.py

class FileDownloadError(AutoficError):
    def __init__(self, path, original_error):
        message = f"{path} 다운로드 실패: {original_error}"
        super().__init__(message)
        self.path = path
        self.original_error = original_error


class SemgrepExecutionError(AutoficError):
    def __init__(self, returncode, stdout=None, stderr=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = f"Semgrep 실행 실패 (리턴 코드: {returncode})"
        super().__init__(message)