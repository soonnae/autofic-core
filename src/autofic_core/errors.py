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
    def __init__(self, message: str):
        super().__init__(message)

class ForkFailedError(RepoAccessError):
    def __init__(self, status_code, message):
        super().__init__(f"Fork 요청 실패 (코드: {status_code}) - {message}")

# downloader.py

class FileDownloadError(AutoficError):
    def __init__(self, path, original_error):
        message = f"{path} 다운로드 실패: {original_error}"
        super().__init__(message)
        self.path = path
        self.original_error = original_error

# semgrep_runner.py

class SemgrepExecutionError(AutoficError):
    def __init__(self, returncode, stdout=None, stderr=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = f"Semgrep 실행 실패 (리턴 코드: {returncode})"
        super().__init__(message)

# prompt_generator.py

class PromptGeneratorErrorCodes:
    EMPTY_SNIPPET = "EMPTY_SNIPPET"
    TEMPLATE_RENDER_ERROR = "TEMPLATE_RENDER_ERROR"
    INVALID_SNIPPET_LIST = "INVALID_SNIPPET_LIST"

class PromptGeneratorErrorMessages:
    EMPTY_SNIPPET = "빈 코드 스니펫입니다."
    TEMPLATE_RENDER_ERROR = "템플릿 렌더링 중 오류가 발생했습니다."
    INVALID_SNIPPET_LIST = "SemgrepSnippet 리스트가 아닙니다."

class PromptGenerationException(AutoficError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

class LLMExecutionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"LLM 실행 오류: {message}")

# diff_generator.py

class DiffGenerationError(AutoficError):
    def __init__(self, filename: str, reason: str):
        message = f"[diff 생성 실패] 파일: {filename} - 이유: {reason}"
        super().__init__(message)
        self.filename = filename
        self.reason = reason