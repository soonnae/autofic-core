import click
import json
from autofic_core.github_handler import get_repo_files
from autofic_core.downloader import download_files  
from autofic_core.semgrep_preprocessor import preprocess_semgrep_results
from autofic_core.sast import run_semgrep

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--silent', is_flag=True, help="결과 출력 없이 조용히 실행")
@click.option('--save-dir', default="downloaded_repo", help="저장할 디렉토리 경로")
@click.option('--sast', is_flag=True, help='SAST 분석 수행 여부')
@click.option('--rule', default='p/javascript', help='Semgrep 규칙')
@click.option('--preprocess-semgrep', is_flag=True, help="Semgrep 결과 전처리 수행")
@click.option('--semgrep-output', default="semgrep_output.json", help="Semgrep 원본 결과 경로")
@click.option('--llm-input', default="llm_input.json", help="LLM 입력용 변환 결과 저장 경로")

def main(repo, silent, save_dir, sast, rule, preprocess_semgrep, semgrep_output, llm_input):
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
    
    if sast:
        click.echo("\nSemgrep 분석 시작!")
        click.echo("Semgrep 분석 진행 중...")
        semgrep_output, semgrep_error, semgrep_status = run_semgrep(save_dir, rule)
    
        if semgrep_status != 0:
            click.echo(f"\n[ ERROR ] Semgrep 실행 실패 (리턴 코드: {semgrep_status})\n")
            
            try:
                err_json = json.loads(semgrep_output or semgrep_error)
                click.echo("[ Semgrep 에러 내용 ]")
                for err in err_json.get("errors", []):
                    click.echo(f"- {err.get('message')} (코드: {err.get('code')})")
            
            except json.JSONDecodeError:
                click.echo("에러 메시지 JSON 파싱 실패 : ")
                click.echo(semgrep_error or semgrep_output)
            
            return

        click.echo("Semgrep 분석 완료!\n\n")

        try:
            with open(semgrep_output, 'r', encoding='utf-8') as f:
                results_json = json.load(f)
            with open(semgrep_output, 'w', encoding='utf-8') as f:
                json.dump(results_json, f, indent=4, ensure_ascii=False)
            click.echo(f"Semgrep 결과가 '{semgrep_output}'에 저장되었습니다.")

        except (json.JSONDecodeError, OSError) as e:
            click.echo(f"[ ERROR ] Semgrep 결과 파일 저장 중 문제 발생: {e}")  

    if preprocess_semgrep:
        output_json_path = preprocess_semgrep_results(semgrep_output, llm_input)
        if output_json_path:
            click.echo(f"전처리 완료된 JSON 파일이 '{output_json_path}'에 저장되었습니다.")
        else:
            click.echo("[ ERROR ] 전처리 실패")

if __name__ == '__main__':
    main()