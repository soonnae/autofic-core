from typing import List
from pydantic import BaseModel
from autofic_core.sast.semgrep_preprocessor import SemgrepSnippet, SemgrepPreprocessor
from autofic_core.errors import (
    PromptGenerationException,
    PromptGeneratorErrorCodes,
    PromptGeneratorErrorMessages,
)

class PromptTemplate(BaseModel):
    title: str
    content: str

    def render(self, snippet: SemgrepSnippet) -> str:
        if not snippet.snippet.strip():
            raise PromptGenerationException (
                PromptGeneratorErrorCodes.EMPTY_SNIPPET,
                PromptGeneratorErrorMessages.EMPTY_SNIPPET,
            )
        
        try:
            return self.content.format (
                input = snippet.input,
                snippet = snippet.snippet,
                vulnerability_class = ", ".join(snippet.vulnerability_class) or "알 수 없음",
                cwe = ", ".join(map(str, snippet.cwe)) or "해당 없음",
                message = snippet.message or "없음",
                severity = snippet.severity or "정보 없음",
            )
        
        except Exception as e:
            raise PromptGenerationException (
                PromptGeneratorErrorCodes.TEMPLATE_RENDER_ERROR,
                PromptGeneratorErrorMessages.TEMPLATE_RENDER_ERROR,
            )

class GeneratedPrompt(BaseModel):
    title: str
    prompt: str
    snippet: SemgrepSnippet

class PromptGenerator:
    def __init__(self):
        self.template = PromptTemplate (
            title = "취약한 코드 스니펫 리팩토링",
            content = ( 
                "다음은 전체 코드입니다 (참고용입니다) :\n\n"
                "```python\n"
                "{input}\n"
                "```\n\n"
                "이 중 다음 스니펫에서 취약점이 발견되었습니다 :\n\n"
                "```python\n"
                "{snippet}\n"
                "```\n\n"
                "### 취약점 정보\n"
                "- 취약점 유형: {vulnerability_class}\n"
                "- CWE : {cwe}\n"
                "- 설명 : {message}\n"
                "- 심각도 : {severity}\n\n"
                "### 요청 사항\n"
                "위 **스니펫 부분만** 수정해주세요. 전체 코드가 아닌 해당 블록만 리팩토링해 주세요.\n\n"
                "아래 형식을 따라 응답해주세요.\n"
                "1. 취약점 설명 :\n"
                "2. 예상 위험 :\n"
                "3. 개선 방안 :\n"
                "4. 수정된 코드 :\n"
                "5. 기타 참고사항 :\n"
            ),
        )

    def generate_prompt(self, snippet: SemgrepSnippet) -> GeneratedPrompt:
        rendered_prompt = self.template.render(snippet)
        return GeneratedPrompt (
            title=self.template.title, prompt=rendered_prompt, snippet=snippet
        )
        

    def generate_prompts(self, snippets: List[SemgrepSnippet]) -> List[GeneratedPrompt]:
        if not isinstance(snippets, list):
            raise PromptGenerationException (
                PromptGeneratorErrorCodes.INVALID_SNIPPET_LIST,
                PromptGeneratorErrorMessages.INVALID_SNIPPET_LIST,
            )
        return [self.generate_prompt(snippet) for snippet in snippets]

    def from_semgrep_file(self, semgrep_result_path: str, base_dir: str = ".") -> List[GeneratedPrompt]:
        snippets = SemgrepPreprocessor().preprocess(semgrep_result_path, base_dir=base_dir)
        return self.generate_prompts(snippets)