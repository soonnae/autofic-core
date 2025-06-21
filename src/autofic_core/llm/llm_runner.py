# src/autofic_core/llm/llm_runner.py
import os
import openai
from autofic_core.errors import LLMExecutionError
from pathlib import Path
import click

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        
def save_md_response(content: str, output_dir: str, idx: int):
    output_dir = Path("artifacts/llm")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"response_{idx:03}.md"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(output_path)
