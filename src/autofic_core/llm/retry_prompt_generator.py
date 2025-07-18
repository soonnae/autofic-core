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

from typing import List
from pydantic import BaseModel
from pathlib import Path

class RetryPromptTemplate(BaseModel):
    title: str
    content: str

class GeneratedRetryPrompt(BaseModel):
    title: str
    prompt: str
    path: str 

class RetryPromptGenerator:
    def __init__(self, parsed_dir: Path):
        self.parsed_dir = parsed_dir
        self.template = RetryPromptTemplate(
            title="Post-patch File Verification (LLM Re-analysis)",
            content=(
                "The following is a JavaScript source file. Please identify and fix any security vulnerabilities.\n\n"
                "```javascript\n"
                "{input}\n"
                "```\n\n"
                "💡 Please strictly follow the guidelines below when modifying the code:\n"
                "- Modify **only the vulnerable parts** of the file with **minimal changes**.\n"
                "- Preserve the **original line numbers, indentation, and code formatting** exactly.\n"
                "- **Do not modify any part of the file that is unrelated to the vulnerabilities.**\n"
                "- Output the **entire file**, not just the changed lines.\n"
                "- This code will be used for diff-based automatic patching, so structural changes may cause the patch to fail.\n\n"
                "📝 Output format example:\n"
                "1. Vulnerability Description: ...\n"
                "2. Potential Risk: ...\n"
                "3. Recommended Fix: ...\n"
                "4. Final Modified Code:\n"
                "```javascript\n"
                "// Entire file content, but only vulnerable parts should be modified minimally\n"
                "...entire code...\n"
                "```\n"
                "5. Additional Notes: (optional)\n"
            ),
        )

    def generate_prompt(self, file_path: Path) -> GeneratedRetryPrompt:
        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"[ERROR] Failed to read {file_path}: {e}")

        rendered_prompt = self.template.content.format(input=code)
        return GeneratedRetryPrompt(
            title=self.template.title,
            prompt=rendered_prompt,
            path=str(file_path.relative_to(self.parsed_dir))
        )

    def generate_prompts(self) -> List[GeneratedRetryPrompt]:
        parsed_files = sorted(self.parsed_dir.glob("*.parsed")) 
        return [self.generate_prompt(file) for file in parsed_files]
    
    def get_unique_file_paths(self, prompts: List[GeneratedRetryPrompt]) -> List[str]:
        seen = set()
        unique = []
        for prompt in prompts:
            if prompt.path not in seen:
                unique.append(prompt.path)
                seen.add(prompt.path)
        return sorted(unique)