import time
from urllib.parse import urlparse
from rich.console import Console
from pathlib import Path

console = Console()


def print_divider(title):
    console.print(f"\n\n[bold magenta]{'-'*20} [ {title} ] {'-'*20}[/bold magenta]\n\n")


def extract_repo_name(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    return parsed.path.strip("/").split("/")[-1]

def print_summary(repo_url: str, detected_issues_count: int, output_dir: str, response_files: list):
    print_divider("AutoFiC Summary")

    repo_name = extract_repo_name(repo_url)
    console.print(f"✔️  [bold]Target Repository:[/bold] {repo_name}")
    console.print(f"✔️  [bold]Files with detected vulnerabilities:[/bold] {detected_issues_count} 개")
    console.print(f"✔️  [bold]LLM Responses:[/bold] Saved in the 'llm' folder")

    console.print(f"\n[bold magenta]{'━'*64}[/bold magenta]\n")
    time.sleep(2.0)


def print_help_message():
    console.print("\n\n [ AutoFiC CLI Usage Guide ]", fg="magenta", bold=True)
    console.print("""

--explain       Display AutoFiC usage guide

--repo          GitHub repository URL to analyze (required)
--save-dir      Directory to save analysis results (default: artifacts/downloaded_repo)

--sast          Run SAST analysis using selected tool (semgrep, codeql, snyk)

--llm           Run LLM to fix vulnerable code and save response
--llm-retry     Re-run LLM to verify and finalize code

\n※ Example usage:
    python -m autofic_core.cli --repo https://github.com/user/project --sast --llm

⚠️ Note:
  - The --sast option must be run before using --llm or --llm-retry
    """)

