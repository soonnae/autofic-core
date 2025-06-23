import os
import json
from pathlib import Path
from pydantic import BaseModel, Field

class SemgrepSnippet(BaseModel):
    input: str
    output: str = ""
    idx: int
    start_line: int
    end_line: int
    snippet: str
    message: str
    vulnerability_class: list = Field(default_factory=list)
    cwe: list = Field(default_factory=list)
    severity: str
    references: list = Field(default_factory=list)
    path: str 

class SemgrepPreprocessor(BaseModel):

    @staticmethod
    def read_json_file(path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_json_file(data: dict, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def preprocess(input_json_path: str, base_dir: str = ".") -> list[SemgrepSnippet]:
        results = SemgrepPreprocessor.read_json_file(input_json_path)
        base_dir_path = Path(base_dir).resolve()
        processed: list[SemgrepSnippet] = []

        for idx, result in enumerate(results.get("results", [])):
            raw_path = result.get("path", "").strip().replace("\\", "/")

            # rel_path에서 base_dir 중복 제거
            rel_path = raw_path
            if raw_path.startswith(str(base_dir).replace("\\", "/")):
                rel_path = raw_path[len(str(base_dir).replace("\\", "/")):].lstrip("/")

            file_path = (base_dir_path / rel_path).resolve()

            if not file_path.exists():
                raise FileNotFoundError(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}")

            lines = file_path.read_text(encoding='utf-8').splitlines()
            full_code = "\n".join(lines)
            start_line = result["start"]["line"]
            end_line = result["end"]["line"]
            snippet = "\n".join(lines[start_line - 1:end_line])

            extra = result.get("extra", {})
            meta = extra.get("metadata", {})

            processed.append(SemgrepSnippet(
                input=full_code.strip(),
                output="",
                idx=idx,
                start_line=start_line,
                end_line=end_line,
                snippet=snippet.strip(),
                message=extra.get("message", ""),
                vulnerability_class=meta.get("vulnerability_class", []),
                cwe=meta.get("cwe", []),
                severity=extra.get("severity", ""),
                references=meta.get("references", []),
                path=rel_path
            ))

        return processed
