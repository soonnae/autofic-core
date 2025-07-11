import os
import json
from pathlib import Path
from typing import List
from autofic_core.sast.snippet import BaseSnippet

class SemgrepPreprocessor:

    @staticmethod
    def read_json_file(path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_json_file(data: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def preprocess(input_json_path: str, base_dir: str = ".") -> List[BaseSnippet]:
        results = SemgrepPreprocessor.read_json_file(input_json_path)
        base_dir_path = Path(base_dir).resolve()
        processed: List[BaseSnippet] = []

        items = results.get("results") if isinstance(results, dict) else results

        for idx, result in enumerate(items):
            raw_path = result.get("path", "").strip().replace("\\", "/")
            base_dir_str = str(base_dir_path).replace("\\", "/")

            rel_path = raw_path[len(base_dir_str):].lstrip("/") if raw_path.startswith(base_dir_str) else raw_path

            file_path = (base_dir_path / rel_path).resolve()
            if not file_path.exists():
                raise FileNotFoundError(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}")

            full_code = file_path.read_text(encoding='utf-8')

            if "start" in result and "line" in result["start"]:
                start_line = result["start"]["line"]
                end_line = result["end"]["line"]
            else:
                start_line = result.get("start_line", 0)
                end_line = result.get("end_line", 0)

            lines = full_code.splitlines()
            snippet_lines = lines[start_line - 1:end_line] if 0 < start_line <= end_line <= len(lines) else []
            snippet = "\n".join(snippet_lines)

            extra = result.get("extra", {})
            meta = extra.get("metadata", {})

            processed.append(BaseSnippet(
                input=full_code,
                idx=idx,
                start_line=start_line,
                end_line=end_line,
                snippet=snippet,
                message=extra.get("message", ""),
                vulnerability_class=meta.get("vulnerability_class", []),
                cwe=meta.get("cwe", []),
                severity=extra.get("severity", ""),
                references=meta.get("references", []),
                path=rel_path
            ))

        return processed