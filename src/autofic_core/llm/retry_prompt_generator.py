from autofic_core.sast.snippet import BaseSnippet
from autofic_core.llm.prompt_generator import PromptGenerator, GeneratedPrompt
from typing import List


class RetryPromptGenerator:
    def __init__(self):
        self.prompt_generator = PromptGenerator()

    def generate_prompts(self, diffs: List[dict]) -> List[GeneratedPrompt]:
        retry_prompts = []

        for diff in diffs:
            snippet = BaseSnippet(
                path=str(diff["source_path"]),
                start_line=diff["start_line"],
                code=diff["diff_content"]
            )
            prompt = self.prompt_generator.generate_prompt(snippet)
            retry_prompts.append(prompt)

        return retry_prompts
