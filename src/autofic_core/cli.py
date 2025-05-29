import click
from autofic_core.github_handler import get_repo_files

@click.command()
@click.option('--repo', help='GitHub repository URL')
def main(repo):
    click.echo(f"Analyzing repo: {repo}")

    click.echo("파일 탐색 시작 ...")
    files = get_repo_files(repo)

    # 파일 목록 출력 예시
    if not files:
        click.echo("JS 파일을 찾지 못했습니다. Github 연결이나 저장소를 확인하세요.")
    
    click.echo(f"JS 파일 {len(files)}개를 찾았습니다!")

if __name__ == '__main__':
    main()