import json
import os
from typing import List
from autofic_core.sast.snippet import BaseSnippet


class CodeQLPreprocessor:

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
    def preprocess(input_json_path: str, base_dir: str) -> List[BaseSnippet]:
        results = CodeQLPreprocessor.read_json_file(input_json_path)

        rule_metadata = {}
        for run in results.get("runs", []):
            for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
                rule_id = rule.get("id")
                if rule_id:
                    rule_metadata[rule_id] = {
                        "cwe": [
                            m.split("/")[-1].replace("cwe-", "CWE-")
                            for m in rule.get("properties", {}).get("tags", [])
                            if "cwe-" in m
                        ],
                        "references": [rule.get("helpUri")] if rule.get("helpUri") else [],
                        "level": (
                            rule.get("defaultConfiguration", {}).get("level")
                            or rule.get("properties", {}).get("problem.severity", "UNKNOWN")
                        )
                    }

        processed: List[BaseSnippet] = []
        snippet_idx = 0

        for run in results.get("runs", []):
            for res in run.get("results", []):
                location = res.get("locations", [{}])[0].get("physicalLocation", {})
                artifact = location.get("artifactLocation", {})
                region = location.get("region", {})

                path = artifact.get("uri", "Unknown").replace("/", os.sep)
                start_line = region.get("startLine", 0)
                end_line = region.get("endLine") or start_line
                full_path = os.path.join(base_dir, path)

                lines = []
                snippet = ""
                
                rule_id = res.get("ruleId")
                meta = rule_metadata.get(rule_id, {}) if rule_id else {}
                
                level = res.get("level") or meta.get("level", "UNKNOWN")
                if isinstance(level, list):
                    level = level[0] if level else "UNKNOWN"
                severity = str(level).upper()

                try:
                    if os.path.exists(full_path):
                        with open(full_path, "r", encoding="utf-8") as code_file:
                            lines = code_file.readlines()

                        if start_line > len(lines) or start_line < 1:
                            continue

                        raw_snippet = (
                            lines[start_line - 1:end_line]
                            if end_line > start_line
                            else [lines[start_line - 1]]
                        )
                        snippet = "".join(raw_snippet)

                        if all(not line.strip() for line in raw_snippet):
                            continue

                except Exception:
                    continue

                processed.append(BaseSnippet(
                    input="".join(lines),
                    snippet=snippet.strip(),
                    path=path,
                    idx=int(snippet_idx),
                    start_line=start_line,
                    end_line=end_line,
                    message=res.get("message", {}).get("text", ""),
                    severity=severity, 
                    vulnerability_class=[rule_id] if rule_id else [],
                    cwe=meta.get("cwe", []),
                    references=meta.get("references", [])
                ))
                snippet_idx += 1

        return processed
