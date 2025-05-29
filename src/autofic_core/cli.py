import click
import json
from autofic_core.github_handler import get_repo_files
from autofic_core.downloader import download_files  
from autofic_core.sast import run_semgrep

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--silent', is_flag=True, help="결과 출력 없이 조용히 실행")
@click.option('--save-dir', default="downloaded_repo", help="저장할 디렉토리 경로")
@click.option('--sast', is_flag=True, help='SAST 분석 수행 여부')
@click.option('--rule', default='p/javascript', help='Semgrep 규칙')
def main(repo, silent, save_dir, sast, rule):
    click.echo(f"Analyzing repo: {repo}")

    files = get_repo_files(repo, silent=silent)

    if not files:
        print("JS 파일을 찾지 못했습니다. 저장소 구조 또는 필터 조건을 확인하세요.")
        return

    if not silent:
        print(f"JS 파일 {len(files)}개를 찾았습니다:")
        for file in files:
            print(f"{file['path']} -> {file['download_url']}")

    results = download_files(js_files=files, save_dir=save_dir, silent=silent)

    if not silent:
        for r in results:
            if r["status"] == "success":
                print(f"{r['path']} 다운로드 완료")
            elif r["status"] == "skipped":
                print(f"{r['path']} 이미 존재함 - 건너뜀")
            else:
                print(f"{r['path']} 다운로드 실패: {r['error']}")

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
        click.echo("[ Semgrep 결과 ]\n")

        try:
            results_json = json.loads(semgrep_output)
            results = results_json.get("results", [])

            for result in results:
                click.echo(json.dumps(result, indent=4))
                click.echo('\n' + '-'*80 + '\n')

        except json.JSONDecodeError:
            click.echo("Semgrep 결과 JSON 파싱 실패")
            click.echo(semgrep_output)    

if __name__ == '__main__':
    main()
