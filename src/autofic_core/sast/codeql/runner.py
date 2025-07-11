import subprocess
from pathlib import Path
from autofic_core.errors import CodeQLExecutionError


class CodeQLRunner:

    def __init__(self, repo_path: Path, language: str = "javascript"):
        self.repo_path = Path(repo_path).resolve()
        self.language = language.lower()
        self.query_pack = f"codeql/{self.language}-queries"
        self.db_path = self.repo_path / ".codeql-db"
        self.result_dir = self.repo_path / ".codeql-results"
        self.output_path = self.result_dir / "codeql.sarif.json"
        self.log_path = self.result_dir / "codeql.log"

    def _run_cmd(self, cmd: list[str], log_file):
        subprocess.run(cmd, check=True, stdout=log_file, stderr=log_file)

    def run_codeql(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Download the query pack (ensures it's available locally)
            with self.log_path.open("w") as log_file:
                self._run_cmd([
                    "codeql", "pack", "download", self.query_pack
                ], log_file)

            # Step 2: Create a CodeQL database from the source code
                self._run_cmd([
                    "codeql", "database", "create", str(self.db_path),
                    f"--language={self.language}",
                    "--source-root", str(self.repo_path)
                ], log_file)

            # Step 3: Analyze the database and output the results as SARIF
                self._run_cmd([
                    "codeql", "database", "analyze", str(self.db_path),
                    self.query_pack,
                    "--format=sarifv2.1.0",
                    "--output", str(self.output_path)
                ], log_file)

        except subprocess.CalledProcessError:
            raise CodeQLExecutionError()

        return self.output_path