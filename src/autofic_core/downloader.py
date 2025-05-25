import os
import requests
import click
from autofic_core.github_handler import get_repo_files

@click.command()
@click.option('--repo', required=True, help='GitHub 저장소 URL')
@click.option('--silent', is_flag=True, help='출력 생략 여부')
@click.option('--save-dir', default='downloaded_repo', help='다운로드할 로컬 디렉토리')
def download(repo, silent, save_dir):
    click.echo(f"[START] 저장소 분석: {repo}")

    js_files = get_repo_files(repo, silent=silent)
    if not js_files:
        click.echo("JS 파일이 없습니다.")
        return

    click.echo(f"총 {len(js_files)}개 JS 파일 다운로드 시작...")

    for file in js_files:
        file_path = os.path.join(save_dir, file["path"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        response = requests.get(file["download_url"])
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            if not silent:
                click.echo(f"저장됨: {file_path}")
        else:
            click.echo(f"실패: {file['download_url']}")

    click.echo("다운로드 완료.")

if __name__ == '__main__':
    download()
