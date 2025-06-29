import requests
import subprocess
import os

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '') # 필요시 Personal Access Token 입력(공개 저장소만 쓸 땐 없어도 됨)
HEADERS = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def get_recent_js_repos(top_n=5):
    query = 'language:JavaScript pushed:>2024-01-01'
    url = f"https://api.github.com/search/repositories?q={query}&sort=pushed&order=desc&per_page={top_n}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    repos = response.json()['items']
    return [repo['clone_url'] for repo in repos]

def run_autofic(repo_url):
    cmd = [
        'python', '-m', 'autofic_core.cli',
        '--repo', repo_url,
        '--save-dir', 'downloaded_folder',
        '--sast',
        '--rule', 'p/javascript'
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    repos = get_recent_js_repos(5)
    for repo_url in repos:
        try:
            run_autofic(repo_url)
        except Exception as e:
            print(f"Error running autofic on {repo_url}: {e}")

if __name__ == "__main__":
    main()