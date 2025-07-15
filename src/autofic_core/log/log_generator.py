import datetime
import json
import re
from typing import List
from pathlib import Path
from collections import Counter, defaultdict
from autofic_core.pr_auto.pr_procedure import PRProcedure
from autofic_core.sast.semgrep.preprocessor import SemgrepPreprocessor
from autofic_core.sast.codeql.preprocessor import CodeQLPreprocessor
from autofic_core.sast.snykcode.preprocessor import SnykCodePreprocessor
from autofic_core.sast.snippet import BaseSnippet

class LogGenerator:
    def __init__(self, default_options=None):
        self.default_options = default_options or {}

    def generate_pr_log(self, user_name, repo_name, approved=False):
        today = datetime.date.today().isoformat()
        return {
            "date": today,
            "repo": f"{repo_name}",
            "user_name":f"{user_name}",
            "approved": approved
        }
 
    def generate_repo_log(self, save_dir, name, owner, repo_url, sastTool, rerun=False):
        before_json = Path(save_dir) / 'sast' / 'before.json'
        vulnerabilities = 0
        byClass = []      
        
        if sastTool == "semgrep":
            snippets = SemgrepPreprocessor.preprocess(before_json)
        elif sastTool == "codeql":
            snippets = CodeQLPreprocessor.preprocess(before_json)
        elif sastTool == "snykcode":
            snippets = SnykCodePreprocessor.preprocess(before_json)
        else:
            raise ValueError(f"Unknown tool: {sastTool}")

        byClass_counter = Counter()
        for item in snippets:
            if item.vulnerability_class:
                byClass_counter[item.vulnerability_class[0]] += 1
        byClass = [{"type": k, "count": v} for k, v in byClass_counter.items()]
        vulnerabilities = sum(byClass_counter.values())

        analysis_lines = []
        analysis_lines.append("## 🔏 Security Patch Summary\n")

        # SAST Summary
        if vulnerabilities > 0:
            analysis_lines.append(f"### SAST Analysis Summary")
            analysis_lines.append(f"- Total Vulnerabilities: {vulnerabilities}")
            for entry in byClass:
                analysis_lines.append(f"- {entry['type']}: {entry['count']}")

            grouped_by_file = defaultdict(list)
            for item in snippets:
                filename = Path(item.path or "Unknown").name
                grouped_by_file[filename].append(item)

            file_idx = 1
            for filename, items in grouped_by_file.items():
                analysis_lines.append(f"\n### 🗂️ {file_idx}. `{filename}`")
                analysis_lines.append(f"#### 🔎 SAST Analysis Details")
                for vuln_idx, item in enumerate(items, 1):
                    vuln = item.vulnerability_class[0] if item.vulnerability_class else "N/A"
                    analysis_lines.append(f"> #### {file_idx}-{vuln_idx}. [Vulnerability] {vuln}")
                    analysis_lines.append(f"> - 🛡️ Severity: {item.severity}")
                    if item.message:
                        analysis_lines.append(f"> - ✍️ Message: {item.message.strip()}")
                    if item.cwe:
                        analysis_lines.append(f"> - 🔖 CWE: {', '.join(item.cwe)}")
                    if item.references:
                        for ref in item.references:
                            analysis_lines.append(f"> - 🔗 Reference: {ref}")
                file_idx += 1
        else:
            analysis_lines.append("⚠️ No SAST results available.")

        # LLM Summary
        llm_dir = Path(save_dir) / 'llm'
        analysis_lines.append("\n### 🤖 LLM Analysis Summary")
        for llm_file in llm_dir.glob('*.md'):
            with open(llm_file, encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                continue

            analysis_lines.append(f"\n#### {llm_file.name}")

            parsed = self.parse_llm_response(content)
            if parsed["Vulnerability"] or parsed["Risks"] or parsed["Recommended Fix"] or parsed["References"]:
                if parsed["Vulnerability"]:
                    analysis_lines.append(f"> #### 🐞 Vulnerability Description")
                    analysis_lines.append(f"> {parsed['Vulnerability']}")
                if parsed["Risks"]:
                    analysis_lines.append(f"> #### ⚠️ Potential Risks")
                    analysis_lines.append(f"> {parsed['Risks']}")
                if parsed["Recommended Fix"]:
                    analysis_lines.append(f"> #### 🛠 Recommended Fix")
                    analysis_lines.append(f"> {parsed['Recommended Fix']}")
                if parsed["References"]:
                    analysis_lines.append(f"> #### 📎 References")
                    analysis_lines.append(f"> {parsed['References']}")

        analysis_text = "\n".join(analysis_lines)

        return {
            "name": name,
            "owner": owner,
            "repo_url": repo_url,
            "vulnerabilities": vulnerabilities,
            "byClass": byClass,
            "changes": 0,
            "analysis": analysis_text,
            "sastTool": sastTool,
            "rerun": rerun
        }

    def parse_llm_response(self, content: str) -> dict:
        sections = {
            "Vulnerability": "",
            "Risks": "",
            "Recommended Fix": "",
            "References": ""
        }

        pattern = re.compile(
            r"1\. 취약점 설명\s*[:：]?(.*?)"
            r"2\. 예상 위험\s*[:：]?(.*?)"
            r"3\. 개선 방안\s*[:：]?(.*?)"
            r"(?:4\. 최종 수정된 전체 코드.*?)?"
            r"5\. 참고사항\s*[:：]?(.*)",
            re.DOTALL
        )

        match = pattern.search(content)
        if match:
            sections["Vulnerability"] = match.group(1).strip()
            sections["Risks"] = match.group(2).strip()
            sections["Recommended Fix"] = match.group(3).strip()
            sections["References"] = match.group(4).strip()

        return sections