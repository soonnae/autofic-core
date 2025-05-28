import json
from pathlib import Path

def preprocess_semgrep_results(input_json_path: str, output_json_path: str, base_dir: str = "./"):
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[입력 파일 오류] {e}")
        return None

    base_dir = Path(base_dir).resolve()  
    processed = []

    for idx, result in enumerate(results.get("results", [])):
        raw_path = result.get("path", "")
        file_path = (base_dir / raw_path).resolve()

        start_line = result.get("start", {}).get("line", None)
        end_line = result.get("end", {}).get("line", None)

        code_snippet = ""

        if file_path.exists() and isinstance(start_line, int) and isinstance(end_line, int):
            try:
                with open(file_path, 'r', encoding='utf-8') as src_file:
                    lines = src_file.readlines()   
                    code_snippet = "".join(lines[start_line-1:end_line])
            except Exception as e:
                print(f"[파일 읽기 실패] {file_path} - {e}")
        else:
            print(f"[코드 추출 실패] {file_path}, lines {start_line}-{end_line}")

        extra = result.get("extra", {})
        metadata = extra.get("metadata", {})

        processed.append({
            "Instruction": "Refactor the code below to fix the security vulnerability and include a brief remediation guide.",
            "input": code_snippet.strip(),
            "output": "",
            "idx": idx, 
            "message": extra.get("message", ""),
            "vulnerability_class": metadata.get("vulnerability_class", []),
            "cwe": metadata.get("cwe", []),
            "severity": extra.get("severity", ""),
            "references": metadata.get("references", [])
        })

    try: 
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[결과 저장 실패] {e}")
        return None

    return output_json_path