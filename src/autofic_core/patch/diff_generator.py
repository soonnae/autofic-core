# =============================================================================
# Copyright 2025 AutoFiC Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

import difflib
from pathlib import Path

class DiffGenerator:
    def __init__(self, repo_dir: Path, parsed_dir: Path, patch_dir: Path):
        self.repo_dir = repo_dir
        self.parsed_dir = parsed_dir
        self.patch_dir = patch_dir

    def generate_diff(self, original: str, modified: str, rel_path: Path) -> str:
        from_path = f"a/{rel_path.as_posix()}"
        to_path = f"b/{rel_path.as_posix()}"
        
        original_lines = [line.rstrip() + '\n' for line in original.splitlines()]
        modified_lines = [line.rstrip() + '\n' for line in modified.splitlines()]
        
        return ''.join(difflib.unified_diff(
            original_lines, modified_lines,
            fromfile=from_path,
            tofile=to_path,
            lineterm="\n"  
        ))

    def run(self):
        self.patch_dir.mkdir(parents=True, exist_ok=True)
        parsed_files = list(self.parsed_dir.rglob("*.*"))  # 하위 폴더 포함 모든 파일 탐색

        for parsed_file in parsed_files:
            if parsed_file.is_dir():
                continue

            try:
                rel_path = parsed_file.relative_to(self.parsed_dir)
                original_file = self.repo_dir / rel_path

                if not original_file.exists():
                    print(f"[ WARN ] 원본 없음 : {original_file}")
                    continue

                original_code = original_file.read_text(encoding="utf-8")
                modified_code = parsed_file.read_text(encoding="utf-8")
                diff_text = self.generate_diff(original_code, modified_code, rel_path)

                if diff_text.strip():
                    diff_name = rel_path.with_suffix('.diff').name
                    diff_path = self.patch_dir / diff_name
                    with open(diff_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(diff_text)
                    print(f"[✓] diff 저장 : {diff_path}")
                else:
                    print(f"[ SKIP ] 변경사항 없음 : {parsed_file.name}")

            except Exception as e:
                print(f"[ ERROR ] diff 생성 실패 : {parsed_file.name} - {e}")

    def load_diffs(self, output_type: str = "semgrep") -> list[tuple[int, Path, str]]:
        diffs = []
        for diff_path in sorted(self.patch_dir.glob("*.diff")):
            try:
                content = diff_path.read_text(encoding="utf-8")
                # start_line 임의로 0 처리 (추후 라인 분석 로직 필요시 개선)
                diffs.append((0, diff_path, content))
            except Exception as e:
                print(f"[ ERROR ] {diff_path.name} 읽기 실패 - {e}")
        return diffs
    