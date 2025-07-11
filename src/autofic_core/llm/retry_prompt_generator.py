from autofic_core.llm.prompt_generator import PromptGenerator
from autofic_core.sast.semgrep_snippet import SemgrepSnippet
from typing import List


class RetryPromptGenerator:
    def __init__(self):
        self.prompt_generator = PromptGenerator()

    def generate_prompts(self, diffs: List[dict]) -> List[PromptGenerator.PromptWithSnippet]:
        retry_prompts = []

        for diff in diffs:
            snippet = SemgrepSnippet(
                path=str(diff["source_path"]),
                start_line=diff["start_line"],
                code=diff["diff_content"]
            )
            prompt = self.prompt_generator.generate_prompt(snippet)
            retry_prompts.append(prompt)

        return retry_prompts
