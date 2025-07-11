import json
import os
from pathlib import Path
from typing import List, Any 
from autofic_core.sast.snippet import BaseSnippet 


class SnykCodePreprocessor:

    @staticmethod
    def read_json_file(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_json_file(data: Any, path: str) -> None:
        os.makedirs(Path(path).parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def preprocess(input_json_path: str, base_dir: str = ".") -> List[BaseSnippet]:
        sarif = SnykCodePreprocessor.read_json_file(input_json_path)
        base_path = Path(base_dir).resolve()
        snippets: List[BaseSnippet] = []

        for run in sarif.get("runs", []):
            rules_map = {
                rule.get("id"): rule
                for rule in run.get("tool", {}).get("driver", {}).get("rules", [])
            }

            for idx, result in enumerate(run.get("results", [])):
                location = result.get("locations", [{}])[0].get("physicalLocation", {})
                region = location.get("region", {})
                file_uri = location.get("artifactLocation", {}).get("uri", "")
                file_path = (base_path / file_uri).resolve()

                if not file_path.exists():
                    continue  # 또는 로그 출력하고 skip

                lines = file_path.read_text(encoding="utf-8").splitlines()
                full_code = "\n".join(lines)
                start_line = region.get("startLine", 0)
                end_line = region.get("endLine", start_line)
                snippet = "\n".join(lines[start_line - 1:end_line])

                rule_id = result.get("ruleId", "")
                rule = rules_map.get(rule_id, {})
                help_uri = rule.get("helpUri", "")
                cwe_tags = rule.get("properties", {}).get("tags", [])
                cwe = [t.split("/")[-1].replace("cwe-", "CWE-") for t in cwe_tags if "cwe" in t.lower()]
                references = [help_uri] if help_uri else []

                snippets.append(BaseSnippet(
                    input=full_code.strip(),
                    idx=idx,
                    start_line=start_line,
                    end_line=end_line,
                    snippet=snippet.strip(),
                    message=result.get("message", {}).get("text", ""),
                    severity=result.get("level", "").upper(),
                    path=file_uri,
                    vulnerability_class=[rule_id] if rule_id else [],
                    cwe=cwe,
                    references=references
                ))

        return snippets