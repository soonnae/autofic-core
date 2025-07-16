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
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path 
        self.template = RetryPromptTemplate(
            title="패치 후 전체 파일 검증 (LLM 재분석)",
            content=(
                "다음은 JavaScript 코드 파일입니다. 이 파일에서 보안 취약점을 찾아 수정하세요.\n\n"
                "```javascript\n"
                "{input}\n"
                "```\n\n"
                "💡 다음 지침을 반드시 지켜서 수정해 주세요:\n"
                "- 전체 파일 중 **취약한 부분만 최소한으로 수정**해 주세요.\n"
                "- **기존 줄 번호, 들여쓰기, 코드 정렬**은 원본 그대로 유지해 주세요.\n"
                "- **취약점과 무관한 부분은 절대로 수정하지 마세요.**\n"
                "- 최종 결과는 **전체 파일 코드**로 출력해 주세요.\n"
                "- 이 코드는 diff 기반 자동 패치로 적용될 예정이므로, 원본 구조 변경이 생기면 적용이 실패할 수 있습니다.\n\n"
                "📝 출력 형식 예시:\n"
                "1. 취약점 설명: ...\n"
                "2. 예상 위험: ...\n"
                "3. 개선 방안: ...\n"
                "4. 최종 수정된 전체 코드:\n"
                "```javascript\n"
                "// 전체 파일이지만 수정은 필요한 부분만 최소로 되어 있어야 합니다\n"
                "...전체 코드...\n"
                "```\n"
                "5. 참고사항: (선택사항)\n"
            ),
        )

    def collect_js_files(self) -> List[Path]:
        exts = ["*.js", "*.jsx", "*.ts", "*.tsx"]
        files = []
        for ext in exts:
            files.extend(self.repo_path.rglob(ext))
        files = [f for f in files if not f.name.endswith(('.min.js', '.test.js', '.bundle.js'))]
        return files

    def generate_prompt(self, file_path: Path) -> GeneratedRetryPrompt:
        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"[ERROR] {file_path} 읽기 실패: {e}")

        rendered_prompt = self.template.content.format(input=code)
        return GeneratedRetryPrompt(
            title=self.template.title,
            prompt=rendered_prompt,
            path=str(file_path.relative_to(self.repo_path))
        )

    def generate_prompts(self) -> List[GeneratedRetryPrompt]:
        return [self.generate_prompt(p) for p in self.collect_js_files()]
    
    def get_unique_file_paths(self, prompts: List[GeneratedRetryPrompt]) -> List[str]:
        seen = set()
        unique = []
        for prompt in prompts:
            if prompt.path not in seen:
                unique.append(prompt.path)
                seen.add(prompt.path)
        return sorted(unique)