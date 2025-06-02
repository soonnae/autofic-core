import json
from pathlib import Path

def read_json_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data: dict, path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def preprocess_semgrep_results(input_json_path: str, output_json_path: str, base_dir: str = ".") -> str:
    results = read_json_file(input_json_path)
    base_dir = Path(base_dir).resolve()
    processed = []
    
    for idx, result in enumerate(results.get("results", [])):
        path = base_dir / result.get("path", "")

        lines = path.read_text(encoding='utf-8').splitlines()
        full_code = "\n".join(lines)
        start_line = result["start"]["line"]
        end_line = result["end"]["line"]
        snippet = "\n".join(lines[start_line - 1:end_line])
        
        extra = result.get("extra", {})
        meta = extra.get("metadata", {})
        
        processed.append({
            "instruction": "Refactor the code below to fix the security vulnerability and include a brief remediation guide.",
            "input": full_code.strip(),
            "output": "",
            "idx": idx,
            "start_line": start_line,
            "end_line": end_line,
            "snippet": snippet.strip(), 
            "message": extra.get("message", ""),
            "vulnerability_class": meta.get("vulnerability_class", []),
            "cwe": meta.get("cwe", []),
            "severity": extra.get("severity", ""),
            "references": meta.get("references", [])
        })
    
    save_json_file(processed, output_json_path)
    
    return output_json_path