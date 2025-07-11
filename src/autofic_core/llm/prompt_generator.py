from typing import List
from pydantic import BaseModel
from autofic_core.sast.snippet import BaseSnippet 
from autofic_core.sast.semgrep.preprocessor import SemgrepPreprocessor
from autofic_core.sast.codeql.preprocessor import CodeQLPreprocessor
from autofic_core.sast.snykcode.preprocessor import SnykCodePreprocessor
from autofic_core.sast.merger import merge_snippets_by_file
from autofic_core.errors import (
    PromptGenerationException,
    PromptGeneratorErrorCodes,
    PromptGeneratorErrorMessages,
)


class PromptTemplate(BaseModel):
    title: str
    content: str

    def render(self, file_snippet: BaseSnippet) -> str:
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
            f"위치: {file_snippet.start_line} ~ {file_snippet.end_line} (이 범위의 코드만 수정하세요)\n\n"
        )

        escaped_input = file_snippet.input

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
    snippet: BaseSnippet


class PromptGenerator:
    def __init__(self):
        self.template = PromptTemplate(
            title="취약한 코드 스니펫 리팩토링 (파일 단위)",
            content=(
                "다음은 JavaScript 코드 파일입니다. 이 파일에서 보안 취약점이 발견되었습니다.\n\n"
                "```javascript\n"
                "{input}\n"
                "```\n\n"
                "발견된 취약점:\n\n"
                "{vulnerabilities}"
                "💡 다음 지침을 반드시 지켜서 수정해 주세요:\n"
                "- 전체 파일 중 **취약한 부분만 최소한으로 수정**해 주세요.\n"
                "- **기존 줄 번호, 들여쓰기, 코드 정렬**은 원본 그대로 유지해 주세요.\n"
                "- **취약점과 무관한 부분은 절대로 수정하지 마세요.**\n"
                "- 최종 결과는 **전체 파일 코드**로 출력해 주세요.\n"
                "- 이 코드는 diff 기반 자동 패치로 적용될 예정이므로, 원본 구조 변경이 생기면 적용이 실패할 수 있습니다.\n\n"
                "📝 출력 형식 예시:\n"
                "1. 취약점 설명: ...\n"
                "2. 예상 위험: ...\n"
                "3. 개선 방안: ...\n"
                "4. 최종 수정된 전체 코드:\n"
                "```javascript\n"
                "// 전체 파일이지만 수정은 필요한 부분만 최소로 되어 있어야 합니다\n"
                "...전체 코드...\n"
                "```\n"
                "5. 참고사항: (선택사항)\n"
            ),
        )

    def generate_prompt(self, file_snippet: BaseSnippet) -> GeneratedPrompt:
        if not isinstance(file_snippet, BaseSnippet):
            raise TypeError(f"[ERROR] generate_prompt: 잘못된 타입 전달됨: {type(file_snippet)}")
        rendered_prompt = self.template.render(file_snippet)
        return GeneratedPrompt(
            title=self.template.title,
            prompt=rendered_prompt,
            snippet=file_snippet,
        )

    def generate_prompts(self, file_snippets: List[BaseSnippet]) -> List[GeneratedPrompt]:
        prompts = []
        for idx, snippet in enumerate(file_snippets):
            if isinstance(snippet, dict):
                snippet = BaseSnippet(**snippet)
            elif not isinstance(snippet, BaseSnippet):
                raise TypeError(f"[ ERROR ] generate_prompts: index {idx} 에서 잘못된 타입: {type(snippet)}")
            prompts.append(self.generate_prompt(snippet))
        return prompts


    def get_preprocessor(self, tool: str):
        if tool == "semgrep":
            return SemgrepPreprocessor
        elif tool == "codeql":
            return CodeQLPreprocessor
        elif tool == "snykcode":
            return SnykCodePreprocessor
        # elif tool == "eslint":
        #     return ESLintPreprocessor
        else:
            raise ValueError(f"[ERROR] 지원하지 않는 도구입니다: {tool}")
        
    def from_sast_file(self, sast_result_path: str, base_dir: str = ".", tool: str = "semgrep") -> List[GeneratedPrompt]:
        try:
            preprocessor = self.get_preprocessor(tool)
            file_snippets = preprocessor.preprocess(sast_result_path, base_dir=base_dir)
            merged_snippets = merge_snippets_by_file(file_snippets)
            return self.generate_prompts(merged_snippets)

        except Exception:
            import traceback
            print("[ DEBUG ] PromptGenerator.from_sast_file() 예외 발생:")
            traceback.print_exc()
            raise

    def get_unique_file_paths(self, file_snippets: List[BaseSnippet]) -> List[str]:
        paths = set()
        for idx, snippet in enumerate(file_snippets):
            if isinstance(snippet, dict):
                snippet = BaseSnippet(**snippet)
            elif not isinstance(snippet, BaseSnippet):
                raise TypeError(f"[ ERROR ] get_unique_file_paths: index {idx} 의 타입 오류: {type(snippet)}")
            paths.add(snippet.path)
        return sorted(paths)