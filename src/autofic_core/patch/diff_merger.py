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

from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import shutil
import re

# 예: patch_023_core_appHandler.patch → (23, 'core_appHandler')
PATCH_FILENAME_PATTERN = re.compile(r"patch_(\d{3})_(.+)\.patch$")


class DiffMerger:
    def __init__(self, diffs: List[Path], clone_path: Path, result_path: Path):
        self.diffs = diffs  # patch 파일 경로 리스트
        self.clone_path = clone_path
        self.result_path = result_path

    def parse_patch_filename(self, path: Path) -> tuple[int, str]:
        match = PATCH_FILENAME_PATTERN.match(path.name)
        if not match:
            raise ValueError(f"[PARSE ERROR] 잘못된 patch 파일명 형식: {path.name}")
        start_line = int(match.group(1))
        flat_filename = match.group(2)
        return start_line, flat_filename

    def flatten_to_relative_path(self, flat_name: str) -> Path:
        parts = flat_name.split("_")
        return Path(*parts[:-1]) / parts[-1]

    def try_find_source_file(self, relative_path: Path) -> Path | None:
        for ext in ['.js', '.py', '.ts', '.java']:
            candidate = (self.clone_path / relative_path).with_suffix(ext)
            if candidate.exists():
                return candidate
        return None

    def group_and_sort_diffs(self) -> Dict[str, List[dict]]:
        grouped = defaultdict(list)
        for patch_path in self.diffs:
            try:
                start_line, flat_filename = self.parse_patch_filename(patch_path)
                relative_path = self.flatten_to_relative_path(flat_filename)
                source_path = self.try_find_source_file(relative_path)

                if not source_path:
                    print(f"[ WARN ] 원본 파일이 존재하지 않음: {self.clone_path / relative_path}")
                    continue

                grouped[flat_filename].append({
                    "start_line": start_line,
                    "flat_filename": flat_filename,
                    "source_path": source_path,
                    "diff_content": patch_path.read_text(encoding="utf-8")
                })
            except Exception as e:
                print(f"[ ERROR ] patch 파일 처리 실패: {patch_path.name} - {e}")

        for filename in grouped:
            grouped[filename].sort(key=lambda d: d["start_line"])
        return grouped

    def prepare_target_files(self, grouped_diffs: Dict[str, List[dict]]) -> Dict[str, Path]:
        filename_to_target_path = {}

        for filename, diffs in grouped_diffs.items():
            source_path = diffs[0]["source_path"]
            relative_path = source_path.relative_to(self.clone_path)
            target_path = self.result_path / relative_path

            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

            filename_to_target_path[filename] = target_path

        return filename_to_target_path

    def apply_unified_diff(self, file_path: Path, diff_text: str):
        import difflib

        original = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        patched = list(difflib.restore(difflib.ndiff(original, diff_text.splitlines(keepends=True)), 2))
        file_path.write_text("".join(patched), encoding="utf-8")

    def merge_all(self) -> None:
        grouped = self.group_and_sort_diffs()
        target_paths = self.prepare_target_files(grouped)
        
        for filename, diffs in grouped.items():
            target_path = target_paths[filename]
            combined_diff = "\n".join(diff["diff_content"] for diff in diffs)

        try:
            self.apply_unified_diff(file_path=target_path, diff_text=combined_diff)
        except Exception as e:
            print(f"[ ERROR ] diff apply failed on {target_path.name}: {e}")

