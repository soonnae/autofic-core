
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
from autofic_core.llm.prompt_generator import PromptGenerator
from autofic_core.llm.prompt_generator import GeneratedPrompt
from autofic_core.sast.snippet import BaseSnippet
from pathlib import Path
from typing import List

class RetryPromptGenerator:
    def __init__(self, patch_dir: Path):
        self.patch_dir = patch_dir
        self.prompt_generator = PromptGenerator()

    def load_diffs(self, output_type: str = "semgrep") -> List[BaseSnippet]:
        snippets = []
        for diff_path in sorted(self.patch_dir.glob("*.diff")):
            try:
                content = diff_path.read_text(encoding="utf-8")
                snippet = BaseSnippet(
                    input="LLM Retry",
                    start_line=0,
                    end_line=content.count("\n"),
                    message="",
                    vulnerability_class=[],
                    cwe=[],
                    severity="",
                    references=[],
                    path=str(diff_path.stem + ".js"),  # 나중에 도구별 확장 가능
                    snippet=content,
                )
                snippets.append(snippet)
            except Exception as e:
                print(f"[ ERROR ] {diff_path.name} 읽기 실패 - {e}")
        return snippets

    def generate_prompts(self, snippets: List[BaseSnippet]) -> List[GeneratedPrompt]:
        return self.prompt_generator.generate_prompts(snippets)