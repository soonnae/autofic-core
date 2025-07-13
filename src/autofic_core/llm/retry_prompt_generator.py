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
