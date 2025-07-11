import re
from pathlib import Path

CODE_BLOCK_PATTERN = re.compile(r'```(?:js|javascript)\n([\s\S]+?)```', re.IGNORECASE | re.MULTILINE)

def extract_code_blocks(content: str) -> str:
    matches = CODE_BLOCK_PATTERN.findall(content)
    if not matches:
        raise ValueError("js/javascript 코드 블럭을 찾을 수 없습니다.")
    return "\n\n".join(m.strip() for m in matches)

def parse_md_filename(md_filename: str) -> str:
    stem = Path(md_filename).stem
    if not stem.startswith("response_"):
        raise ValueError(f"[PARSE ERROR] 잘못된 파일명 형식: {md_filename}")

    flat_path = stem[len("response_"):]
    flat_path = flat_path.replace("_", "/")

    return flat_path

def save_code_file(code_content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code_content)

def parse_response_and_save_code(md_path: Path, output_dir: Path) -> Path:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        code_content = extract_code_blocks(content)
        flat_path = parse_md_filename(md_path.name)
    except Exception as e:
        raise RuntimeError(f"[PARSE ERROR] {md_path.name}: {e}")

    output_path = output_dir / flat_path
    save_code_file(code_content, output_path)

    return output_path

class ResponseParser:
    def __init__(self, md_dir: Path, diff_dir: Path):
        self.md_dir = md_dir
        self.diff_dir = diff_dir

    def extract_and_save_all(self) -> bool:
        md_files = list(self.md_dir.glob("*.md"))
        if not md_files:
            print(f"[WARN] {self.md_dir} 에 .md 파일이 없습니다.")
            return False

        success_count = 0
        for md_file in md_files:
            try:
                parse_response_and_save_code(md_file, self.diff_dir)
                success_count += 1
            except Exception as e:
                print(f"[ERROR] {md_file.name} 처리 실패: {e}")

        return success_count > 0