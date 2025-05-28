import json
from pathlib import Path

def preprocess_semgrep_results(input_json_path: str, output_json_path: str, base_dir: str = "../.."):
    with open(input_json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    processed = []

    for idx, result in enumerate(results.get("results", [])):
        file_path = Path(base_dir) / result.get("path", "")
        start_line = result.get("start", {}).get("line", None)
        end_line = result.get("end", {}).get("line", None)

        code_snippet = ""
        if file_path.exists() and start_line and end_line:
            with open(file_path, 'r', encoding='utf-8') as src_file:
                lines = src_file.readlines()
                code_snippet = "".join(lines[start_line-1:end_line])

        processed.append({
            "instruction": "Refactor the code below to fix the security vulnerability and include a brief remediation guide.",
            "input": code_snippet.strip(),
            "output": "",
            "idx": idx
        })

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=4, ensure_ascii=False)

    return output_json_path
    