import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class SnykCodeResult(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    result_path: Optional[str] = None


class SnykCodeRunner:

    def __init__(self, repo_path: Path):

        self.repo_path = Path(repo_path).resolve()
        self.snyk_token = os.environ.get("SNYK_TOKEN")

    def run_snykcode(self) -> SnykCodeResult:

        snyk_cmd, use_shell, prepend_node = self._resolve_snyk_command()

        if not self.snyk_token:
            raise EnvironmentError("SNYK_TOKEN environment variable not set.")

        self._ensure_config()

        # 환경 변수 설정
        env = os.environ.copy()
        env["SNYK_TOKEN"] = self.snyk_token

        # 인증 수행
        self._ensure_authenticated(snyk_cmd, env)

        # 분석 명령어 구성
        cmd = [snyk_cmd, "code", "test", "--json"]
        if prepend_node:
            cmd.insert(0, "node")

        try:
            result = subprocess.run(
                cmd if not use_shell else " ".join(cmd),
                cwd=self.repo_path,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                shell=use_shell
            )
            output_path = self.repo_path / "snyk_result.sarif.json"
            output_path.write_text(result.stdout, encoding="utf-8")

            return SnykCodeResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                result_path=str(output_path) 
            )
        except subprocess.CalledProcessError as err:
            return SnykCodeResult(
                stdout=err.stdout,
                stderr=err.stderr,
                returncode=err.returncode
            )

    def _ensure_authenticated(self, snyk_cmd: str, env: dict) -> None:
        """
        Runs 'snyk config set api=...' to store token in config, mimicking `snyk auth`.
        """
        subprocess.run(
            [snyk_cmd, "config", "set", f"api={self.snyk_token}"],
            env=env,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False
        )

    def _ensure_config(self) -> None:
        config_path = self.repo_path / ".snyk"
        if not config_path.exists():
            config_path.write_text("# empty config\n")

    def _resolve_snyk_command(self) -> tuple[str, bool, bool]:
        # 1. 환경 변수로 지정된 경로 우선
        env_path = os.getenv("SNYK_CMD_PATH")
        if env_path and Path(env_path).exists():
            return env_path, env_path.endswith(".cmd"), env_path.endswith(".js")

        # 2. PATH 검색
        for candidate in ["snyk.cmd", "snyk.exe", "snyk"]:
            path = shutil.which(candidate)
            if path:
                return path, candidate.endswith(".cmd"), False

        # 3. npm 글로벌 경로 fallback
        try:
            npm_bin = subprocess.check_output(["npm", "bin", "-g"], text=True).strip()
            for fallback in ["snyk.cmd", "snyk"]:
                fallback_path = Path(npm_bin) / fallback
                if fallback_path.exists():
                    return str(fallback_path), fallback_path.suffix == ".cmd", False
        except Exception:
            pass
