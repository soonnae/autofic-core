from pathlib import Path
import re

class DiffGenerator:
    def __init__(self, repo_dir: Path, diff_dir: Path):
        self.repo_dir = repo_dir    # 원본 코드 저장소 루트 경로
        self.diff_dir = diff_dir    # diff 파일들이 저장된 경로

    def get_diff_files(self):
        """
        diff 디렉토리 내 .patch 파일을 모두 반환
        """
        return list(self.diff_dir.glob("*.patch"))

    def parse_diff_filename(self, diff_filename: str) -> tuple[int, str]:
        """
        patch_023_core_appHandler.js.patch → (23, 'core_appHandler.js') 추출
        """
        m = re.match(r"patch_(\d{3})_(.+)\.patch$", diff_filename)
        if not m:
            raise ValueError(f"[ ERROR ] 잘못된 diff 파일명 형식: {diff_filename}")

        start_line = int(m.group(1))
        flatten_name = m.group(2)
        return start_line, flatten_name

    def flatten_to_relative_path(self, flat_name: str) -> Path:
        """
        예: 'core_appHandler.js' → Path('core/appHandler.js')
        """
        parts = flat_name.split("_")
        return Path(*parts[:-1]) / parts[-1]

    def load_diffs(self):
        """
        diff 디렉토리의 모든 patch 파일을 불러와서
        적용 가능한 diff 정보를 리스트로 반환
        """
        diff_files = self.get_diff_files()
        diffs = []

        for diff_file in diff_files:
            try:
                start_line, flat_filename = self.parse_diff_filename(diff_file.name)
                source_path = self.repo_dir / self.flatten_to_relative_path(flat_filename)

                if not source_path.exists():
                    print(f"[ WARN ] 원본 파일이 없습니다: {source_path}")
                    continue

                diff_content = diff_file.read_text(encoding="utf-8")

                diffs.append({
                    "start_line": start_line,
                    "flat_filename": flat_filename,
                    "source_path": source_path,
                    "diff_content": diff_content,
                })
            except Exception as e:
                print(f"[ ERROR ] diff 파일 처리 실패: {diff_file.name} - {e}")

        return diffs
