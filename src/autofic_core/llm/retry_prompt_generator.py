from autofic_core.llm.prompt_generator import PromptGenerator, GeneratedPrompt
from autofic_core.sast.semgrep_preprocessor import SemgrepFileSnippet
from typing import List, Dict



class RetryPromptGenerator:
    def __init__(self):
        self.prompt_generator = PromptGenerator()

    def generate_prompts(self, diffs: List[dict]) -> List[GeneratedPrompt]:
        retry_prompts = []

        for diff in diffs:
            start_line, source_path, diff_content = diff

            # 필수 필드 맞춰서 객체 생성
            snippet = SemgrepFileSnippet(
                input="LLM Retry",
                start_line=start_line,
                end_line=start_line + diff_content.count("\n"),
                message="",  # 기본값
                vulnerability_class=[],
                cwe=[],
                severity="",
                references=[],
                path=str(source_path),
                snippet=diff_content  # 내용도 snippet에 넣어야 해요!
            )

            prompt = self.prompt_generator.generate_prompt(snippet)
            retry_prompts.append(prompt)
        return retry_prompts
    
    def load_diffs(self) -> List[Dict]:
        diff_files = sorted(self.patch_dir.glob("*.diff"))
        diffs = []

        for diff_file in diff_files:
            # diff_file.stem → 'appHandler' (확장자 제외한 파일명)
            diffs.append({
                "source_path": diff_file.stem + ".js",  # 파일명 기반으로 경로 추정
                "start_line": 0,  # 줄 번호는 기본값 0 (정확한 정보가 없으므로)
                "diff_content": diff_file.read_text(encoding="utf-8")
            })

        return diffs

