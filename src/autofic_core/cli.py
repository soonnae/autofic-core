import click
from autofic_core.github_handler import get_repo_files
from autofic_core.downloader import download_files  
from autofic_core.semgrep_preprocessor import preprocess_semgrep_results

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--silent', is_flag=True, help="결과 출력 없이 조용히 실행")
@click.option('--save-dir', default="downloaded_repo", help="저장할 디렉토리 경로")

@click.option('--preprocess-semgrep', is_flag=True, help="Semgrep 결과 전처리 수행")
@click.option('--semgrep-input', default="semgrep_output.json", help="Semgrep 원본 결과 경로")
@click.option('--semgrep-output', default="llm_input.json", help="LLM 입력용 변환 결과 저장 경로")

def main(repo, silent, save_dir, preprocess_semgrep, semgrep_input, semgrep_output):
    click.echo(f"Analyzing repo: {repo}")

    files = get_repo_files(repo, silent=silent)

    if not files:
        print("JS 파일을 찾지 못했습니다. 저장소 구조 또는 필터 조건을 확인하세요.")
        return

    if not silent:
        print(f"JS 파일 {len(files)}개를 찾았습니다:")
        for file in files:
            print(f"{file['path']} -> {file['download_url']}")

    download_files(js_files=files, save_dir=save_dir, silent=silent)

    if preprocess_semgrep:
        output_json_path = preprocess_semgrep_results(semgrep_input, semgrep_output)
        print(f"전처리 완료된 JSON 파일이 저장되었습니다 : {output_json_path}")

if __name__ == '__main__':
    main()
