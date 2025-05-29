import click
import json
from autofic_core.github_handler import get_repo_files
from autofic_core.downloader import download_files  
from autofic_core.sast import run_semgrep
from autofic_core.semgrep_preprocessor import preprocess_semgrep_results, save_json_file 
from rich.progress import Progress, SpinnerColumn, TextColumn

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--save-dir', default="downloaded_repo", help="저장할 디렉토리 경로")
@click.option('--sast', is_flag=True, help='SAST 분석 수행 여부')
@click.option('--rule', default='p/javascript', help='Semgrep 규칙')
@click.option('--preprocess-semgrep', is_flag=True, help="Semgrep 결과 전처리 수행")
@click.option('--semgrep-result', default="semgrep_result.json", help="Semgrep 원본 결과 경로")
@click.option('--llm-input', default="llm_input.json", help="LLM 입력용 변환 결과 저장 경로")

def main(repo, save_dir, sast, rule, preprocess_semgrep, semgrep_result, llm_input):
    click.echo(f"Analyzing repo: {repo}")

    #click.echo("파일 탐색 시작 ...")
    files = get_repo_files(repo)

    if not files:
        click.echo("JS 파일을 찾지 못했습니다. Github 연결이나 저장소를 확인하세요.")
    
    click.echo(f"JS 파일 {len(files)}개를 찾았습니다!")
    
    results = download_files(js_files=files, save_dir=save_dir)

    for r in results:
        if r["status"] == "success":
            click.echo(f"{r['path']} 다운로드 완료")
        elif r["status"] == "skipped":
            click.echo(f"{r['path']} 이미 존재함 - 건너뜀")
        else:
            click.echo(f"{r['path']} 다운로드 실패: {r['error']}")

    if sast:
        click.echo("\nSemgrep 분석 시작!")

        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Semgrep 분석 중입니다..."),
            transient=True
        ) as progress:
            task3 = progress.add_task("[cyan]Semgrep 분석 진행 중...", total=None)

            semgrep_output, semgrep_error, semgrep_status = run_semgrep(save_dir, rule)

            progress.update(task3, completed=1)
    
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
            
        save_json_file(json.loads(semgrep_output), semgrep_result)
        click.echo(f"Semgrep 분석 완료! 결과가 '{semgrep_result}'에 저장되었습니다.")
    
    if preprocess_semgrep:
        try:
            output_json_path = preprocess_semgrep_results(semgrep_result, llm_input)
            click.echo(f"전처리 완료: '{output_json_path}'에 저장되었습니다.")
        except Exception as e:
            click.echo(f"[ERROR] 전처리 실패: {e}")

if __name__ == '__main__':
    main()