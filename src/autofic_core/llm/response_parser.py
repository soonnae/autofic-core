import re
from pathlib import Path

# unified diff 형식의 코드 블럭 추출
DIFF_CODE_BLOCK_PATTERN = re.compile(r'```(?:diff|[a-z]*)\n(@@[\s\S]+?)```', re.MULTILINE)
DIFF_HEADER_PATTERN = re.compile(r'^@@ -\d+,\d+ \+\d+,\d+ @@', flags=re.MULTILINE)


def extract_unified_diff(content: str) -> str:
    """
    .md 파일 내용에서 unified diff 코드 블럭을 추출한다.
    """
    matches = DIFF_CODE_BLOCK_PATTERN.findall(content)
    if not matches:
        raise ValueError("Unified diff 코드 블럭을 찾을 수 없습니다.")
    return matches[0].strip()


def parse_md_filename(md_filename: str) -> tuple[int, str]:
    """
    response_023_core_appHandler.js → (23, core_appHandler.js)
    """
    stem = Path(md_filename).stem
    if not stem.startswith("response_"):
        raise ValueError(f"[PARSE ERROR] 잘못된 파일명 형식: {md_filename}")

    name = stem[len("response_"):]  # remove prefix
    match = re.match(r"(\d{3})_(.+)", name)
    if not match:
        raise ValueError(f"[PARSE ERROR] 파일명에서 줄 번호 추출 실패: {md_filename}")

    start_line = int(match.group(1))
    flat_path = match.group(2)
    return start_line, flat_path


def fix_diff_header(diff_content: str, correct_line: int) -> str:
    """
    diff 헤더의 줄 번호를 Semgrep의 start_line에 맞게 보정한다.
    """
    def replacer(match):
        # 기존 삭제/추가 줄 수 유지
        parts = match.group().split()
        old_range = parts[1]
        new_range = parts[2]
        old_len = old_range.split(',')[1]
        new_len = new_range.split(',')[1]
        return f"@@ -{correct_line},{old_len} +{correct_line},{new_len} @@"

    return DIFF_HEADER_PATTERN.sub(replacer, diff_content, count=1)


def save_patch_file(diff_content: str, output_path: Path) -> None:
    """
    diff 내용을 .patch 파일로 저장한다.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(diff_content)


def parse_response_and_save_patch(md_path: Path, output_dir: Path) -> Path:
    """
    .md 파일을 읽고 diff를 추출한 뒤, .patch 파일로 저장한다.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        diff_content = extract_unified_diff(content)
        start_line, flat_path = parse_md_filename(md_path.name)
        diff_content = fix_diff_header(diff_content, start_line)
    except Exception as e:
        raise RuntimeError(f"[PARSE ERROR] {md_path.name}: {e}")

    patch_filename = f"patch_{start_line:03d}_{flat_path}.patch"
    patch_path = output_dir / patch_filename
    save_patch_file(diff_content, patch_path)

    return patch_path


class ResponseParser:
    """
    LLM의 응답으로 생성된 .md 파일들에서 unified diff 코드를 추출하고,
    diff 디렉토리에 .patch 파일로 저장한다.
    """
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
                parse_response_and_save_patch(md_file, self.diff_dir)
                success_count += 1
            except Exception as e:
                print(f"[ERROR] {md_file.name} 처리 실패: {e}")

        return success_count > 0
