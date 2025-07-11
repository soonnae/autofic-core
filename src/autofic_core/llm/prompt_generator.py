from typing import List
from pydantic import BaseModel
from autofic_core.sast.semgrep_preprocessor import SemgrepPreprocessor, SemgrepFileSnippet
from autofic_core.sast.semgrep_merger import merge_snippets_by_file  # 병합 함수 임포트
from autofic_core.errors import (
    PromptGenerationException,
    PromptGeneratorErrorCodes,
    PromptGeneratorErrorMessages,
)


class PromptTemplate(BaseModel):
    title: str
    content: str

    def render(self, file_snippet: SemgrepFileSnippet) -> str:
        if not file_snippet.input.strip():
            raise PromptGenerationException(
                PromptGeneratorErrorCodes.EMPTY_SNIPPET,
                PromptGeneratorErrorMessages.EMPTY_SNIPPET,
            )

        vulnerabilities_str = (
            f"유형: {', '.join(file_snippet.vulnerability_class) or '알 수 없음'}\n"
            f"CWE: {', '.join(file_snippet.cwe) or '해당 없음'}\n"
            f"설명: {file_snippet.message or '없음'}\n"
            f"심각도: {file_snippet.severity or '정보 없음'}\n"
            f"위치: {file_snippet.start_line} ~ {file_snippet.end_line}\n\n"
        )

        escaped_input = file_snippet.input.replace("{", "{{").replace("}", "}}")

        try:
            return self.content.format(
                input=escaped_input,
                vulnerabilities=vulnerabilities_str,
            )
        except Exception as e:
            print(f"[DEBUG] PromptTemplate.render() 예외: {e}")
            raise PromptGenerationException(
                PromptGeneratorErrorCodes.TEMPLATE_RENDER_ERROR,
                PromptGeneratorErrorMessages.TEMPLATE_RENDER_ERROR,
            )


class GeneratedPrompt(BaseModel):
    title: str
    prompt: str
    snippet: SemgrepFileSnippet


class PromptGenerator:
    def __init__(self):
        self.template = PromptTemplate(
            title="취약한 코드 스니펫 리팩토링 (파일 단위)",
            content=(
                "다음은 파일 전체 코드입니다:\n\n"
                "```javascript\n"
                "{input}\n"
                "```\n\n"
                "이 파일에서 다음 취약점들이 발견되었습니다:\n\n"
                "{vulnerabilities}"
                "수정 시 아래를 지켜주세요:\n"
                "- 취약점 부분을 반드시 수정해 주세요.\n"
                "- 전체 코드를 수정된 최종 상태로 보여주세요.\n"
                "- 취약점과 무관한 부분은 변경하지 말아 주세요.\n\n"
                "각 취약점별로 아래 형식에 맞춰 작성해 주세요:\n"
                "1. 취약점 설명:\n"
                "2. 예상 위험:\n"
                "3. 개선 방안:\n"
                "4. 최종 수정된 전체 코드:\n"
                "5. 참고사항:\n"
            ),
        )

    def generate_prompt(self, file_snippet: SemgrepFileSnippet) -> GeneratedPrompt:
        if not isinstance(file_snippet, SemgrepFileSnippet):
            raise TypeError(f"[ERROR] generate_prompt: 잘못된 타입 전달됨: {type(file_snippet)}")
        rendered_prompt = self.template.render(file_snippet)
        return GeneratedPrompt(
            title=self.template.title,
            prompt=rendered_prompt,
            snippet=file_snippet,
        )

    def generate_prompts(self, file_snippets: List[SemgrepFileSnippet]) -> List[GeneratedPrompt]:
        prompts = []
        for idx, snippet in enumerate(file_snippets):
            if isinstance(snippet, dict):
                snippet = SemgrepFileSnippet(**snippet)
            elif not isinstance(snippet, SemgrepFileSnippet):
                raise TypeError(f"[ERROR] generate_prompts: index {idx} 에서 잘못된 타입: {type(snippet)}")
            prompts.append(self.generate_prompt(snippet))
        return prompts

    def from_semgrep_file(self, semgrep_result_path: str, base_dir: str = ".") -> List[GeneratedPrompt]:
        try:
            file_snippets = SemgrepPreprocessor.preprocess(semgrep_result_path, base_dir=base_dir)
            merged_snippets = merge_snippets_by_file(file_snippets)
            return self.generate_prompts(merged_snippets)

        except Exception:
            import traceback
            print("[DEBUG] PromptGenerator.from_semgrep_file() 예외 발생:")
            traceback.print_exc()
            raise

    def get_unique_file_paths(self, file_snippets: List[SemgrepFileSnippet]) -> List[str]:
        paths = set()
        for idx, snippet in enumerate(file_snippets):
            if isinstance(snippet, dict):
                snippet = SemgrepFileSnippet(**snippet)
            elif not isinstance(snippet, SemgrepFileSnippet):
                raise TypeError(f"[ERROR] get_unique_file_paths: index {idx} 의 타입 오류: {type(snippet)}")
            paths.add(snippet.path)
        return sorted(paths)