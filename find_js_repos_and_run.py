import requests
import subprocess
import os
import tempfile
import shutil

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
HEADERS = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def get_recent_js_repos(top_n=5):
    query = 'language:JavaScript pushed:>2024-01-01'
    url = f"https://api.github.com/search/repositories?q={query}&sort=pushed&order=desc&per_page={top_n}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    repos = response.json()['items']
    return repos

def run_autofic(repo):
    repo_url = repo['clone_url']
    full_name = repo['full_name']  # OWNER/REPO
    
    tmp_dir = tempfile.mkdtemp()
    orig_dir = os.getcwd()
    try:
        # Clone repo (공개 레포는 토큰 없이 clone 가능)
        subprocess.run(['git', 'clone', repo_url, tmp_dir], check=True)
        os.chdir(tmp_dir)

        # 만약 push가 필요하다면 remote set-url, 아니면 생략 가능
        if GITHUB_TOKEN:
            subprocess.run([
                'git', 'remote', 'set-url', 'origin',
                f'https://x-access-token:{GITHUB_TOKEN}@github.com/{full_name}.git'
            ], check=True)

        # Run Autofic
        cmd = [
            'python', '-m', 'autofic_core.cli',
            '--repo', repo_url,
            '--save-dir', 'downloaded_folder',
            '--sast',
            '--rule', 'p/javascript'
        ]
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)
    finally:
        os.chdir(orig_dir)
        shutil.rmtree(tmp_dir)

def main():
    repos = get_recent_js_repos(5)
    for repo in repos:
        try:
            run_autofic(repo)
        except Exception as e:
            print(f"Error running autofic on {repo['clone_url']}: {e}")

if __name__ == "__main__":
    main()
