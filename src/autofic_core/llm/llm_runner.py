import os
import click
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from autofic_core.errors import LLMExecutionError
from autofic_core.sast.semgrep_preprocessor import SemgrepPreprocessor, SemgrepSnippet
from autofic_core.sast.semgrep_merger import merge_snippets_by_location
from autofic_core.llm.prompt_generator import PromptGenerator

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class LLMRunner:
    def __init__(self, model="gpt-4o"):
        self.model = model

    def run(self, prompt: str) -> str:
        try:
            response = client.chat.completions.create (
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

# LLM 응답 결과 .md 파일로 저장
def save_md_response(content: str, snippet: SemgrepSnippet, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)

    path = Path(snippet.path)
    parts = path.parts

    while parts and parts[0] in ("artifacts", "downloaded_repo"):
        parts = parts[1:]

    flat_path = "_".join(parts)
    base_name = f"response_{flat_path}_{snippet.start_line}"
    output_path = output_dir / f"{base_name}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return str(output_path)


def run_llm_for_semgrep_results(
    semgrep_json_path: str,
    output_dir: Path,
    model: str = "gpt-4o",
) -> None:

    # semgrep 결과 JSON에서 스니펫 추출
    raw_snippets = SemgrepPreprocessor.preprocess(semgrep_json_path)
    # 위치 기준으로 스니펫 병합
    merged_snippets = merge_snippets_by_location(raw_snippets)

    # 프롬프트 생성
    prompt_generator = PromptGenerator()
    prompts = prompt_generator.generate_prompts(merged_snippets)

    runner = LLMRunner(model=model)
    
    # 프롬프트별로 LLM 실행 및 응답 저장
    for generated_prompt in prompts:
        try:
            response = runner.run(generated_prompt.prompt)
            save_md_response(response, generated_prompt.snippet, output_dir)
        except LLMExecutionError as e:
            click.echo(f"[ERROR] LLM 처리 실패: {e}")
