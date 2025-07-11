from autofic_core.llm.prompt_generator import GeneratedPrompt
from autofic_core.sast.semgrep_preprocessor import SemgrepFileSnippet
from typing import List


class RetryPromptGenerator:
    def __init__(self):
        self.prompt_generator = GeneratedPrompt()

    def generate_prompts(self, diffs: List[dict]) -> List[GeneratedPrompt]:
        retry_prompts = []

        for diff in diffs:
            snippet = SemgrepFileSnippet(
                path=str(diff["source_path"]),
                start_line=diff["start_line"],
                code=diff["diff_content"]
            )
            prompt = self.prompt_generator.generate_prompt(snippet)
            retry_prompts.append(prompt)

        return retry_prompts
