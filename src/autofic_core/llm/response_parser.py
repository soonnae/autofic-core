import re
from typing import List, Optional, Union
from pydantic import BaseModel
from pathlib import Path
from autofic_core.errors import AutoficError  

class ParsedCodeBlock(BaseModel):
    language: str
    code: str
    filename: Optional[str] = None

class LLMResponseParser:
    @staticmethod
    def extract_code_blocks(response: str) -> List[ParsedCodeBlock]:
        pattern = r"```(\w+)\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        code_blocks = []
        for language, code in matches:
            filename = LLMResponseParser.extract_filename(code)
            code_blocks.append(
                ParsedCodeBlock(language=language, code=code.strip(), filename=filename)
            )
        return code_blocks

    @staticmethod
    def extract_filename(code: str) -> Optional[str]:
        filename_pattern = r"(?:\/\/|#|\/\*)\s*filename:\s*(.+?)(?:\s|\*\/|$)"
        match = re.search(filename_pattern, code)
        return match.group(1).strip() if match else None

    @staticmethod
    def load_and_parse(path: Union[str, Path]) -> List[ParsedCodeBlock]:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return LLMResponseParser.extract_code_blocks(content)
        except Exception as e:
            raise AutoficError(f"[LLM 응답 파일 로딩 실패] {path}: {e}")
