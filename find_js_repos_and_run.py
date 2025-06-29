import requests
import subprocess
import os

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
HEADERS = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def get_recent_js_repos(top_n=5):
    query = 'language:JavaScript pushed:>2025-01-01'
    url = f"https://api.github.com/search/repositories?q={query}&sort=pushed&order=desc&per_page={top_n}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    repos = response.json()['items']
    return repos

def run_autofic(repo):
    repo_url = repo['clone_url']
    cmd = [
        'python', '-m', 'autofic_core.cli',
        '--repo', repo_url,
        '--save-dir', 'downloaded_folder',
        '--sast',
        '--rule', 'p/javascript'
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"Error running autofic on {repo_url} (exit code {result.returncode})")

def main():
    repos = get_recent_js_repos(2)
    for repo in repos:
        try:
            run_autofic(repo)
        except Exception as e:
            print(f"Error running autofic on {repo['clone_url']}: {e}")

if __name__ == "__main__":
    main()
