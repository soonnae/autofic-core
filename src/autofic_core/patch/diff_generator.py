import difflib
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
from autofic_core.errors import DiffGenerationError 

class DiffResult(BaseModel):
    filename: str
    diff: str
    success: bool
    error: Optional[str] = None
    saved_path: Optional[str] = None

class DiffGenerator:
    def __init__(self, downloaded_dir: str = "artifacts/downloaded_repo", diff_dir: str = "artifacts/diffs"):
        base_dir = Path(__file__).resolve().parents[2] 
        self.downloaded_dir = base_dir / downloaded_dir
        self.diff_dir = base_dir / diff_dir
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    def generate_diff(self, relative_path: str, modified_code: str) -> DiffResult:
        original_path = self.downloaded_dir / relative_path
        try:
            if not original_path.exists():
                raise FileNotFoundError(f"\uacbd\ub8e8 \ud30c\uc77c \uc5c6\uc74c: {original_path}")

            original_lines = original_path.read_text(encoding="utf-8").splitlines()
            modified_lines = modified_code.strip().splitlines()

            diff_lines = list(difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
                lineterm=""
            ))

            diff_text = "\n".join(diff_lines)
            return DiffResult(filename=relative_path, diff=diff_text, success=True)

        except Exception as e:
            raise DiffGenerationError(filename=relative_path, reason=str(e))

    def save_diff(self, result: DiffResult) -> Optional[Path]:
        if not result.success or not result.diff.strip():
            return None

        flat_name = result.filename.replace("/", "__")
        diff_path = self.diff_dir / f"{flat_name}.diff"
        diff_path.write_text(result.diff, encoding="utf-8")
        result.saved_path = str(diff_path)
        return diff_path