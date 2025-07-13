import subprocess
from pathlib import Path
import click

class PatchApplier:
    def __init__(self, patch_dir: Path, repo_dir: Path):
        self.patch_dir = patch_dir
        self.repo_dir = repo_dir
        self.parsed_dir = patch_dir.parent / "parsed"

    def apply_all(self):
        patch_files = sorted(self.patch_dir.glob("*.diff"))

        if not patch_files:
            click.secho(f"[ WARN ] {self.patch_dir} 에 .diff 파일이 없습니다.", fg="yellow")
            return False

        all_success = True
        for patch_file in patch_files:
            success = self._apply_single_patch(patch_file)
            if not success:
                all_success = False

        return all_success

    def _apply_single_patch(self, patch_file: Path) -> bool:
        try:
            result = subprocess.run(
                ["git", "apply", str(patch_file)],
                cwd=self.repo_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                click.secho(f"[ SUCCESS ] 패치 적용 완료 : {patch_file.name}", fg="green")
                return True
            else:
                click.secho(f"[ WARN ] 기본 패치 실패, fallback 시도: {patch_file.name}", fg="yellow")
                click.secho(result.stderr, fg="yellow")
                return self._apply_fallback_patch(patch_file)

        except Exception as e:
            click.secho(f"[ ERROR ] {patch_file.name} 적용 중 예외 발생 : {e}", fg="red")
            return False

    def _apply_fallback_patch(self, patch_file: Path) -> bool:
        file_stem = patch_file.stem.replace("patch_", "")  
        relative_parts = file_stem.split("_") 
        original_rel_path = Path(*relative_parts)  

        original_file = self.repo_dir / original_rel_path
        parsed_file = self.parsed_dir / original_rel_path

        if not original_file.exists():
            click.secho(f"[ ERROR ] 원본 파일 없음 → {original_file}", fg="red")
            return False

        if not parsed_file.exists():
            click.secho(f"[ ERROR ] parsed 파일 없음 → {parsed_file}", fg="red")
            return False

        fallback_diff = self.patch_dir / f"fallback_{file_stem}.diff"

        try:
            with open(fallback_diff, "w", encoding="utf-8") as f:
                subprocess.run(
                    ["git", "diff", "--no-index", str(original_file), str(parsed_file)],
                    check=True,
                    text=True,
                    stdout=f,
                    stderr=subprocess.DEVNULL
                )

            result = subprocess.run(
                ["git", "apply", str(fallback_diff)],
                cwd=self.repo_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                click.secho(f"[ SUCCESS ] fallback diff 적용 완료 : {fallback_diff.name}", fg="green")
                return True
            else:
                click.secho(f"[ FAIL ] fallback diff 적용 실패 : {fallback_diff.name}", fg="red")
                click.secho(result.stderr, fg="red")
                return False

        except Exception as e:
            click.secho(f"[ ERROR ] fallback diff 생성 실패 : {e}", fg="red")
            return False