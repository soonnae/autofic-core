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

import subprocess
from pathlib import Path
import click

class PatchApplier:
    def __init__(self, patch_dir: Path, repo_dir: Path):
        self.patch_dir = patch_dir
        self.repo_dir = repo_dir

    def apply_all(self):
        patch_files = sorted(self.patch_dir.glob("*.diff"))

        if not patch_files:
            click.secho(f"[ WARN ] {self.patch_dir} 에 .diff 파일이 없습니다.", fg="yellow")
            return

        for patch_file in patch_files:
            self._apply_single_patch(patch_file)

    def _apply_single_patch(self, patch_file: Path):
        try:
            result = subprocess.run(
                ["git", "apply", str(patch_file)],
                cwd=self.repo_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                click.secho(f"[ SUCCESS ] 패치 적용 완료 : {patch_file.name}", fg="green")
            else:
                click.secho(f"[ ERROR ] 패치 적용 실패 : {patch_file.name}", fg="red")
                click.secho(f"{result.stderr}", fg="red")

        except Exception as e:
            click.secho(f"[ ERROR ] {patch_file.name} 적용 중 예외 발생 : {e}", fg="red")