import os
import click
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from autofic_core.errors import LLMExecutionError
from autofic_core.sast.semgrep_preprocessor import SemgrepSnippet

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
        
def save_md_response(content: str, snippet: SemgrepSnippet):
    output_dir = Path("artifacts/llm")
    output_dir.mkdir(parents=True, exist_ok=True)

    path = Path(snippet.path)
    parts = path.parts

    while parts and parts[0] in ("artifacts", "downloaded_repo"):
        parts = parts[1:]

    flat_path = "_".join(parts)
    base_name = f"response_{flat_path}_{snippet.start_line}"
    output_path = output_dir / f"{base_name}.md"

    counter = 2
    while output_path.exists():
        output_path = output_dir / f"{base_name}_{counter}.md"
        counter += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(output_path)
