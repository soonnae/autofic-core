import click
from autofic_core.github_handler import get_repo_files
from autofic_core.downloader import download_files  

@click.command()
@click.option('--repo', help='GitHub repository URL')
@click.option('--silent', is_flag=True, help="결과 출력 없이 조용히 실행")
@click.option('--save-dir', default="downloaded_repo", help="저장할 디렉토리 경로")
def main(repo, silent, save_dir):
    click.echo(f"Analyzing repo: {repo}")

    files = get_repo_files(repo, silent=silent)

    if not files:
        print("JS 파일을 찾지 못했습니다. 저장소 구조 또는 필터 조건을 확인하세요.")
        return

    if not silent:
        print(f"JS 파일 {len(files)}개를 찾았습니다:")
        for file in files:
            print(f"{file['path']} -> {file['download_url']}")

    download_files(repo_url=repo, save_dir=save_dir, silent=silent)

if __name__ == '__main__':
    main()
