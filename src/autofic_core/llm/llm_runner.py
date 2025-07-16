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

import os
import click
from pathlib import Path
from openai import OpenAI
from typing import Any
from dotenv import load_dotenv
from autofic_core.errors import LLMExecutionError
from autofic_core.sast.merger import merge_snippets_by_file
from autofic_core.llm.prompt_generator import PromptGenerator

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class LLMRunner:
    def __init__(self, model="gpt-4o"):
        self.model = model

    def run(self, prompt: str) -> str:
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security code fixer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            click.echo(f"[LLM ERROR] 모델 요청 실패 - {e}")
            raise LLMExecutionError(str(e))


def save_md_response(content: str, prompt_obj: Any, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if hasattr(prompt_obj, "snippet"):
            path = Path(prompt_obj.snippet.path)
        else:
            path = Path(prompt_obj.path)
    except Exception as e:
        raise RuntimeError(f"[ERROR] 저장 경로 추출 실패: {e}")
    
    parts = path.parts

    # artifacts, downloaded_repo 같은 상위 디렉토리 제거
    while parts and parts[0] in ("artifacts", "downloaded_repo"):
        parts = parts[1:]

    flat_path = "_".join(parts)

    # 숫자 부분 제거 (start_line 사용 안 함)
    base_name = f"response_{flat_path}"
    output_path = output_dir / f"{base_name}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return str(output_path)

def run_llm_for_semgrep_results(
    semgrep_json_path: str,
    output_dir: Path,
    tool: str = "semgrep",
    model: str = "gpt-4o",
) -> None:
    
    if tool == "semgrep":
        from autofic_core.sast.semgrep.preprocessor import SemgrepPreprocessor as Preprocessor
    elif tool == "codeql":
        from autofic_core.sast.codeql.preprocessor import CodeQLPreprocessor as Preprocessor
    elif tool == "snykcode":
        from autofic_core.sast.snykcode.preprocessor import SnykCodePreprocessor as Preprocessor
    else:
        raise ValueError(f"지원되지 않는 SAST 도구: {tool}")
    
    # Semgrep 결과 JSON에서 스니펫 추출
    raw_snippets = Preprocessor.preprocess(semgrep_json_path)
    # 위치 기준으로 스니펫 병합
    merged_snippets = merge_snippets_by_file(raw_snippets)

    # 프롬프트 생성
    prompt_generator = PromptGenerator()
    prompts = prompt_generator.generate_prompts(merged_snippets)

    runner = LLMRunner(model=model)

    # 프롬프트별로 LLM 실행 및 응답 저장
    for generated_prompt in prompts:
        try:
            click.echo(f"[DEBUG] Prompt 길이 (문자 수): {len(generated_prompt.prompt)}")
            response = runner.run(generated_prompt.prompt)
            save_md_response(response, generated_prompt, output_dir)
        except LLMExecutionError as e:
            click.echo(f"[ERROR] LLM 처리 실패: {e}")