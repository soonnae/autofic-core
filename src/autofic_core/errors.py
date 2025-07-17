class AutoficError(Exception):
    """Base class for all custom errors"""
    pass

# github_handler.py 

class GitHubTokenMissingError(AutoficError):
    def __init__(self):
        super().__init__("GITHUB_TOKEN is not set in the environment.")

class RepoURLFormatError(AutoficError):
    def __init__(self, repo_url):
        super().__init__(f"Invalid GitHub repository URL format: {repo_url}")

class RepoAccessError(AutoficError):
    def __init__(self, message: str):
        super().__init__(message)

class ForkFailedError(RepoAccessError):
    def __init__(self, status_code, message):
        super().__init__(f"Failed to fork repository (HTTP {status_code}) - {message}")

# downloader.py

class FileDownloadError(AutoficError):
    def __init__(self, path, original_error):
        message = f"{path} Failed to download file: {original_error}"
        super().__init__(message)
        self.path = path
        self.original_error = original_error

# semgrep_runner.py

class SemgrepExecutionError(AutoficError):
    def __init__(self, returncode, stdout=None, stderr=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = f"Semgrep execution failed (return code:{returncode})"
        super().__init__(message)

# prompt_generator.py

class PromptGeneratorErrorCodes:
    EMPTY_SNIPPET = "EMPTY_SNIPPET"
    TEMPLATE_RENDER_ERROR = "TEMPLATE_RENDER_ERROR"
    INVALID_SNIPPET_LIST = "INVALID_SNIPPET_LIST"

class PromptGeneratorErrorMessages:
    EMPTY_SNIPPET = "The provided code snippet is empty."
    TEMPLATE_RENDER_ERROR = "An error occurred while rendering the prompt template."
    INVALID_SNIPPET_LIST = "The input must be a list of SemgrepSnippet objects."

class PromptGenerationException(AutoficError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

class LLMExecutionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"LLM execution error: {message}")

# diff_generator.py

class DiffGenerationError(AutoficError):
    def __init__(self, filename: str, reason: str):
        message = f"[Diff Generation Failed] File: {filename} - Reason: {reason}"
        super().__init__(message)
        self.filename = filename
        self.reason = reason

class CodeQLExecutionError(Exception):
    """Raised when CodeQL execution fails."""
    def __init__(self):
        super().__init__("[ERROR] CodeQL execution failed. Please check the log file for details.")