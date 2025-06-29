import requests
import subprocess
import os
import time

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
HEADERS = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def has_js_in_latest_commit(owner, repo):
    """최신 커밋에 js파일 변경이 포함되어 있는지 확인"""
    commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    resp = requests.get(commits_url, headers=HEADERS)
    resp.raise_for_status()
    latest_commit = resp.json()[0]
    sha = latest_commit['sha']

    commit_detail_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    detail_resp = requests.get(commit_detail_url, headers=HEADERS)
    detail_resp.raise_for_status()
    files = detail_resp.json().get('files', [])
    for f in files:
        if f['filename'].endswith('.js'):
            return True
    return False

def get_recent_js_committed_repos(top_n=5):
    """최근 커밋이 JS파일 변경인 레포만 top_n개 반환(중복없이)"""
    query = 'pushed:>2025-01-01'
    per_page = 20  # 넉넉하게 받아서 필터
    url = f"https://api.github.com/search/repositories?q={query}&sort=pushed&order=desc&per_page={per_page}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    repos = response.json()['items']

    filtered = []
    seen = set()
    for repo in repos:
        full_name = repo['full_name']
        owner = repo['owner']['login']
        name = repo['name']
        if full_name in seen:
            continue
        seen.add(full_name)
        try:
            if has_js_in_latest_commit(owner, name):
                filtered.append(repo)
                print(f"[INFO] {full_name} (최근커밋에 JS 변경 O)")
            else:
                print(f"[SKIP] {full_name} (최근커밋에 JS 변경 X)")
        except Exception as e:
            print(f"[ERROR] {full_name}: {e}")
        if len(filtered) >= top_n:
            break
        time.sleep(0.3)  # GitHub API rate limit 대비

    return filtered

def run_autofic(repo):
    repo_url = repo['clone_url']
    print(f"\n[RUN] {repo_url}")
    cmd = [
        'python', '-m', 'autofic_core.cli',
        '--repo', repo_url,
        '--save-dir', 'downloaded_folder',
        '--sast',
        '--rule', 'p/javascript'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("[STDOUT]", result.stdout)
    print("[STDERR]", result.stderr)
    if result.returncode != 0:
        print(f"[FAIL] {repo_url} (exit code {result.returncode})")

def main():
    repos = get_recent_js_committed_repos(top_n=2)
    for repo in repos:
        try:
            run_autofic(repo)
        except Exception as e:
            print(f"[ERROR] {repo['clone_url']}: {e}")

if __name__ == "__main__":
    main()
