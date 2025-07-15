
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

from autofic_core.llm.prompt_generator import PromptGenerator, GeneratedPrompt
from autofic_core.sast.snippet import BaseSnippet
from pathlib import Path
from typing import List
import re

class RetryPromptGenerator:
    def __init__(self, patch_dir: Path, md_dir: Path):
        self.patch_dir = patch_dir
        self.md_dir = md_dir
        self.prompt_generator = PromptGenerator()

    def extract_code_from_md(self, md_path: Path) -> str:
        content = md_path.read_text(encoding="utf-8")
        match = re.search(r"```javascript\n(.*?)```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            raise ValueError(f"[ERROR] {md_path.name} 에서 코드 블록 추출 실패")

    def load_diffs(self, output_type: str = "semgrep") -> List[BaseSnippet]:
        snippets = []
        for diff_path in sorted(self.patch_dir.glob("*.diff")):
            try:
                content = diff_path.read_text(encoding="utf-8")

                # 파일 경로 추출 (e.g., +++ b/src/foo.js → src/foo.js)
                file_match = re.search(r"\+\+\+ b/(.+)", content)
                path = file_match.group(1) if file_match else diff_path.stem + ".js"

                # diff에서 시작 줄 추출 (e.g., @@ -2,5 +3,6 @@ → 3)
                hunk_match = re.search(r"\@\@ -\d+(,\d+)? \+(\d+)", content)
                start_line = int(hunk_match.group(2)) if hunk_match else 0

                # 대응되는 .md에서 코드 블록 추출
                md_file = self.md_dir / f"response_{diff_path.stem}.md"
                try:
                    extracted_code = self.extract_code_from_md(md_file)
                except Exception:
                    extracted_code = ""

                # 프롬프트 input을 diff + 코드로 구성
                prompt_input = f"수정된 코드:\n```javascript\n{extracted_code}\n```\n\n수정 근거(diff):\n{content}"

                snippet = BaseSnippet(
                    input=prompt_input,
                    start_line=start_line,
                    end_line=start_line + content.count("\n"),
                    message="GPT 재분석을 위한 diff + 수정코드 기반 요청입니다.",
                    vulnerability_class=["LLM Retry"],
                    cwe=[],
                    severity="중간",
                    references=[],
                    path=path,
                    snippet=extracted_code or content,
                )
                snippets.append(snippet)

            except Exception as e:
                print(f"[ ERROR ] {diff_path.name} 읽기 실패 - {e}")
        return snippets

    def generate_prompts(self, snippets: List[BaseSnippet]) -> List[GeneratedPrompt]:
        return self.prompt_generator.generate_prompts(snippets)