import click
from autofic_core.github_handler import get_repo_files

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--silent', is_flag=True, help="결과 출력 없이 조용히 실행")
def main(repo, silent):
    click.echo(f"Analyzing repo: {repo}")

    files = get_repo_files(repo, silent=silent)

    # 파일 목록 출력 예시
    if not files:
        click.echo("JS 파일을 찾지 못했습니다. 저장소 구조 또는 필터 조건을 확인하세요.")
    
    click.echo(f"JS 파일 {len(files)}개를 찾았습니다:")

    if not silent:
        for file in files:
            click.echo(f"{file['path']} -> {file['download_url']}")

if __name__ == '__main__':
    main()