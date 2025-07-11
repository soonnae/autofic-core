from collections import defaultdict
from typing import List
from autofic_core.sast.semgrep.preprocessor import BaseSnippet


def merge_snippets_by_file(snippets: List[BaseSnippet]) -> List[BaseSnippet]:
    grouped = defaultdict(list)

    for snippet in snippets:
        grouped[snippet.path].append(snippet)

    merged_snippets = []

    for path, group in grouped.items():
        base = group[0]
        start_line = min(s.start_line for s in group)
        end_line = max(s.end_line for s in group)

        snippet_lines_set = set()
        for s in group:
            if s.snippet:
                snippet_lines_set.update(s.snippet.splitlines())
        merged_snippet_text = "\n".join(sorted(snippet_lines_set))

        merged_message = " | ".join(sorted(set(s.message for s in group if s.message)))
        merged_vuln_class = sorted({vc for s in group for vc in s.vulnerability_class})
        merged_cwe = sorted({c for s in group for c in s.cwe})
        merged_references = sorted({r for s in group for r in s.references})

        severity = max(
            (s.severity for s in group),
            key=lambda x: ["INFO", "WARNING", "ERROR"].index(x.upper()) if x.upper() in ["INFO", "WARNING", "ERROR"] else -1,
            default=""
        )

        merged_snippets.append(BaseSnippet(
            input=base.input,
            idx=None,
            start_line=start_line,
            end_line=end_line,
            snippet=merged_snippet_text,
            message=merged_message,
            vulnerability_class=merged_vuln_class,
            cwe=merged_cwe,
            severity=severity,
            references=merged_references,
            path=path
        ))

    return merged_snippets